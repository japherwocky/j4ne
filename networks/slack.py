"""
Slack network client implementation using Slack Bolt for Python.
"""

import asyncio
import time
import os
import re
from typing import Optional
import logging

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from .base import NetworkClient, NetworkMessage


def markdown_to_mrkdwn(text: str) -> str:
    """
    Convert markdown formatting to Slack's mrkdwn format.

    Markdown → Slack mrkdwn:
    - **bold** → *bold*
    - *italic* → _italic_
    - `code` → `code`
    - ```code block``` → ```code block```
    - ~~strike~~ → ~strike~
    - > quote → > quote
    - [text](url) → <url|text>
    """
    if not text:
        return text

    # Code blocks (```...```)
    text = re.sub(r'```(\w*)\n([\s\S]*?)```', r'```\2```', text)

    # Inline code (`...`)
    text = re.sub(r'`([^`]+)`', r'`\1`', text)

    # Bold (**...** → *...*)
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)

    # Italic (*...* → _..._) - be careful not to match bold
    text = re.sub(r'(?<![\*])(\*)([^\s*]+)(?!\1)', r'_\2_', text)
    # Actually, this is tricky. Let's use a simpler approach for italic
    # Match _italic_ format if it's already there
    text = re.sub(r'_(.+?)_', r'_\1_', text)

    # Strikethrough (~~...~~ → ~...~)
    text = re.sub(r'~~(.+?)~~', r'~\1~', text)

    # Links ([text](url) → <url|text>)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', text)

    # Block quotes (> text)
    text = re.sub(r'^>\s*(.+)$', r'>\1', text, flags=re.MULTILINE)

    return text


class SlackClient(NetworkClient):
    """Slack network client supporting both HTTP and Socket Mode."""

    # Reaction emoji constants
    REACTION_THINKING = "hourglass"  # Thinking/working on it
    REACTION_DONE = "white_check_mark"  # Done/success
    REACTION_ERROR = "x"  # Error/failed

    # Global instance for HTTP webhook access
    _global_instance = None

    @classmethod
    def set_global_instance(cls, instance):
        """Set the global SlackClient instance for HTTP webhook access."""
        cls._global_instance = instance

    @classmethod
    def get_global_instance(cls):
        """Get the global SlackClient instance."""
        return cls._global_instance

    def __init__(self, chat_client=None, mode: str = "auto"):
        """
        Initialize Slack client.

        Args:
            chat_client: Chat client for AI responses
            mode: Connection mode - "socket" (Socket Mode), "http" (HTTP webhook),
                  or "auto" (HTTP if signing secret available, otherwise Socket Mode)
        """
        super().__init__("slack")

        # Slack configuration from environment variables
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.app_token = os.getenv('SLACK_APP_TOKEN')
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')

        # Determine connection mode
        self.mode = self._determine_mode(mode)

        # Slack Bolt app and socket handler
        self.app = None
        self.handler = None
        self._handler_task = None

        # Chat client for AI responses
        self.chat_client = chat_client

        # Bot user ID (will be set after connection)
        self.bot_user_id = None

        # Validate required tokens based on mode
        if self.mode == "socket":
            if not self.bot_token or not self.app_token:
                self.logger.warning(
                    "Socket Mode requires SLACK_BOT_TOKEN and SLACK_APP_TOKEN. "
                    "Set these environment variables or use HTTP mode."
                )
        else:  # http mode
            if not self.bot_token:
                self.logger.warning(
                    "Missing SLACK_BOT_TOKEN. Set this environment variable to enable Slack integration."
                )
            if not self.signing_secret:
                self.logger.warning(
                    "Missing SLACK_SIGNING_SECRET. This is required for HTTP mode. "
                    "Get it from your Slack app settings."
                )

    def _determine_mode(self, mode: str) -> str:
        """
        Determine the connection mode based on parameter and environment.

        Args:
            mode: Requested mode ("socket", "http", or "auto")

        Returns:
            Actual mode to use
        """
        if mode == "socket":
            return "socket"
        if mode == "http":
            return "http"

        # Auto mode: prefer HTTP if signing secret is available
        if mode == "auto":
            if self.signing_secret:
                return "http"
            if self.app_token:
                return "socket"
            return "http"  # Default to HTTP if neither is configured

        return "http"

    async def connect(self) -> bool:
        """Connect to Slack using either HTTP mode or Socket Mode."""
        if not self.bot_token:
            self.logger.warning("Slack bot token not configured, skipping Slack client startup")
            return False

        try:
            # Initialize Slack Bolt app
            self.app = AsyncApp(token=self.bot_token)

            # Get bot user info
            auth_response = await self.app.client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            self.logger.info(f"Slack bot user ID: {self.bot_user_id}")

            # Set up event handlers (for both modes)
            self._setup_handlers()

            # Register as global instance for HTTP mode
            SlackClient.set_global_instance(self)

            if self.mode == "socket":
                # Socket Mode connection
                if not self.app_token:
                    self.logger.warning("SLACK_APP_TOKEN required for Socket Mode")
                    return False

                # Initialize Socket Mode handler
                self.handler = AsyncSocketModeHandler(self.app, self.app_token)
                self._handler_task = asyncio.create_task(self.handler.start_async())

                # Wait a bit for connection
                await asyncio.sleep(2)

                self.connected = True
                self.logger.info("Connected to Slack via Socket Mode")
            else:
                # HTTP mode - just verify connection, no socket needed
                self.connected = True
                self.logger.info("Connected to Slack via HTTP mode (webhook receiver active)")

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Slack: {e}")
            return False

    async def disconnect(self):
        """Disconnect from Slack."""
        if self.handler:
            await self.handler.close_async()

        if self._handler_task:
            self._handler_task.cancel()
            try:
                await self._handler_task
            except asyncio.CancelledError:
                pass

        # Clear global instance
        if SlackClient.get_global_instance() == self:
            SlackClient.set_global_instance(None)

        self.connected = False
        self.logger.info("Disconnected from Slack")

    async def send_message(self, channel: str, message: str, thread_ts: Optional[str] = None):
        """Send a message to a Slack channel, converting markdown to mrkdwn format."""
        if not self.connected or not self.app:
            self.logger.warning("Not connected to Slack")
            return

        # Convert markdown to Slack's mrkdwn format
        mrkdwn_message = markdown_to_mrkdwn(message)

        try:
            self.logger.info(f"chat_postMessage: channel={channel}, thread_ts={thread_ts}, message_preview={message[:100]}...")
            await self.app.client.chat_postMessage(
                channel=channel,
                text=mrkdwn_message,
                thread_ts=thread_ts
            )
            self.logger.info(f"Successfully sent message to channel={channel}, thread_ts={thread_ts}")
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")

    async def add_reaction(self, channel_id: str, timestamp: str, emoji: str) -> bool:
        """
        Add an emoji reaction to a message.

        Args:
            channel_id: The Slack channel ID
            timestamp: The timestamp of the message to react to
            emoji: The emoji name (without colons)

        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.app:
            self.logger.warning("Not connected to Slack")
            return False

        try:
            await self.app.client.reactions_add(
                channel=channel_id,
                timestamp=timestamp,
                name=emoji
            )
            self.logger.debug(f"Added reaction :{emoji}: to message {timestamp}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add reaction :{emoji}: {e}")
            return False

    async def remove_reaction(self, channel_id: str, timestamp: str, emoji: str) -> bool:
        """
        Remove an emoji reaction from a message.

        Args:
            channel_id: The Slack channel ID
            timestamp: The timestamp of the message to unreact from
            emoji: The emoji name (without colons)

        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not self.app:
            self.logger.warning("Not connected to Slack")
            return False

        try:
            await self.app.client.reactions_remove(
                channel=channel_id,
                timestamp=timestamp,
                name=emoji
            )
            self.logger.debug(f"Removed reaction :{emoji}: from message {timestamp}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove reaction :{emoji}: {e}")
            return False

    async def update_reaction(self, channel_id: str, timestamp: str, old_emoji: str, new_emoji: str) -> bool:
        """
        Replace one emoji reaction with another.

        Args:
            channel_id: The Slack channel ID
            timestamp: The timestamp of the message
            old_emoji: The emoji to remove (without colons)
            new_emoji: The emoji to add (without colons)

        Returns:
            True if successful, False otherwise
        """
        # Remove old reaction and add new one
        removed = await self.remove_reaction(channel_id, timestamp, old_emoji)
        added = await self.add_reaction(channel_id, timestamp, new_emoji)
        return removed and added

    async def join_channel(self, channel: str):
        """Join a Slack channel (bot must be invited by users)."""
        # Note: Slack bots typically need to be invited to channels
        # This method is here for interface compatibility
        self.logger.info(f"Slack bots need to be invited to channels. Ask a user to invite the bot to {channel}")

    async def leave_channel(self, channel: str):
        """Leave a Slack channel."""
        if not self.connected or not self.app:
            self.logger.warning("Not connected to Slack")
            return

        try:
            await self.app.client.conversations_leave(channel=channel)
            self.logger.info(f"Left Slack channel: {channel}")
        except Exception as e:
            self.logger.error(f"Failed to leave Slack channel {channel}: {e}")

    def _setup_handlers(self):
        """Set up Slack event handlers."""

        # Debug: Log ALL events received
        @self.app.event("*")
        async def handle_all_events(event, **kwargs):
            """Debug handler to log all events."""
            self.logger.debug(f"Received event: {event.get('type', 'unknown')}")
            self.logger.debug(f"Event data: {event}")

        @self.app.event("app_mention")
        async def handle_app_mention(event, say, client):
            """Handle @mentions of the bot."""
            self.logger.info(f"App mention received: {event.get('text', '')[:100]}...")
            await self._handle_message_event(event, client, is_mention=True)

        @self.app.event("message")
        async def handle_message(event, client):
            """Handle direct messages to the bot."""
            # Only respond to DMs (not channel messages without mentions)
            if event.get("channel_type") == "im":
                self.logger.info(f"DM received: {event.get('text', '')[:100]}...")
                await self._handle_message_event(event, client, is_mention=False)

    async def _get_thread_history(self, channel_id: str, thread_ts: str, client) -> list:
        """
        Fetch all messages in a thread to build conversation history.

        Args:
            channel_id: The Slack channel ID
            thread_ts: The timestamp of the thread parent message
            client: Slack client for API calls

        Returns:
            List of message dictionaries with role and content
        """
        try:
            # Fetch all replies in the thread
            response = await client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )

            if not response.get("ok") or not response.get("messages"):
                self.logger.debug(f"No thread messages found for {thread_ts}")
                return []

            # Build history from thread messages
            history = []
            for msg in response["messages"]:
                # Skip messages without text
                if not msg.get("text"):
                    continue

                # Check if this is our bot's message
                is_our_bot = msg.get("bot_id") or msg.get("user") == self.bot_user_id

                # Get username for user messages
                if not is_our_bot and msg.get("user"):
                    try:
                        user_info = await client.users_info(user=msg["user"])
                        username = user_info["user"]["real_name"] or user_info["user"]["name"]
                    except Exception:
                        username = "unknown"
                elif not is_our_bot:
                    username = "unknown"
                else:
                    username = "j4ne"  # Our bot's name

                # Clean the message text (remove bot mentions)
                msg_text = msg["text"]
                if self.bot_user_id:
                    bot_mention = f"<@{self.bot_user_id}>"
                    msg_text = msg_text.replace(bot_mention, "").strip()

                # Add to history with appropriate role
                # Our bot messages get role="assistant", users get role="user"
                history.append({
                    "role": "assistant" if is_our_bot else "user",
                    "content": f"{username}: {msg_text}"
                })

            self.logger.debug(f"Fetched {len(history)} messages from thread")
            return history

        except Exception as e:
            self.logger.error(f"Error fetching thread history: {e}")
            return []

    async def _handle_message_event(self, event, client, is_mention: bool = False):
        """Process a Slack message event."""
        self.logger.debug(f"Processing message event: {event.get('type', 'unknown')}")
        self.logger.debug(f"Event details: channel={event.get('channel')}, user={event.get('user')}, text={event.get('text', '')[:50]}...")

        try:
            # Skip bot messages and messages without text
            if event.get("bot_id") or not event.get("text"):
                self.logger.debug(f"Skipping message: bot_id={event.get('bot_id')}, text={event.get('text')}")
                return

            # Skip our own messages
            if event.get("user") == self.bot_user_id:
                self.logger.debug(f"Skipping own message")
                return

            self.logger.info(f"Processing message from user {event.get('user')}: {event.get('text', '')[:100]}...")

            # Get user info
            user_info = await client.users_info(user=event["user"])
            username = user_info["user"]["real_name"] or user_info["user"]["name"]

            # Get channel info
            channel_id = event["channel"]
            self.logger.info(f"Event channel_id={channel_id}, thread_ts={event.get('thread_ts')}, ts={event.get('ts')}")
            channel_info = await client.conversations_info(channel=channel_id)
            channel_name = channel_info["channel"]["name"] if channel_info["channel"].get("name") else "DM"

            # Clean the message text (remove bot mention)
            message_text = event["text"]
            if is_mention and self.bot_user_id:
                # Remove the bot mention from the message
                bot_mention = f"<@{self.bot_user_id}>"
                message_text = message_text.replace(bot_mention, "").strip()

            # Create NetworkMessage
            network_message = NetworkMessage(
                network="slack",
                channel=f"#{channel_name}",
                user=username,
                content=message_text,
                timestamp=float(event.get("ts", time.time())),
                raw_data={
                    "event": event,
                    "channel_id": channel_id,
                    "thread_ts": event.get("thread_ts"),
                    "is_mention": is_mention
                }
            )

            # Dispatch to message handlers
            await self._dispatch_message(network_message)

            # Generate AI response if chat client is available
            if self.chat_client and message_text.strip():
                # Get message timestamp for reactions
                message_ts = event.get("ts")

                # Add thinking reaction immediately
                if message_ts:
                    await self.add_reaction(
                        channel_id,
                        message_ts,
                        self.REACTION_THINKING
                    )

                try:
                    # Check if this is a thread reply
                    thread_ts = event.get("thread_ts")

                    if thread_ts:
                        # Fetch full thread history
                        history = await self._get_thread_history(channel_id, thread_ts, client)
                        self.logger.info(f"Using thread history with {len(history)} messages")
                    else:
                        # Just use the current message
                        history = [
                            {"role": "user", "content": f"{username}: {message_text}"}
                        ]

                    # Get AI response
                    response = await self.chat_client.process_query(history)

                    if response and response.strip():
                        # Send response in thread if original message was in a thread or if it was a mention
                        reply_ts = thread_ts or (event.get("ts") if is_mention else None)

                        self.logger.info(f"Sending response: channel={channel_id} ({channel_name}), thread_ts={reply_ts}, is_mention={is_mention}, original_thread_ts={thread_ts}")

                        await self.send_message(
                            channel=channel_id,
                            message=response,
                            thread_ts=reply_ts
                        )

                        self.logger.info(f"Sent AI response to {channel_name} for {username}")

                        # Update reaction to done
                        if message_ts:
                            await self.update_reaction(
                                channel_id,
                                message_ts,
                                self.REACTION_THINKING,
                                self.REACTION_DONE
                            )

                except Exception as e:
                    self.logger.error(f"Error generating AI response: {e}")

                    # Update reaction to error
                    if message_ts:
                        await self.update_reaction(
                            channel_id,
                            message_ts,
                            self.REACTION_THINKING,
                            self.REACTION_ERROR
                        )

                    # Send a friendly error message
                    await self.send_message(
                        channel=channel_id,
                        message="Sorry, I'm having trouble processing that right now. Please try again later!",
                        thread_ts=event.get("thread_ts") or (event.get("ts") if is_mention else None)
                    )

        except Exception as e:
            self.logger.error(f"Error handling Slack message: {e}")

    def set_chat_client(self, chat_client):
        """Set the chat client for AI responses."""
        self.chat_client = chat_client
