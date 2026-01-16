from rich.console import Console
import time
from typing import Optional

# Import the enhanced chat command functions
from commands.bot_commands import show_tool_call, show_conversation_summary, chat_command
from commands.bot_commands import ConversationLogger

# Rich console for pretty output
console = Console()

def handle_message(message: str) -> str:
    """
    Handle incoming messages - both for chat commands and traditional messages
    """
    if message.startswith('/'):
        # Handle slash commands
        return handle_slash_command(message)
    else:
        # Handle regular messages - just return empty to indicate it should be processed as chat
        return ""

def handle_slash_command(command: str) -> str:
    """
    Handle slash commands like /chat, /help, etc.
    """
    parts = command.split()
    if not parts:
        return "No command provided"

    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    if cmd == '/chat':
        # Enhanced chat command with defaults
        # Extract message and flags
        message_parts = []
        thinking = True  # 🚀 DEFAULT: Now True by default
        tools = True     # 🚀 DEFAULT: Now True by default
        verbose = False
        
        # Parse the arguments
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '--thinking':
                thinking = True
            elif arg == '--no-thinking':
                thinking = False
            elif arg == '--tools':
                tools = True
            elif arg == '--no-tools':
                tools = False
            elif arg == '--verbose':
                verbose = True
            else:
                # Treat as part of the message
                message_parts.append(arg)
            i += 1
        
        message = ' '.join(message_parts)
        if not message:
            return "Please provide a message for /chat"
        
        # Get the current client instance
        from tools.direct_client import DirectClient
        client = DirectClient.get_instance()
        
        if client is None:
            return "No active chat client found"
        
        # 🚀 NEW: Use defaults (thinking=True, tools=True) or override with flags
        chat_command(client, message, thinking=thinking, tools=tools, verbose=verbose)
        return None  # Return None to indicate the command was handled internally

    elif cmd == '/help':
        show_help()
        return None

    elif cmd in ('/quit', '/exit'):
        return "QUIT"

    else:
        return f"Unknown command: {cmd}\nAvailable commands: /chat, /help, /quit"

def show_help():
    """Show available commands"""
    help_text = """
[bold green]Available Commands:[/bold green]

• [cyan]/chat "message"[/cyan] - Enhanced chat with thinking indicators and tool visibility
• [cyan]/chat "message" --no-thinking --no-tools[/cyan] - Enhanced chat with features disabled
• [cyan]/help[/cyan] - Show this help message
• [cyan]/quit[/cyan] - Exit the chat

[bold yellow]Features (now ON by default):[/bold yellow]
• [green]--thinking[/green] - Shows thinking spinner and timing (enabled by default)
• [green]--no-thinking[/green] - Disable thinking indicators
• [green]--tools[/green] - Displays tool execution details (enabled by default) 
• [green]--no-tools[/green] - Disable tool visibility
• [green]--verbose[/green] - Show detailed tool information

[dim]Tip: --thinking and --tools are now enabled automatically! Use --no-thinking or --no-tools to disable them.[/dim]
    """
    console.print(help_text)

# Enhanced chat loop function that uses the Rich UI by default
async def enhanced_chat_loop(client):
    """
    Enhanced chat loop with Rich UI features enabled by default
    """
    console.print("\n[bold cyan]Enhanced Chat Started![/]")
    console.print("[dim]Thinking indicators and tool visibility are enabled by default[/]")
    console.print("Type your queries, '/help' for commands, or '/quit' to exit.\n")
    
    logger = ConversationLogger()
    
    # Initialize history if not already done
    if not hasattr(client, 'history'):
        client.history = []
    
    while True:
        try:
            query = input("> ").strip()
            
            # Check if this is a command
            if query.startswith('/'):
                result = handle_message(query)
                if result == "QUIT":
                    break
                elif result:
                    console.print(result)
                    continue
            # Legacy support for 'quit' and 'exit' without slash
            elif query.lower() in ('quit', 'exit'):
                break
            
            if not query:
                continue
            
            # Add to history
            client.history.append({'role': 'user', 'content': query})
            
            # 🚀 DEFAULTS: thinking=True, tools=True for all chat
            thinking_display = None
            start_time = time.time()
            
            try:
                # Show thinking indicator by default
                thinking_display = console.status("[bold blue]Thinking...[/bold blue]", spinner="dots")
                thinking_display.start()
                
                # Process the query
                response = await client.process_query(list(client.history))
                
                # Stop thinking display
                thinking_time = time.time() - start_time
                thinking_display.stop()
                
                # Show thinking time by default
                console.print(f"[dim]💭 Thought for {thinking_time:.2f} seconds[/dim]")
                
                # Display response with Rich formatting
                console.print("\n[bold]Response:[/bold]")
                console.print(response)
                
                # Log the conversation
                logger.log_conversation(
                    user_input=query,
                    assistant_response=response,
                    thinking_time=thinking_time
                )
                
                # Add response to history
                client.history.append({'role': 'assistant', 'content': response})
                
            except Exception as e:
                if thinking_display:
                    thinking_display.stop()
                console.print(f"[red]Error: {e}[/red]")
                import traceback
                traceback.print_exc()
                
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Goodbye![/]")
            break
        except Exception as e:
            console.print(f"[red]Error in chat loop: {e}[/red]")
            import traceback
            traceback.print_exc()