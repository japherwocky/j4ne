"""
Direct Client Implementation - A client that uses the direct tools architecture.

This module provides a client that uses the DirectMultiplexer to call tools directly
as Python functions rather than through subprocess communication.
"""

import os
import json
import asyncio
import logging
from collections import deque
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

# Import the global database connection
from db import db

from tools.direct_tools import (
    DirectMultiplexer,
    FilesystemToolProvider,
    SQLiteToolProvider,
    GitToolProvider,
)
# Import the command handler from the new location
from commands import command_handler

# Import client factory for flexible client creation
from clients import create_client

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('direct_client')

# Rich console for pretty output
console = Console()

class DirectClient:
    """Client that uses the DirectMultiplexer to call tools directly"""
    
    # Class variable to store the singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of DirectClient"""
        return cls._instance
    
    def __init__(self, root_path: str = "./", db_path: str = "./database.db"):
        """Initialize the client with tool providers"""
        logger.info("Initializing DirectClient")
        
        # Set this instance as the singleton instance
        DirectClient._instance = self
        
        # Initialize history
        self.history = deque(maxlen=8)
        
        # Set up the multiplexer with tool providers
        self.multiplexer = DirectMultiplexer()
        
        # Add filesystem tools
        fs_provider = FilesystemToolProvider(root_path)
        self.multiplexer.add_provider(fs_provider)
        
        # Add SQLite tools
        sqlite_provider = SQLiteToolProvider(db_path)
        self.multiplexer.add_provider(sqlite_provider)
        
        # Add Git tools
        git_provider = GitToolProvider(root_path)
        self.multiplexer.add_provider(git_provider)
        
        # Set up inference client (supports both Azure OpenAI and Hugging Face)
        self._setup_inference_client()
        
        logger.info("DirectClient initialized successfully")
    
    def _setup_inference_client(self):
        """Set up the inference client using environment variables"""
        try:
            # Use client factory to create appropriate client
            self.client = create_client(prefer_huggingface=True)
            logger.info("Inference client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize inference client: {str(e)}")
            raise
    
    async def process_query(self, history: List[Dict[str, str]]) -> str:
        """Process a query using available tools"""
        logger.info("Processing query")
        
        # Get available tools
        available_tools = self.multiplexer.get_available_tools()
        logger.debug(f"Available tools: {len(available_tools)}")
        
        # Initial LLM call
        try:
            # Use environment variable for model name, with fallback
            model_name = os.getenv('HF_MODEL_NAME') or os.getenv('OPENAI_MODEL', "gpt-4")
            init = self.client.chat.completions.create(
                model=model_name,
                max_tokens=3000,
                messages=history,
                tools=available_tools
            )
            
            # Process the response
            out_messages, out_reason = await self._handle_response(init, history)
            
            # Continue processing if needed
            while out_reason != 'stop':
                # Keep passing tool responses back
                # Use environment variable for followup model, with fallback
                followup_model = os.getenv('HF_FOLLOWUP_MODEL') or os.getenv('OPENAI_FOLLOWUP_MODEL', "gpt-4.1-mini")
                r = self.client.chat.completions.create(
                    model=followup_model,
                    max_tokens=3000,
                    messages=out_messages,
                    tools=available_tools
                )
                
                out_messages, out_reason = await self._handle_response(r, out_messages)
            
            # Return the final response
            return "\n".join([x['content'] for x in out_messages[-1:]])
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return f"Error processing query: {str(e)}"
    
    async def _handle_response(self, response, messages):
        """Handle a response from the LLM"""
        reason = response.choices[0].finish_reason
        content = response.choices[0]
        
        if reason == 'stop':
            # Regular response
            messages.append({"role": "assistant", "content": content.message['content']})
        
        elif reason == 'tool_calls':
            # Tool call
            content = content.model_dump()
            tool_calls = content['message'].get('tool_calls', [])
            
            if not tool_calls:
                logger.warning("Tool calls indicated but none found")
                messages.append({"role": "assistant", "content": "No tool calls found"})
                return messages, 'stop'
            
            # Process the first tool call (or potentially multiple in the future)
            tool_call = tool_calls[0]
            
            tool_name = tool_call['function']['name']
            tool_args = json.loads(tool_call['function']['arguments'])
            
            logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
            
            # Execute tool directly through the multiplexer
            result = self.multiplexer.execute_tool(tool_name, tool_args)
            
            # Format the result for the message history
            if "error" in result:
                summary = f"""Called tool {tool_name} ({tool_args}), got ERROR: {result["error"]}\n"""
            else:
                summary = f"""Called tool {tool_name} ({tool_args}), got results: {result}\n"""
            
            messages.append({"role": "assistant", "content": summary})
        
        return messages, reason
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        console.print("\nDirect Tool Client Started!")
        console.print("Type your queries or '/quit' to exit.")
        console.print("Type '/help' to see available commands.")
        
        # Initialize history if not already done
        if not hasattr(self, 'history'):
            self.history = deque(maxlen=8)
        
        while True:
            try:
                query = input("\n> ").strip()
                
                # Check if this is a command
                if query.startswith('/'):
                    result = command_handler.handle_message(query)
                    if result == "QUIT":
                        break
                    elif result:
                        console.print(result)
                        continue
                # Legacy support for 'quit' and 'exit' without slash
                elif query.lower() in ('quit', 'exit'):
                    break
                
                self.history.append({'role': 'user', 'content': query})
                console.print('\n')
                
                response = await self.process_query(list(self.history))
                self.history.append({'role': 'assistant', 'content': response})
                console.print(Markdown("\n" + response))
            
            except Exception as e:
                logger.error(f"Error in chat loop: {str(e)}")
                import traceback
                traceback.print_exc()
                break
    
    async def connect_to_server(self):
        """
        Compatibility method with the old MCP client interface.
        In the direct implementation, there's no server to connect to.
        """
        logger.info("Direct client doesn't need to connect to a server")
        # Nothing to do here, as we're not connecting to any server
        pass
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        # Nothing to clean up for now, but this method could be used in the future
