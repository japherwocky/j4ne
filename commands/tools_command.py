"""
Tools command for j4ne.

This module provides a command to list all available tools for the LLM.
"""

import logging
from rich.console import Console
from rich.table import Table
from commands.handler import command_handler

logger = logging.getLogger(__name__)
console = Console()

def register_tools_command():
    """Register the tools command with the command handler."""

    def tools_command(args: str) -> str:
        """Handler for the tools command."""
        from tools.direct_client import DirectClient

        # The running client's own tools, after its allowed_tools filter
        client = DirectClient.get_instance()
        if client is None:
            return "No active chat client found"

        all_tools = [tool["function"] for tool in client.get_available_tools()]

        # Create a table to display the tools
        table = Table(title="Available LLM Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")

        # Add each tool to the table
        for tool in sorted(all_tools, key=lambda t: t["name"]):
            table.add_row(tool["name"], tool.get("description", ""))

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
