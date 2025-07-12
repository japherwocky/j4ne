"""
Command system for j4ne.

This module provides a framework for handling commands that start with '/'.
Commands are registered with the CommandHandler and can be executed when
a message starts with '/'.
"""

from commands.handler import command_handler
from commands.core import register_core_commands
from commands.tools_command import register_tools_command

# Register the core commands
register_core_commands()

# Register the tools command
register_tools_command()

