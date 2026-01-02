"""
IRC network client implementation.
"""

import asyncio
import time
import os
from typing import List, Optional
from collections import deque
import logging
import irc3
from irc3.plugins.autojoins import AutoJoins

from .base import NetworkClient, NetworkMessage


class IRCClient(NetworkClient):
    """IRC network client using irc3."""
    
    def __init__(self, chat_client=None):
        super().__init__("irc")
        
        # IRC configuration from environment variables
        self.server = os.getenv('IRC_SERVER', 'irc.libera.chat')
        self.port = int(os.getenv('IRC_PORT', '6667'))
        self.nickname = os.getenv('IRC_NICKNAME', 'j4ne-bot')
        self.realname = os.getenv('IRC_REALNAME', 'J4NE Chat Bot')
        self.channels = os.getenv('IRC_CHANNELS', '#j4ne-test').split(',')
        self.password = os.getenv('IRC_PASSWORD', None)
        
        # IRC3 bot instance
        self.bot = None
        self._connection_future = None
        
        # Chat client for AI responses
        self.chat_client = chat_client
        
        # Conversation history per channel
        self.channel_histories = {}
        self.max_history = 10  # Keep last 10 messages per channel
    
    async def connect(self) -> bool:
        """Connect to IRC server."""
        try:
            # IRC3 configuration
            config = {
                'nick': self.nickname,
                'username': self.realname,  # IRC3 uses 'username' instead of 'realname'
                'host': self.server,
                'port': self.port,
                'ssl': self.port == 6697,  # Use SSL for port 6697
                'autojoins': self.channels,
                'includes': [
                    'irc3.plugins.core',
                    'irc3.plugins.ctcp',
                    'irc3.plugins.autojoins',
                ],
            }
            
            if self.password:
                config['password'] = self.password
            
            # Create IRC3 bot
            self.bot = irc3.IrcBot.from_config(config)
            
            # Add event handlers
            self._setup_handlers()
            
            # Start the bot in a separate task
            self._connection_future = asyncio.create_task(self._run_bot())
            
            # Wait a bit for connection
            await asyncio.sleep(2)
            
            self.connected = True
            self.logger.info(f"Connected to IRC server {self.server}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to IRC: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from IRC server."""
        if self.bot:
            self.bot.quit("Goodbye!")
            
        if self._connection_future:
            self._connection_future.cancel()
            
        self.connected = False
        self.logger.info("Disconnected from IRC")
    
    async def send_message(self, channel: str, message: str):
        """Send a message to an IRC channel."""
        if not self.connected or not self.bot:
            self.logger.warning("Not connected to IRC")
            return
        
        # Ensure channel starts with #
        if not channel.startswith('#'):
            channel = f"#{channel}"
        
        # Split long messages
        max_length = 450  # IRC message limit is ~512, leave room for overhead
        if len(message) <= max_length:
            self.bot.privmsg(channel, message)
        else:
            # Split into multiple messages
            lines = message.split('\n')
            current_message = ""
            
            for line in lines:
                if len(current_message + line + '\n') <= max_length:
                    current_message += line + '\n'
                else:
                    if current_message:
                        self.bot.privmsg(channel, current_message.rstrip())
                    current_message = line + '\n'
            
            if current_message:
                self.bot.privmsg(channel, current_message.rstrip())
    
    async def join_channel(self, channel: str):
        """Join an IRC channel."""
        if not self.connected or not self.bot:
            self.logger.warning("Not connected to IRC")
            return
        
        if not channel.startswith('#'):
            channel = f"#{channel}"
        
        self.bot.join(channel)
        self.logger.info(f"Joined channel {channel}")
    
    async def leave_channel(self, channel: str):
        """Leave an IRC channel."""
        if not self.connected or not self.bot:
            self.logger.warning("Not connected to IRC")
            return
        
        if not channel.startswith('#'):
            channel = f"#{channel}"
        
        self.bot.part(channel)
        self.logger.info(f"Left channel {channel}")
    
    def _setup_handlers(self):
        """Setup IRC event handlers."""
        
        @irc3.event(irc3.rfc.PRIVMSG)
        def on_privmsg(mask, event, target, data):
            """Handle incoming messages."""
            # Create NetworkMessage
            message = NetworkMessage(
                network="irc",
                channel=target,
                user=mask.nick,
                content=data,
                timestamp=time.time(),
                raw_data={'mask': str(mask), 'event': event}
            )
            
            # Dispatch to handlers asynchronously
            asyncio.create_task(self._dispatch_message(message))
            
            # Handle AI response
            asyncio.create_task(self._handle_irc_message(message))
        
        @irc3.event(irc3.rfc.JOIN)
        def on_join(mask, channel):
            """Handle join events."""
            if mask.nick == self.nickname:
                self.logger.info(f"Successfully joined {channel}")
        
        @irc3.event(irc3.rfc.PART)
        def on_part(mask, channel, data=None):
            """Handle part events."""
            if mask.nick == self.nickname:
                self.logger.info(f"Left {channel}")
        
        @irc3.event(irc3.rfc.KICK)
        def on_kick(mask, channel, target, data=None):
            """Handle kick events."""
            if target == self.nickname:
                self.logger.warning(f"Kicked from {channel}: {data}")
        
        # Bind handlers to the bot
        self.bot.attach_events(on_privmsg, on_join, on_part, on_kick)
    
    async def _handle_irc_message(self, message: NetworkMessage):
        """Handle incoming IRC message and generate AI response if needed."""
        # Skip messages from ourselves
        if message.user == self.nickname:
            return
        
        # Initialize channel history if needed
        if message.channel not in self.channel_histories:
            self.channel_histories[message.channel] = deque(maxlen=self.max_history)
        
        # Add message to history
        self.channel_histories[message.channel].append({
            'role': 'user',
            'content': f"{message.user}: {message.content}"
        })
        
        # Check if bot was mentioned or if it's a direct message
        should_respond = (
            self.nickname.lower() in message.content.lower() or
            message.channel == self.nickname or  # Direct message
            message.content.startswith('!')  # Command prefix
        )
        
        if should_respond and self.chat_client:
            try:
                # Get conversation history for this channel
                history = list(self.channel_histories[message.channel])
                
                # Generate AI response
                response = await self.chat_client.process_query(history)
                
                # Send response back to IRC
                if response and response.strip():
                    await self.send_message(message.channel, response)
                    
                    # Add bot response to history
                    self.channel_histories[message.channel].append({
                        'role': 'assistant',
                        'content': response
                    })
                    
            except Exception as e:
                self.logger.error(f"Error generating AI response: {e}")
                await self.send_message(message.channel, f"Sorry, I encountered an error: {str(e)}")
    
    def set_chat_client(self, chat_client):
        """Set the chat client for AI responses."""
        self.chat_client = chat_client
    
    async def _run_bot(self):
        """Run the IRC bot in the asyncio event loop."""
        try:
            # IRC3 runs in its own event loop, so we need to run it in a thread
            # or adapt it to work with asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.bot.run)
        except asyncio.CancelledError:
            self.logger.info("IRC bot task cancelled")
        except Exception as e:
            self.logger.error(f"IRC bot error: {e}")
            self.connected = False
