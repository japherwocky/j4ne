"""
Tools command for j4ne.

This module provides a command to list all available tools for the LLM.
"""

import logging
import os
from rich.console import Console
from rich.table import Table
from commands.handler import command_handler

# Import the tool providers to access their tools
from tools.direct_tools import (
    DirectMultiplexer,
    FilesystemToolProvider,
    SQLiteToolProvider,
)

logger = logging.getLogger(__name__)
console = Console()

def register_tools_command():
    """Register the tools command with the command handler."""
    
    def tools_command(args: str) -> str:
        """Handler for the tools command."""
        # Create instances of the tool providers
        current_dir = os.path.abspath(os.getcwd())
        fs_provider = FilesystemToolProvider(root_path=current_dir)
        sqlite_provider = SQLiteToolProvider("database.db")
        
        # Get all tools from the providers
        all_tools = []
        all_tools.extend(fs_provider.get_tools())
        all_tools.extend(sqlite_provider.get_tools())
        
        # Create a table to display the tools
        table = Table(title="Available LLM Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        
        # Add each tool to the table
        for tool in sorted(all_tools, key=lambda t: t.name):
            table.add_row(tool.name, tool.description)
        
        # Render the table to the console
        console.print(table)
        
        # Return a simple message (the table is already printed)
        return f"Listed {len(all_tools)} available tools."

    command_handler.register_function(
        "tools",
        tools_command,
        "List all available tools for the LLM",
        ["t"]
    )

