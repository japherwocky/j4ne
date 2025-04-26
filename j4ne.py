import colorama
colorama.init()
import tornado  # this sets up logging
import logging
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

import argparse
import asyncio

logger = logging.getLogger()
logger.setLevel("INFO")

channel = logging.StreamHandler()
channel.setFormatter(tornado.log.LogFormatter())
logger.addHandler(channel)

from chatters import chat_loop

def home(request):
    return JSONResponse({"message": "Hi there! Welcome to the Jane Web Interface. How can we assist you today?"})

routes = [
    Route("/", endpoint=home),
]

def start_web_server():
    """
    Starts the Starlette web server.
    """
    app = Starlette(debug=True, routes=routes)
    logger.info("Starting Starlette web server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

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

    # Web subcommand
    web_parser = subparsers.add_parser(
        "web",
        help="Start the Starlette web server."
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
        from chatters import EmCeePee
        asyncio.run(EmCeePee())
    elif args.command == "web":  # Start the web server
        start_web_server()
    else:
        parser.print_help()


def handle_greet(name):
    """
    Handle the 'greet' command.
    """
    logger.info(f"Greeting {name}!")  # Log message styled by Tornado LogFormatter


if __name__ == "__main__":
    main()