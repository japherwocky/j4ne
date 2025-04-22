import os
import asyncio
import json
from typing import Optional
from contextlib import AsyncExitStack
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        api_path=os.getenv('AZURE_OPENAI_ENDPOINT') + os.getenv('AZURE_OPENAI_API_MODEL')
        self.client = AzureOpenAI(api_version=os.getenv('AZURE_OPENAI_API_VERSION'), base_url=api_path)

    async def connect_to_server(self):
        

        command = "./.venv/Scripts/python.exe"
        server_params = StdioServerParameters(
            command=command,
            args=['./servers/localsqlite.py', '--db-path', './database.db'],  # defaults to 'test.db'
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

    async def process_query(self, query: str) -> str:
        """Process a query using available tools"""
        init_messages = [
            {
                "role": "user",
                "content": query
            }
        ]

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
            model="gpt-4-turbo",
            max_tokens=1000,
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
                result = await self.session.call_tool(tool_name, tool_args)

                summary = f"""Called tool {tool_name} ({tool_args}), got results: {result.content[0].text}"""

                messages.append({"role":"assistant", "content":summary})


            return messages, reason

        out_messages, out_reason = await handle(init, init_messages)

        while out_reason != 'stop':
            # keep passing tool responses back
            r = self.client.chat.completions.create(
                model="gpt-4-turbo",
                max_tokens=1000,
                messages=out_messages,
                tools=available_tools
            )

            out_messages, out_reason = await handle(r, out_messages)

                    
        return "\n".join([x['content'] for x in out_messages[1:]])

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()