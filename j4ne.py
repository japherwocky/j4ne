import argparse
import asyncio
import logging
import sys

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def chat_loop():
    """
    Async chat loop that lets the user interact with the CLI in real time.
    """
    print("Welcome to the chat CLI! Type 'exit' to quit.")
    try:
        while True:
            message = await asyncio.to_thread(input, "You: ")  # Use asyncio to avoid blocking
            if message.strip().lower() == "exit":
                print("Goodbye!")
                break
            # Simulate processing of the message (you can replace with real logic)
            response = f"Echo: {message}"
            print(response)
    except KeyboardInterrupt:
        print("\nChat interrupted. Goodbye!")

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
        sys.exit(1)

def handle_greet(name):
    """
    Handle the 'greet' command.
    """
    logger.info(f"Greeting {name}!")
    print(f"Hello, {name}!")

if __name__ == "__main__":
    main()