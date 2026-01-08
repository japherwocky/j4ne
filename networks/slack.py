"""
Slack network client implementation using Slack Bolt for Python.
"""

import asyncio
import time
import os
from typing import Optional
import logging

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from .base import NetworkClient, NetworkMessage


class SlackClient(NetworkClient):
    """Slack network client using Slack Bolt with Socket Mode."""
    
    def __init__(self, chat_client=None):
        super().__init__("slack")
        
        # Slack configuration from environment variables
        self.bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.app_token = os.getenv('SLACK_APP_TOKEN')
        self.signing_secret = os.getenv('SLACK_SIGNING_SECRET')
        
        # Slack Bolt app and socket handler
        self.app = None
        self.handler = None
        self._handler_task = None
        
        # Chat client for AI responses
        self.chat_client = chat_client
        
        # Bot user ID (will be set after connection)
        self.bot_user_id = None
        
        # Validate required tokens
        if not self.bot_token or not self.app_token:
            self.logger.warning(
                "Missing Slack tokens. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN "
                "environment variables to enable Slack integration."
            )
    
    async def connect(self) -> bool:
        """Connect to Slack using Socket Mode."""
        if not self.bot_token or not self.app_token:
            self.logger.warning("Slack tokens not configured, skipping Slack client startup")
            return False
        
        try:
            # Initialize Slack Bolt app
            self.app = AsyncApp(token=self.bot_token)
            
            # Get bot user info
            auth_response = await self.app.client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            self.logger.info(f"Slack bot user ID: {self.bot_user_id}")
            
            # Set up event handlers
            self._setup_handlers()
            
            # Initialize Socket Mode handler
            self.handler = AsyncSocketModeHandler(self.app, self.app_token)
            
            # Start the handler in background
            self._handler_task = asyncio.create_task(self.handler.start_async())
            
            # Wait a bit for connection
            await asyncio.sleep(2)
            
            self.connected = True
            self.logger.info("Connected to Slack via Socket Mode")
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
            
        self.connected = False
        self.logger.info("Disconnected from Slack")
    
    async def send_message(self, channel: str, message: str, thread_ts: Optional[str] = None):
        """Send a message to a Slack channel."""
        if not self.connected or not self.app:
            self.logger.warning("Not connected to Slack")
            return
        
        try:
            await self.app.client.chat_postMessage(
                channel=channel,
                text=message,
                thread_ts=thread_ts
            )
            self.logger.debug(f"Sent message to {channel}: {message[:50]}...")
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
    
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
                try:
                    # Create a simple conversation history for context
                    history = [
                        {"role": "user", "content": f"{username}: {message_text}"}
                    ]
                    
                    # Get AI response
                    response = await self.chat_client.process_query(history)
                    
                    if response and response.strip():
                        # Send response in thread if original message was in a thread or if it was a mention
                        thread_ts = event.get("thread_ts") or (event.get("ts") if is_mention else None)
                        
                        await self.send_message(
                            channel=channel_id,
                            message=response,
                            thread_ts=thread_ts
                        )
                        
                        self.logger.info(f"Sent AI response to {channel_name} for {username}")
                    
                except Exception as e:
                    self.logger.error(f"Error generating AI response: {e}")
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
