from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live
from rich.table import Table
from rich.markdown import Markdown
from typing import Optional
import json
import time
from datetime import datetime

console = Console()

class ConversationLogger:
    def __init__(self, log_file: str = "logs/conversations.jsonl"):
        self.log_file = log_file
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def log_conversation(self, user_input: str, assistant_response: str, 
                        tools_used: list = None, thinking_time: float = None):
        """Log conversation to JSONL file"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "tools_used": tools_used or [],
            "thinking_time": thinking_time
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def chat_command(client, message: str, 
                thinking: bool = True,  # Default to True
                tools: bool = True,    # Default to True  
                verbose: bool = False):
    """
    Enhanced chat command with Rich UI features
    """
    logger = ConversationLogger()
    
    # Setup Rich UI based on flags
    if thinking:
        thinking_display = Live(
            Spinner("dots", text="Thinking..."), 
            console=console, 
            refresh_per_second=10
        )
        thinking_display.start()
        start_time = time.time()
    
    try:
        # Process the chat message through the client
        response = asyncio.run(client.process_query([{"role": "user", "content": message}]))
        
        if thinking:
            thinking_time = time.time() - start_time
            thinking_display.stop()
            
            # Show thinking time
            console.print(f"[dim]Thought for {thinking_time:.2f} seconds[/dim]")
        
        # Display response with Rich formatting
        console.print("\n[bold]Response:[/bold]")
        console.print(Markdown(response))
        
        # Log the conversation
        logger.log_conversation(
            user_input=message,
            assistant_response=response,
            thinking_time=thinking_time if thinking else None
        )
        
    except Exception as e:
        if thinking:
            thinking_display.stop()
        console.print(f"[red]Error: {e}[/red]")

def show_tool_call(tool_name: str, args: dict, result: str, verbose: bool = False):
    """Display tool execution information"""
    if verbose:
        table = Table(title=f"🔧 Tool Call: {tool_name}")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in args.items():
            table.add_row(key, str(value))
        
        console.print(table)
        console.print(f"[dim]Result: {result[:200]}...[/dim]")
    else:
        console.print(f"🔧 [cyan]{tool_name}[/cyan] called")

def show_conversation_summary(user_input: str, response: str, tools_used: list = None):
    """Show a summary of the conversation"""
    panel_content = f"[bold]You:[/bold] {user_input}\n\n[bold]j4ne:[/bold] {response[:100]}..."
    
    if tools_used:
        panel_content += f"\n\n[dim]Tools used: {', '.join(tools_used)}[/dim]"
    
    console.print(Panel(
        panel_content,
        title="💬 Conversation",
        border_style="blue"
    ))