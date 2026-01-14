"""Direct Client Implementation - A client that uses the direct tools architecture.

This module provides a client that uses the DirectMultiplexer to call tools directly
as Python functions rather than through subprocess communication.

Tool Access Control:
- By default, all tools are available
- Pass allowed_tools=[...] to restrict tools for specific clients (e.g., Slack)
- Tools are filtered by name prefix (e.g., "filesystem", "sqlite", "git")
"""

import os
import json
import asyncio
import logging
from collections import deque
from typing import List, Dict, Any, Optional, Set

from openai import OpenAI
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
from tools.web_search_tool_simple import WebSearchToolProvider
from tools.github_tool_simple import GitHubToolProvider
# Import the command handler from the new location
from commands import command_handler

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger('direct_client')

# Rich console for pretty output
console = Console()


# ---- Safe Tools Configuration ----

# ---- CLI-LOCAL TOOLS (NEVER expose to Slack) ----
# Tools that access local filesystem and require trusted environment
CLI_LOCAL_TOOLS: Set[str] = {
    "filesystem.read-file",
    "filesystem.list-files",
    "filesystem.glob",
    "filesystem.write-file",
    "filesystem.delete-file",
    "sqlite.read-query",
    "sqlite.list-tables",
    "sqlite.describe-table",
    "sqlite.write-query",
    "sqlite.create-table",
    "sqlite.append-insight",
    "git.status",
    "git.log",
    "git.diff",
    "git.add",
    "git.commit",
    "git.branch",
    "bash.execute",
    "grep.search",
}

# ---- SLACK-SAFE TOOLS (Public/Remote tools only) ----
# Tools that are safe to expose to public Slack users
# These tools only access public APIs and don't touch local filesystem
SLACK_TOOLS: Set[str] = {
    "web.search",
    "github.explore-repo",
    "github.search-repos",
    "github.get-file",
}

# ---- Legacy compatibility ----
# Tools that are safe for CLI/IRC (includes all CLI_LOCAL_TOOLS)
SAFE_TOOLS: Set[str] = CLI_LOCAL_TOOLS.copy()

# Tools that require write access (potentially dangerous) - for CLI only
WRITE_TOOLS: Set[str] = {
    "filesystem.write-file",
    "filesystem.delete-file",
    "sqlite.write-query",
    "sqlite.create-table",
    "sqlite.append-insight",
    "git.add",
    "git.commit",
    "git.branch",
}


class DirectClient:
    """Client that uses the DirectMultiplexer to call tools directly"""

    # Class variable to store the singleton instance
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of DirectClient"""
        return cls._instance

    def __init__(self, root_path: str = "./", db_path: str = "./database.db",
                 allowed_tools: Optional[Set[str]] = None, context: str = "cli"):
        """Initialize the client with tool providers

        Args:
            root_path: Root path for filesystem tools
            db_path: Path to SQLite database
            allowed_tools: Set of tool names allowed for this client.
                          If None, all tools are available.
                          Use SAFE_TOOLS for read-only access.
            context: Context in which the client is being used ("cli" or "slack")
        """
        logger.info(f"Initializing DirectClient (allowed_tools: {allowed_tools}, context: {context})")
        self.context = context

        # Set this instance as the singleton instance
        DirectClient._instance = self

        # Store allowed tools (None means all tools allowed)
        self.allowed_tools = allowed_tools

        # Initialize history
        self.history = deque(maxlen=8)

        # Set up the multiplexer with tool providers
        self.multiplexer = DirectMultiplexer()

        # Add filesystem tools (CLI only, NOT for Slack)
        if self.context != "slack":
            fs_provider = FilesystemToolProvider(root_path)
            self.multiplexer.add_provider(fs_provider)

            # Add SQLite tools (CLI only, NOT for Slack)
            sqlite_provider = SQLiteToolProvider(db_path)
            self.multiplexer.add_provider(sqlite_provider)

            # Add Git tools (CLI only, NOT for Slack)
            git_provider = GitToolProvider(root_path)
            self.multiplexer.add_provider(git_provider)

        # Add Web Search tools (Slack-safe)
        web_provider = WebSearchToolProvider()
        self.multiplexer.add_provider(web_provider)

        # Add GitHub tools (Slack-safe - public repos only)
        github_provider = GitHubToolProvider()
        self.multiplexer.add_provider(github_provider)

        # Set up OpenCode Zen client
        self._setup_opencode_zen_client()

        # Log available tools
        all_tools = self.multiplexer.get_available_tools()
        if self.allowed_tools is not None:
            filtered = [t for t in all_tools if t["function"]["name"] in self.allowed_tools]
            logger.info(f"DirectClient initialized with {len(filtered)}/{len(all_tools)} tools (filtered)")
        else:
            logger.info(f"DirectClient initialized with all {len(all_tools)} tools")

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get definitions of available tools, filtered by allowed_tools if set"""
        all_tools = self.multiplexer.get_available_tools()

        if self.allowed_tools is None:
            return all_tools

        # Filter to only allowed tools
        filtered = [t for t in all_tools if t["function"]["name"] in self.allowed_tools]
        logger.debug(f"Filtered tools: {len(filtered)} allowed from {len(all_tools)} total")
        return filtered

    def _setup_opencode_zen_client(self):
        """Set up the OpenCode Zen client using environment variables"""
        try:
            # Get API key from environment variables
            api_key = os.getenv('OPENCODE_ZEN_API_KEY')

            if not api_key:
                logger.warning("Missing OpenCode Zen API key")
                raise ValueError(
                    "Missing OPENCODE_ZEN_API_KEY environment variable. "
                    "Set it using 'export OPENCODE_ZEN_API_KEY=your_key' or add it to your .env file. "
                    "Get your API key from: https://opencode.ai/auth"
                )

            # Set up the OpenAI client to use OpenCode Zen's endpoint
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://opencode.ai/zen/v1"
            )

            # Store model configuration from environment variables
            self.default_model = os.getenv('OPENCODE_ZEN_MODEL', 'gpt-5.1-codex')
            self.followup_model = os.getenv('OPENCODE_ZEN_FOLLOWUP_MODEL', 'gpt-5.1-codex-mini')

            logger.info(f"OpenCode Zen client initialized successfully with model: {self.default_model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenCode Zen client: {str(e)}")
            raise

    async def process_query(self, history: List[Dict[str, str]]) -> str:
        """Process a query using available tools"""
        logger.info("Processing query")

        # Add system prompt if not present
        if not history or history[0].get("role") != "system":
            if self.context == "slack":
                system_content = "You are j4ne, a helpful AI assistant. You communicate through Slack and your name is j4ne. When users ask about your identity or name, you should confidently identify yourself as j4ne. You're here to help with various tasks and conversations."
            else:  # cli context
                system_content = "You are j4ne, a helpful AI assistant. Your name is j4ne. When users ask about your identity or name, you should confidently identify yourself as j4ne. You're here to help with various tasks and conversations through this command-line interface."
            
            system_prompt = {
                "role": "system",
                "content": system_content
            }
            history = [system_prompt] + history

        # Get available tools (filtered based on allowed_tools)
        available_tools = self.get_available_tools()
        logger.debug(f"Available tools: {len(available_tools)}")

        # Initial LLM call
        try:
            init = self.client.chat.completions.create(
                model=self.default_model,
                max_tokens=3000,
                messages=history,
                tools=available_tools
            )

            # Process the response
            out_messages, out_reason = await self._handle_response(init, history)

            # Continue processing if needed
            while out_reason != 'stop':
                # Keep passing tool responses back
                r = self.client.chat.completions.create(
                    model=self.followup_model,
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
            messages.append({"role": "assistant", "content": content.message.content})

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

            # Check if tool is allowed
            if self.allowed_tools is not None and tool_name not in self.allowed_tools:
                logger.warning(f"Tool {tool_name} is not allowed, skipping")
                messages.append({
                    "role": "assistant",
                    "content": f"Tool {tool_name} is not available. Only read-only operations are permitted."
                })
                return messages, 'stop'

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
        
        # Clean up async tool providers that have resources
        for provider in self.multiplexer.providers:
            if hasattr(provider, 'cleanup'):
                try:
                    await provider.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up provider {type(provider).__name__}: {e}")
