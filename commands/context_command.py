"""
Context command for j4ne.

This module provides a command to show information about the current chat context.
"""

import logging
import tiktoken
from rich.console import Console
from rich.table import Table
from commands.handler import command_handler

logger = logging.getLogger(__name__)
console = Console()

# Function to count tokens in a message
def count_tokens(text, model="gpt-3.5-turbo"):
    """Count the number of tokens in a text string."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        # Fallback: rough estimate (1 token ≈ 4 chars)
        return len(text) // 4

def register_context_command():
    """Register the context command with the command handler."""
    
    def context_command(args: str) -> str:
        """Handler for the context command."""
        from tools.direct_client import DirectClient
        
        # Get the history from the DirectClient instance
        client = DirectClient.get_instance()
        if not client or not hasattr(client, 'history'):
            return "No chat context available. Start a conversation first."
        
        history = list(client.history)
        if not history:
            return "Chat context is empty. Start a conversation first."
        
        # Count messages by role
        user_messages = sum(1 for msg in history if msg.get('role') == 'user')
        assistant_messages = sum(1 for msg in history if msg.get('role') == 'assistant')
        
        # Count tokens
        total_tokens = 0
        for msg in history:
            content = msg.get('content', '')
            tokens = count_tokens(content)
            total_tokens += tokens
        
        # Create a table to display the context info
        table = Table(title="Chat Context Information")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Messages in Context", str(len(history)))
        table.add_row("User Messages", str(user_messages))
        table.add_row("Assistant Messages", str(assistant_messages))
        table.add_row("Maximum Context Size", "8 messages")
        table.add_row("Estimated Total Tokens", str(total_tokens))
        table.add_row("Token Limit per Response", "3000")
        
        # Render the table to the console
        console.print(table)
        
        # Return a simple message (the table is already printed)
        return f"Displayed context information for {len(history)} messages."

    command_handler.register_function(
        "context",
        context_command,
        "Show information about the current chat context",
        ["ctx"]
    )

