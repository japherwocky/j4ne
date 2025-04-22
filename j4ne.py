
import colorama
colorama.init()
import tornado  # this sets up logging
import logging

import argparse
import asyncio
from rich.console import Console

# Instantiate Rich Console
console = Console()
logger = logging.getLogger()
logger.setLevel("INFO")

channel = logging.StreamHandler()
channel.setFormatter(tornado.log.LogFormatter())
logger.addHandler(channel)

async def chat_loop():
    """
    Async chat loop that lets the user interact with the CLI in real time.
    """
    console.print("[bold cyan]Welcome to the chat CLI![/] Type '[green]exit[/]' to quit.")
    try:
        while True:
            message = await asyncio.to_thread(input, "> ")  # Use asyncio to avoid blocking
            if message.strip().lower() == "exit":
                console.print("[bold yellow]Goodbye![/]")
                break
            # Simulate processing of the message (replace with real logic)
            console.print(f"[bold green]Echo:[/] {message}")
            logger.info(f"User input: {message}")  # Log to Tornado-style logs
    except KeyboardInterrupt:
        console.print("\n[bold red]Chat interrupted. Goodbye![/]")
        logger.warning("Chat loop interrupted by KeyboardInterrupt")


def main():
    """
    Entry point for the CLI tool.
    """
    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="A custom CLI tool with multiple commands."
    )

    # Define global arguments
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging for debugging."
    )

    # Define subcommands
    subparsers = parser.add_subparsers(
        title="commands", 
        dest="command", 
        help="Available subcommands"
    )

    # Chat subcommand (default functionality)
    chat_parser = subparsers.add_parser(
        "chat", 
        help="Start an interactive chat loop (default command)."
    )

    # Greet subcommand
    greet_parser = subparsers.add_parser(
        "greet", 
        help="Send a greeting to someone."
    )
    greet_parser.add_argument(
        "name", 
        type=str, 
        help="Name to greet."
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled.")

    # Dispatch based on command
    if args.command == "greet":
        handle_greet(args.name)
    elif args.command == "chat" or args.command is None:  # Default to 'chat'
        logger.info("Starting the chat loop...")
        asyncio.run(chat_loop())
    else:
        parser.print_help()


def handle_greet(name):
    """
    Handle the 'greet' command.
    """
    logger.info(f"Greeting {name}!")  # Log message styled by Tornado LogFormatter
    console.print(f"[bold blue]Hello, {name}![/]")  # Pretty CLI output for the user


if __name__ == "__main__":
    main()
