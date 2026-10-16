import colorama
colorama.init()
import tornado  # this sets up logging
import logging
import logging.handlers
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
import uvicorn

import asyncio
import typer
from typing import Optional
import os

# Get the directory where this script is located (for reliable paths in service mode)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def setup_logging(verbose=False, to_file=True, console_output=False):
    """
    Setup logging with file rotation and optional console output.
    
    Args:
        verbose: Enable DEBUG level logging
        to_file: Write logs to ./logs/j4ne.log
        console_output: Also show logs in console (for web server)
    """
    # Get root logger (tornado already set it up)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set up formatter (keep tornado formatting)
    formatter = tornado.log.LogFormatter()
    
    if to_file:
        # Create logs directory using BASE_DIR for reliable paths
        logs_dir = os.path.join(BASE_DIR, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Rotating file handler (10MB per file, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, 'j4ne.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Console output for verbose mode or web server
    if verbose or console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

# Default logging setup (for imports and initial setup)
logger = setup_logging(verbose=False, to_file=True, console_output=False)

from chatters import chat_loop
from starlette.responses import PlainTextResponse
# --- Import network clients ---
from networks import IRCClient, SlackClient
# --- Import Slack HTTP routes for production mode ---
from networks.slack_http import get_slack_routes
# --- Import DirectClient with tool filtering ---
from tools.direct_client import DirectClient, PUBLIC_TOOLS
# --- Import Proactive Agent ---
from proactive import ProactiveAgent

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
    chat_client_irc = None
    chat_client_slack = None
    slack_client = None
    irc_client = None

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

    # IRC is opt-in: anyone in the channel can talk to the bot, so it gets
    # the same public tools as Slack, never the filesystem, git or SQLite
    if os.getenv('IRC_SERVER'):
        try:
            chat_client_irc = DirectClient(allowed_tools=PUBLIC_TOOLS, context="irc")
            logger.info("Chat client initialized for IRC (public tools only)")
        except Exception as e:
            logger.warning(f"Failed to initialize IRC chat client: {e}")

        irc_client = IRCClient(chat_client=chat_client_irc)
        logger.info("Starting IRC client...")
        if await irc_client.connect():
            logger.info(f"IRC client connecting to {irc_client.server}")
        else:
            logger.warning("Failed to connect to IRC")
    else:
        logger.info("IRC_SERVER not set, skipping IRC client startup")

    # Initialize restricted chat client for Slack (public tools only)
    try:
        chat_client_slack = DirectClient(allowed_tools=PUBLIC_TOOLS, context="slack")
        logger.info("Chat client initialized for Slack (public tools only)")
    except Exception as e:
        logger.warning(f"Failed to initialize Slack chat client: {e}")

    # Initialize Slack client with appropriate mode
    slack_client = SlackClient(chat_client=chat_client_slack, mode=slack_mode)

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

    # Initialize and start proactive agent
    proactive_agent = ProactiveAgent()
    if proactive_agent.enabled:
        proactive_agent.start()
    else:
        logger.info("Proactive agent disabled (set PROACTIVE_INTERVAL_SECONDS > 0 to enable)")

    # Create Starlette app. Not debug: that serves tracebacks to whoever
    # reaches the server, and in production nginx proxies the internet to it.
    app = Starlette(debug=False, routes=app_routes)

    # Start web server. nginx proxies to 127.0.0.1:8000, so that is the
    # default; set J4NE_HOST=0.0.0.0 to listen on every interface.
    host = os.getenv('J4NE_HOST', '127.0.0.1')
    port = int(os.getenv('J4NE_PORT', '8000'))
    logger.info(f"Starting Starlette web server on {host}:{port}...")
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        # Cleanup proactive agent
        if proactive_agent:
            await proactive_agent.stop()

        # Cleanup network clients
        if irc_client:
            await irc_client.disconnect()
        if slack_client and slack_client.connected:
            await slack_client.disconnect()
        for chat_client in (chat_client_irc, chat_client_slack):
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
    # Setup logging for chat mode
    setup_logging(verbose=verbose, to_file=True, console_output=False)
    
    if verbose:
        logger.debug("Verbose mode enabled - logs will be written to ./logs/j4ne.log")
    else:
        logger.info("Chat mode started - logs are being written to ./logs/j4ne.log")
    
    from chatters import EmCeePee
    asyncio.run(EmCeePee())

@app.command()
def greet(
    name: str = typer.Argument(..., help="Name to greet."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging for debugging.")
):
    """Send a greeting to someone."""
    # Setup logging for greet command
    setup_logging(verbose=verbose, to_file=True, console_output=False)
    
    if verbose:
        logger.debug("Verbose mode enabled - logs will be written to ./logs/j4ne.log")
    
    handle_greet(name)

@app.command()
def web(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging for debugging.")
):
    """Start the Starlette web server with IRC and Slack clients."""
    # Setup logging for web mode (always show console output for web server)
    setup_logging(verbose=verbose, to_file=True, console_output=True)
    
    if verbose:
        logger.debug("Verbose mode enabled - logs will be written to ./logs/j4ne.log AND shown in console")
    else:
        logger.info("Web server mode started - logs are being written to ./logs/j4ne.log AND shown in console")
    
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
        # Setup logging for default chat mode
        setup_logging(verbose=verbose, to_file=True, console_output=False)
        
        if verbose:
            logger.debug("Verbose mode enabled - logs will be written to ./logs/j4ne.log")
        else:
            logger.info("Chat mode started - logs are being written to ./logs/j4ne.log")
        
        from chatters import EmCeePee
        asyncio.run(EmCeePee())


def handle_greet(name):
    """
    Handle the 'greet' command.
    """
    # Printed, not only logged: the log has no console handler in this mode
    typer.echo(f"Hello {name}!")
    logger.info(f"Greeting {name}!")  # Log message styled by Tornado LogFormatter


if __name__ == "__main__":
    app()