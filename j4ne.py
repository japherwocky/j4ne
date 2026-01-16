import colorama
colorama.init()
import tornado  # this sets up logging
import logging
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
import uvicorn

import asyncio
import typer
from typing import Optional
import os

logger = logging.getLogger()
logger.setLevel("INFO")

channel = logging.StreamHandler()
channel.setFormatter(tornado.log.LogFormatter())
logger.addHandler(channel)

from chatters import chat_loop
from starlette.responses import PlainTextResponse
# --- Import network clients ---
from networks import IRCClient, SlackClient
# --- Import Slack HTTP routes for production mode ---
from networks.slack_http import get_slack_routes
# --- Import DirectClient with tool filtering ---
from tools.direct_client import DirectClient, SAFE_TOOLS, SLACK_TOOLS

def home(request):
    # Simple home page response
    return PlainTextResponse("J4NE Chat Bot - Use 'j4ne chat' to start chatting or 'j4ne --help' for more options.")

# Main app routes
routes = [
    Route("/", endpoint=home),
]

async def start_web_server_with_networks():
    """
    Starts the Starlette web server with IRC and Slack clients.
    Supports both Socket Mode (development) and HTTP mode (production).
    """
    chat_client = None
    chat_client_full = None  # For IRC (trusted environment)
    slack_client = None

    # Determine Slack mode from environment or auto-detect
    slack_mode = os.getenv('SLACK_MODE', 'auto').lower()
    slack_signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    slack_app_token = os.getenv('SLACK_APP_TOKEN')

    # Auto-detect mode: HTTP if signing secret available, otherwise Socket Mode
    if slack_mode == 'auto':
        if slack_signing_secret:
            slack_mode = 'http'
            logger.info("Auto-detected Slack mode: HTTP (signing secret available)")
        elif slack_app_token:
            slack_mode = 'socket'
            logger.info("Auto-detected Slack mode: Socket Mode (app token available)")
        else:
            slack_mode = 'http'
            logger.info("Auto-detected Slack mode: HTTP (default)")

    logger.info(f"Using Slack mode: {slack_mode}")

    # Initialize full chat client for IRC (trusted, gets all tools)
    try:
        chat_client_full = DirectClient(allowed_tools=None)  # All tools
        await chat_client_full.connect_to_server()
        logger.info("Full chat client initialized for IRC")
    except Exception as e:
        logger.warning(f"Failed to initialize full chat client: {e}")

    # Initialize restricted chat client for Slack (no tools, conversational only)
    try:
        chat_client_slack = DirectClient(allowed_tools=SLACK_TOOLS, context="slack")
        logger.info("Chat client initialized for Slack (no tools)")
    except Exception as e:
        logger.warning(f"Failed to initialize Slack chat client: {e}")
        chat_client_slack = None

    # Use the restricted client for Slack
    chat_client = chat_client_slack

    # Initialize IRC client (uses full client for all tools)
    irc_client = IRCClient(chat_client=chat_client_full)

    # Start IRC client in background
    if irc_client.server:  # Only start if IRC is configured
        logger.info("Starting IRC client...")
        success = await irc_client.connect()
        if success:
            logger.info(f"IRC client connected to {irc_client.server}")
        else:
            logger.warning("Failed to connect to IRC")
    else:
        logger.info("IRC not configured, skipping IRC client startup")

    # Initialize Slack client with appropriate mode
    slack_client = SlackClient(chat_client=chat_client, mode=slack_mode)

    # Start Slack client based on mode
    if slack_mode == 'socket':
        # Socket Mode: requires bot_token AND app_token
        if slack_client.bot_token and slack_client.app_token:
            logger.info("Starting Slack client via Socket Mode...")
            success = await slack_client.connect()
            if success:
                logger.info("Slack client connected via Socket Mode")
            else:
                logger.warning("Failed to connect to Slack via Socket Mode")
        else:
            logger.info("Slack tokens not configured for Socket Mode, skipping Slack client startup")
    else:
        # HTTP mode: only requires bot_token (for API calls) and signing_secret (for webhooks)
        if slack_client.bot_token:
            logger.info("Starting Slack client via HTTP mode...")
            success = await slack_client.connect()
            if success:
                logger.info("Slack client ready via HTTP mode (webhooks active)")
            else:
                logger.warning("Failed to initialize Slack client for HTTP mode")
        else:
            logger.info("Slack bot token not configured, skipping Slack client startup")

    # Build routes (include Slack HTTP routes for production mode)
    app_routes = [
        Route("/", endpoint=home),
    ]

    # Add Slack HTTP routes in production mode
    if slack_mode == 'http':
        app_routes.extend(get_slack_routes())
        logger.info("Slack HTTP webhook routes registered")

    # Create Starlette app
    app = Starlette(debug=True, routes=app_routes)
    
    # Start web server
    logger.info("Starting Starlette web server...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    finally:
        # Cleanup network clients
        if irc_client and irc_client.connected:
            await irc_client.disconnect()
        if slack_client and slack_client.connected:
            await slack_client.disconnect()
        if chat_client:
            await chat_client.cleanup()

def start_web_server():
    """
    Starts the Starlette web server (legacy sync wrapper).
    """
    asyncio.run(start_web_server_with_networks())

# Create the Typer app
app = typer.Typer(
    name="j4ne",
    help="A chat bot with data visualizations for IRC and Slack",
    no_args_is_help=False,  # Allow running without args to default to chat
)

@app.command()
def chat(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging for debugging.")
):
    """Start an interactive chat loop (default command)."""
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled.")
    
    logger.info("Starting the chat loop...")
    from chatters import EmCeePee
    asyncio.run(EmCeePee())

@app.command()
def greet(
    name: str = typer.Argument(..., help="Name to greet."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging for debugging.")
):
    """Send a greeting to someone."""
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled.")
    
    handle_greet(name)

@app.command()
def web(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging for debugging.")
):
    """Start the Starlette web server with IRC and Slack clients."""
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled.")
    
    start_web_server()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging for debugging.")
):
    """
    A chat bot with data visualizations for IRC and Slack.
    
    If no command is specified, defaults to the 'chat' command.
    """
    if ctx.invoked_subcommand is None:
        # Default to chat command when no subcommand is provided
        if verbose:
            logger.setLevel(logging.DEBUG)
            logger.debug("Verbose mode enabled.")
        
        logger.info("Starting the chat loop...")
        from chatters import EmCeePee
        asyncio.run(EmCeePee())


def handle_greet(name):
    """
    Handle the 'greet' command.
    """
    logger.info(f"Greeting {name}!")  # Log message styled by Tornado LogFormatter


if __name__ == "__main__":
    app()