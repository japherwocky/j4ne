"""
Core commands for j4ne.

This module provides the basic commands that are available in j4ne.
"""

import os
import logging
from commands.handler import command_handler

logger = logging.getLogger(__name__)

def register_core_commands():
    """Register all core commands with the command handler."""
    
    # Register the quit command
    def quit_command(_: str) -> str:
        """Handler for the quit command."""
        return "QUIT"

    command_handler.register_function(
        "quit", 
        quit_command,
        "Exit the application",
        ["exit", "bye"]
    )

    # Register the help command
    def help_command(args: str) -> str:
        """Handler for the help command."""
        if args:
            # Show help for a specific command
            command_name = args.strip().lower()
            for name, cmd in command_handler.commands.items():
                if cmd.matches(command_name):
                    aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
                    return f"/{name}{aliases}: {cmd.description}"
            return f"Unknown command: /{command_name}"
        
        # Show help for all commands
        return command_handler.get_help()

    command_handler.register_function(
        "help",
        help_command,
        "Show help for available commands",
        ["?"]
    )

    # Register a clear command to clear the console
    def clear_command(_: str) -> str:
        """Handler for the clear command."""
        os.system('cls' if os.name == 'nt' else 'clear')
        return "Console cleared."

    command_handler.register_function(
        "clear",
        clear_command,
        "Clear the console",
        ["cls"]
    )

    # Register a version command
    def version_command(_: str) -> str:
        """Handler for the version command."""
        return "j4ne v0.1.0"

    command_handler.register_function(
        "version",
        version_command,
        "Show the version of j4ne",
        ["v"]
    )

