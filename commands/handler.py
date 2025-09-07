"""
Command handler for j4ne.

This module provides the core CommandHandler class that manages command registration
and execution.
"""

import logging
from typing import Dict, Callable, List, Optional, Any

logger = logging.getLogger(__name__)

class Command:
    """Represents a command that can be executed by the user."""
    
    def __init__(self, name: str, handler: Callable, description: str = "", aliases: List[str] = None):
        """
        Initialize a new command.
        
        Args:
            name: The name of the command (without the '/' prefix)
            handler: The function to call when the command is executed
            description: A description of what the command does
            aliases: Alternative names for the command
        """
        self.name = name
        self.handler = handler
        self.description = description
        self.aliases = aliases or []
    
    def matches(self, command_name: str) -> bool:
        """Check if the given name matches this command."""
        return command_name == self.name or command_name in self.aliases

class CommandHandler:
    """Handles the registration and execution of commands."""
    
    def __init__(self):
        """Initialize a new command handler."""
        self.commands: Dict[str, Command] = {}
    
    def register(self, command: Command) -> None:
        """
        Register a command with the handler.
        
        Args:
            command: The command to register
        """
        self.commands[command.name] = command
        logger.debug(f"Registered command: /{command.name}")
    
    def register_function(self, name: str, handler: Callable, description: str = "", aliases: List[str] = None) -> None:
        """
        Register a function as a command.
        
        Args:
            name: The name of the command (without the '/' prefix)
            handler: The function to call when the command is executed
            description: A description of what the command does
            aliases: Alternative names for the command
        """
        command = Command(name, handler, description, aliases)
        self.register(command)
    
    def handle_message(self, message: str) -> Optional[Any]:
        """
        Handle a message, executing a command if it starts with '/'.
        
        Args:
            message: The message to handle
            
        Returns:
            The result of the command handler if a command was executed,
            or None if the message wasn't a command or no matching command was found.
        """
        if not message.startswith('/'):
            return None
        
        # Extract the command name and arguments
        parts = message[1:].split(maxsplit=1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Find the command
        for cmd in self.commands.values():
            if cmd.matches(command_name):
                logger.debug(f"Executing command: /{command_name}")
                try:
                    return cmd.handler(args)
                except Exception as e:
                    logger.error(f"Error executing command /{command_name}: {str(e)}")
                    return f"Error executing command: {str(e)}"
        
        return f"Unknown command: /{command_name}"
    
    def get_help(self) -> str:
        """Get help text listing all available commands."""
        if not self.commands:
            return "No commands available."
        
        help_text = "Available commands:\n"
        for name, cmd in sorted(self.commands.items()):
            aliases = f" (aliases: {', '.join(cmd.aliases)})" if cmd.aliases else ""
            help_text += f"/{name}{aliases}: {cmd.description}\n"
        
        return help_text

# Create a global command handler instance
command_handler = CommandHandler()

