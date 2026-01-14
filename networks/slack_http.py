"""
Slack HTTP webhook receiver for production mode.
Handles Events API requests via HTTPS POST from Slack.
"""

import hmac
import hashlib
import os
import logging
from typing import Optional
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def verify_slack_signature(request: Request) -> bool:
    """
    Verify the X-Slack-Signature header to ensure the request is from Slack.

    Args:
        request: The Starlette request object

    Returns:
        True if signature is valid, False otherwise
    """
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    if not signing_secret:
        logger.error("SLACK_SIGNING_SECRET not configured")
        return False

    # Get the raw body for signature verification
    body = await request.body()
    body = body.decode('utf-8')

    # Get timestamp from header
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    if not timestamp:
        logger.warning("Missing X-Slack-Request-Timestamp header")
        return False

    # Check for replay attack (request older than 5 minutes)
    import time
    try:
        ts_int = int(timestamp)
        if abs(time.time() - ts_int) > 60 * 5:
            logger.warning(f"Slack request timestamp too old (replay attack check): {timestamp}")
            return False
    except (ValueError, TypeError):
        logger.warning(f"Invalid Slack request timestamp: {timestamp}")
        return False

    # Compute the signature
    sig_basestring = f"v0:{timestamp}:{body}"
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    # Get the signature from header
    slack_signature = request.headers.get('X-Slack-Signature', '')

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(my_signature, slack_signature):
        logger.warning("Slack signature verification failed")
        return False

    return True


async def slack_events_handler(request: Request) -> PlainTextResponse:
    """
    Handle Slack Events API HTTP requests.

    This endpoint receives:
    1. URL verification challenge (when setting up Event Subscriptions)
    2. Event payloads (app_mention, message.im, etc.)

    Args:
        request: The Starlette request object containing the Slack payload

    Returns:
        PlainTextResponse with challenge for verification, or "OK" for events
    """
    try:
        # Verify the request is from Slack
        if not await verify_slack_signature(request):
            logger.warning("Rejected request with invalid signature")
            return PlainTextResponse("Invalid signature", status_code=403)

        payload = await request.json()

        # Handle URL verification challenge
        if payload.get('type') == 'url_verification':
            logger.info("Handling URL verification challenge")
            return PlainTextResponse(payload.get('challenge', ''))

        # Get the global SlackClient instance
        from networks.slack import SlackClient
        slack_client = SlackClient.get_global_instance()

        if not slack_client:
            logger.error("No global SlackClient instance available")
            return PlainTextResponse("Server error", status_code=500)

        # Process the event(s)
        # Events can come as a single event or as a batch
        event_data = payload.get('event', {})

        if event_data:
            # Route event to the appropriate handler
            event_type = event_data.get('type')

            logger.info(f"Received Slack event: type={event_type}, channel={event_data.get('channel')}, user={event_data.get('user')}, thread_ts={event_data.get('thread_ts')}, ts={event_data.get('ts')}")

            if event_type == 'app_mention':
                # Handle @mentions of the bot
                await slack_client._handle_message_event(
                    event_data,
                    slack_client.app.client,
                    is_mention=True
                )
            elif event_type == 'message':
                # Handle direct messages
                channel_type = event_data.get('channel_type')
                if channel_type == 'im':
                    await slack_client._handle_message_event(
                        event_data,
                        slack_client.app.client,
                        is_mention=False
                    )
                else:
                    logger.debug(f"Ignoring channel message: {channel_type}")
            else:
                logger.debug(f"Ignoring unhandled event type: {event_type}")

        # Always respond with 200 quickly to acknowledge receipt
        return PlainTextResponse("OK", status_code=200)

    except Exception as e:
        logger.error(f"Error handling Slack webhook: {e}")
        # Still return 200 to prevent Slack from retrying
        return PlainTextResponse("Error processed", status_code=200)


async def slack_interactive_endpoint(request: Request) -> PlainTextResponse:
    """
    Handle Slack interactive component payloads (buttons, menus, etc.).

    Args:
        request: The Starlette request object

    Returns:
        PlainTextResponse
    """
    try:
        # Verify the request is from Slack
        if not verify_slack_signature(request):
            logger.warning("Rejected interactive request with invalid signature")
            return PlainTextResponse("Invalid signature", status_code=403)

        payload = await request.form()
        payload_json = str(payload.get('payload', '{}'))
        import json
        payload_data = json.loads(payload_json)

        logger.info(f"Interactive payload received: {payload_data.get('type')}")

        # TODO: Handle interactive components as needed
        # - message actions
        # - block actions
        # - view submissions (modals)

        return PlainTextResponse("OK", status_code=200)

    except Exception as e:
        logger.error(f"Error handling Slack interactive endpoint: {e}")
        return PlainTextResponse("Error processed", status_code=200)


async def slack_command_endpoint(request: Request) -> PlainTextResponse:
    """
    Handle Slack slash command invocations.

    Args:
        request: The Starlette request object

    Returns:
        PlainTextResponse
    """
    try:
        # Verify the request is from Slack
        if not verify_slack_signature(request):
            logger.warning("Rejected command request with invalid signature")
            return PlainTextResponse("Invalid signature", status_code=403)

        form_data = await request.form()
        command = form_data.get('command', '')
        text = form_data.get('text', '')
        user_id = form_data.get('user_id', '')
        channel_id = form_data.get('channel_id', '')

        logger.info(f"Slash command received: {command} {text} from {user_id}")

        # TODO: Handle slash commands as needed

        return PlainTextResponse("OK", status_code=200)

    except Exception as e:
        logger.error(f"Error handling Slack command endpoint: {e}")
        return PlainTextResponse("Error processed", status_code=200)


def get_slack_routes():
    """
    Get all Slack-related routes for the Starlette app.

    Returns:
        List of Route objects
    """
    return [
        Route('/slack/events', slack_events_handler, methods=['POST']),
        Route('/slack/interactive', slack_interactive_endpoint, methods=['POST']),
        Route('/slack/commands', slack_command_endpoint, methods=['POST']),
    ]
