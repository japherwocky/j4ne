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

logger = logging.getLogger()
logger.setLevel("INFO")

channel = logging.StreamHandler()
channel.setFormatter(tornado.log.LogFormatter())
logger.addHandler(channel)

from chatters import chat_loop
from starlette.responses import PlainTextResponse
# --- Import network clients ---
from networks import IRCClient, SlackClient
# --- Import DirectClient with tool filtering ---
from tools.direct_client import DirectClient, SAFE_TOOLS

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
    """
    chat_client = None
    chat_client_full = None  # For IRC (trusted environment)
    slack_client = None

    # Initialize full chat client for IRC (trusted, gets all tools)
    try:
        chat_client_full = DirectClient(allowed_tools=None)  # All tools
        await chat_client_full.connect_to_server()
        logger.info("Full chat client initialized for IRC")
    except Exception as e:
        logger.warning(f"Failed to initialize full chat client: {e}")

    # Initialize restricted chat client for Slack (untrusted, only safe tools)
    try:
        chat_client_slack = DirectClient(allowed_tools=SAFE_TOOLS)
        logger.info("Restricted chat client initialized for Slack")
    except Exception as e:
        logger.warning(f"Failed to initialize restricted chat client: {e}")
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
    
    # Initialize Slack client
    slack_client = SlackClient(chat_client=chat_client)
    
    # Start Slack client in background
    if slack_client.bot_token and slack_client.app_token:  # Only start if Slack is configured
        logger.info("Starting Slack client...")
        success = await slack_client.connect()
        if success:
            logger.info("Slack client connected via Socket Mode")
        else:
            logger.warning("Failed to connect to Slack")
    else:
        logger.info("Slack not configured, skipping Slack client startup")
    
    # Create Starlette app
    app = Starlette(debug=True, routes=routes)
    
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
    help="A chat bot with data visualizations for IRC, Twitch, Discord, and Twitter",
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
    A chat bot with data visualizations for IRC, Twitch, Discord, and Twitter.
    
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
