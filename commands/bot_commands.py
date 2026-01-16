"""
Enhanced bot commands with conversation logging and UI controls.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.live import Live
from rich.status import Status
from rich.panel import Panel
from datetime import datetime
import json
import os
import logging
import asyncio
from collections import deque

console = Console()

def greet_command(args):
    """Greet the user with a personalized message"""
    name = args[0] if args else "Friend"
    return f"Hello {name}! 👋"

def help_command(args):
    """Show help information"""
    return """
**Available Commands:**
- `/greet <name>` - Greet someone
- `/help` - Show this help message
- `/quit` - Exit the program
- `/chat <message>` - Enhanced chat with optional flags

**Enhanced Chat Options:**
- `--thinking` - Show thinking indicator
- `--tools` - Show tool call details
- `--verbose` - Verbose logging mode
- Example: `/chat "list files" --thinking --tools`

**Legacy Commands:**
- `quit` or `exit` - Exit the program
"""

def quit_command(args):
    """Quit the program"""
    return "QUIT"

async def handle_enhanced_chat_command(
    message: str, 
    result_text: str = "", 
    show_thinking: bool = False,
    show_tool_calls: bool = False, 
    verbose: bool = False, 
    context: str = "cli"
):
    """
    Handle enhanced chat with logging, thinking indicators, and tool call visibility.
    
    Args:
        message: The user's message
        result_text: Current result text (for continuation)
        show_thinking: Whether to show thinking indicator
        show_tool_calls: Whether to show tool call details
        verbose: Whether to enable verbose logging
        context: The context ("cli" or "web")
    
    Returns:
        str: The final response
    """
    logger = logging.getLogger('bot_commands')
    
    # Import here to avoid circular imports
    from tools.direct_client import DirectClient
    
    try:
        # Get or create client instance
        client = DirectClient.get_instance()
        if client is None:
            # Create new instance if none exists
            client = DirectClient(context=context)
        
        # Start logging the conversation
        conversation_log = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "user_message": message,
            "assistant_response": None,
            "tool_calls": []
        }
        
        # Create history for this interaction
        history = [{"role": "user", "content": message}]
        
        # Track tool calls for logging and UI
        tool_calls_made = []
        
        # Enhanced thinking and tool call display
        if show_thinking or show_tool_calls:
            with Live(console=console, refresh_per_second=4) as live:
                # Show thinking status
                if show_thinking:
                    thinking_status = Status("🤔 Thinking...", spinner="dots")
                    live.update(thinking_status)
                
                # Process the query with tool call tracking
                try:
                    # Override the tool execution to capture calls
                    original_execute = client.multiplexer.execute_tool
                    
                    def tracked_execute(tool_name, tool_args):
                        # Log the tool call
                        tool_call_info = {
                            "tool": tool_name,
                            "args": tool_args,
                            "timestamp": datetime.now().isoformat()
                        }
                        tool_calls_made.append(tool_call_info)
                        
                        # Show tool call in UI if requested
                        if show_tool_calls:
                            tool_display = Panel(
                                f"🔧 Calling: {tool_name}\n📋 Args: {json.dumps(tool_args, indent=2)}",
                                title="Tool Call",
                                border_style="blue"
                            )
                            live.update(tool_display)
                        
                        # Execute the original tool
                        result = original_execute(tool_name, tool_args)
                        
                        # Log result
                        if show_tool_calls:
                            result_display = Panel(
                                f"✅ Result: {json.dumps(result, indent=2)[:500]}...",
                                title="Tool Result",
                                border_style="green"
                            )
                            live.update(result_display)
                        
                        return result
                    
                    # Temporarily replace the execute method
                    client.multiplexer.execute_tool = tracked_execute
                    
                    # Process the query
                    response = await client.process_query(history)
                    
                    # Restore original method
                    client.multiplexer.execute_tool = original_execute
                    
                    # Show final response
                    response_panel = Panel(
                        Markdown(response),
                        title="Response",
                        border_style="cyan"
                    )
                    live.update(response_panel)
                    
                except Exception as e:
                    logger.error(f"Error in enhanced chat: {e}")
                    error_panel = Panel(
                        f"❌ Error: {str(e)}",
                        title="Error",
                        border_style="red"
                    )
                    live.update(error_panel)
                    return f"Error: {str(e)}"
        
        else:
            # Normal chat without UI enhancements
            response = await client.process_query(history)
            console.print(Markdown(response))
        
        # Log the conversation
        conversation_log["assistant_response"] = response
        conversation_log["tool_calls"] = tool_calls_made
        
        # Save to conversation log file
        await save_conversation_log(conversation_log, verbose)
        
        # If verbose, show conversation summary
        if verbose:
            summary = f"\n📝 Conversation logged:\n"
            summary += f"   User: {message[:50]}...\n"
            summary += f"   Tools used: {len(tool_calls_made)}\n"
            summary += f"   Response length: {len(response)} chars\n"
            console.print(summary)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in enhanced chat: {e}")
        return f"Error: {str(e)}"

async def save_conversation_log(log_entry: dict, verbose: bool = False):
    """Save conversation log to file with rotation"""
    try:
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Use a separate log file for conversations
        log_file = 'logs/conversations.jsonl'
        
        # Append the log entry as JSON line
        with open(log_file, 'a', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write('\n')
        
        # Optional: Log to main logger too
        logger = logging.getLogger('bot_commands')
        logger.info(f"Conversation logged: {log_entry['user_message'][:50]}...")
        
        if verbose:
            console.print(f"💾 Conversation saved to {log_file}")
            
    except Exception as e:
        logger = logging.getLogger('bot_commands')
        logger.error(f"Failed to save conversation log: {e}")