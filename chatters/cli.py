import os
import asyncio
import json
from collections import deque
from typing import Optional
from contextlib import AsyncExitStack
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

from rich.console import Console
from rich.markdown import Markdown
console = Console()

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Set up OpenCode Zen client
        api_key = os.getenv('OPENCODE_ZEN_API_KEY')
        if not api_key:
            try:
                from keys import opencode_zen_api_key
                api_key = opencode_zen_api_key
            except ImportError:
                pass
        
        if not api_key:
            raise ValueError("Missing OpenCode Zen API key. Set OPENCODE_ZEN_API_KEY environment variable or update keys.py")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://opencode.ai/zen/v1"
        )
        
        # Store model configuration
        self.default_model = os.getenv('OPENCODE_ZEN_MODEL', 'gpt-5.1-codex')
        try:
            from keys import opencode_zen_model
            if opencode_zen_model:
                self.default_model = opencode_zen_model
        except ImportError:
            pass

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
        init = self.client.chat.completions.create(
            model=self.default_model,
            max_tokens=3000,
            messages=init_messages,
            tools=available_tools
        )

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

        # Set up followup model
        followup_model = os.getenv('OPENCODE_ZEN_FOLLOWUP_MODEL', 'gpt-5.1-codex-mini')
        
        while out_reason != 'stop':
            # keep passing tool responses back
            r = self.client.chat.completions.create(
                model=followup_model,
                max_tokens=3000,
                messages=out_messages,
                tools=available_tools
            )

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
