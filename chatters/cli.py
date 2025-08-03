import os
import asyncio
import json
from collections import deque
from typing import Optional
from contextlib import AsyncExitStack
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

from rich.console import Console
from rich.markdown import Markdown
from llm_providers import provider_registry
from llm_providers.config import ProviderConfig

console = Console()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Initialize LLM provider system
        self.provider_config = ProviderConfig()
        self.current_provider = None
        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the LLM provider based on configuration."""
        try:
            # Try to initialize from auto-detection
            provider = provider_registry.initialize_auto_provider()
            if provider:
                self.current_provider = provider
                logging.info(f"Initialized LLM provider: {provider.name}")
            else:
                logging.warning("No LLM provider could be initialized")
        except Exception as e:
            logging.error(f"Failed to initialize LLM provider: {str(e)}")

    async def connect_to_server(self):

        command = "./.venv/Scripts/python.exe"
        server_params = StdioServerParameters(
            command=command,
            # args=['./servers/localsqlite.py', '--db-path', './database.db'],  # defaults to 'test.db'
            args=['./servers/filesystem.py', './'],
            # args=['./servers/multiplexer.py'],
            env=None
        )
        
        logging.debug(f'Launching server {command} {server_params}')
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        logging.debug(f"Connected to server with tools:{[tool.name for tool in tools]}")

    async def process_query(self, history):
        """Process a query using available tools"""

        init_messages = history

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "parameters": tool.inputSchema,
            }
        } for tool in response.tools]

        # Initial LLM call
        if not self.current_provider:
            raise RuntimeError("No LLM provider available")
        
        init_response = self.current_provider.chat_completion(
            messages=init_messages,
            max_tokens=3000,
            tools=available_tools
        )
        
        # Convert to expected format for compatibility
        class MockResponse:
            def __init__(self, response_dict):
                self.choices = [MockChoice(choice) for choice in response_dict['choices']]
        
        class MockChoice:
            def __init__(self, choice_dict):
                self.finish_reason = choice_dict['finish_reason']
                self.message = MockMessage(choice_dict['message'])
        
        class MockMessage:
            def __init__(self, message_dict):
                self.content = message_dict['content']
                self.tool_calls = message_dict.get('tool_calls')
            
            def model_dump(self):
                return {
                    'message': {
                        'tool_calls': [self.tool_calls] if self.tool_calls else None
                    }
                }
        
        init = MockResponse(init_response)

        # Process response and handle tool calls

        async def handle(response, messages):
            reason = response.choices[0].finish_reason

            content = response.choices[0]

            if reason == 'stop':
                messages.append({"role":"assistant", "content":content.message.content})
            elif reason == 'tool_calls':
                
                content = content.model_dump()
                content = content['message']['tool_calls'][0]  # are models smart enough to send multiple tool calls?

                tool_name = content['function']['name']
                tool_args = json.loads(content['function']['arguments'])
                
                # Execute tool call
                logging.info(f'calling tool {tool_name}({tool_args})')
                result = await self.session.call_tool(tool_name, tool_args)

                if result.isError:
                    summary = f"""Called tool {tool_name} ({tool_args}), got ERROR: {result.content[0].text}\n"""
                else:
                    summary = f"""Called tool {tool_name} ({tool_args}), got results: {result.content[0].text}\n"""

                messages.append({"role":"assistant", "content":summary})


            return messages, reason

        out_messages, out_reason = await handle(init, init_messages)

        while out_reason != 'stop':
            # keep passing tool responses back
            followup_response = self.current_provider.chat_completion(
                messages=out_messages,
                model=self.current_provider.get_followup_model(),
                max_tokens=3000,
                tools=available_tools
            )
            
            r = MockResponse(followup_response)
            out_messages, out_reason = await handle(r, out_messages)
                    
        return "\n".join([x['content'] for x in out_messages[-1:]])

    async def chat_loop(self):
        """Run an interactive chat loop"""
        console.print("\nMCP Client Started!")
        console.print("Type your queries or 'quit' to exit.")

        history = deque(maxlen=8)

        while True:
            try:
                query = input("\n> ").strip()
                
                if query.lower() in ('quit', 'exit'):
                    break

                history.append({'role':'user', 'content':query})
                console.print('\n')

                response = await self.process_query(list(history))
                history.append({'role':'assistant', 'content':response})
                console.print(Markdown("\n" + response))
                    
            except Exception as e:
                logging.exception(e)
                break
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
