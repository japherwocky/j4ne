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

# Characters that start a channel name; any other PRIVMSG target is a DM
CHANNEL_PREFIXES = ('#', '&', '+', '!')

# The most of one reply sent to IRC. irc3 sends without flood control (its
# queue needs asyncio APIs Python 3.10 removed), and servers kick floods.
MAX_REPLY_CHARS = 1800


class IRCClient(NetworkClient):
    """IRC network client using irc3."""

    def __init__(self, chat_client=None):
        super().__init__("irc")

        # IRC configuration from environment variables. No server, no IRC:
        # it is opt-in, not a default connection to a public network.
        self.server = os.getenv('IRC_SERVER') or None
        self.port = int(os.getenv('IRC_PORT', '6667'))
        self.nickname = os.getenv('IRC_NICKNAME', 'j4ne-bot')
        self.realname = os.getenv('IRC_REALNAME', 'J4NE Chat Bot')
        self.channels = [c.strip() for c in os.getenv('IRC_CHANNELS', '#j4ne-test').split(',') if c.strip()]
        self.password = os.getenv('IRC_PASSWORD', None)
        self.command_prefix = os.getenv('IRC_COMMAND_PREFIX', '!')

        # IRC3 bot instance
        self.bot = None

        # Chat client for AI responses
        self.chat_client = chat_client

        # Conversation history per channel, and per user for DMs
        self.channel_histories = {}
        self.max_history = 10  # Keep last 10 messages per channel

        # Replies being worked on; the loop only holds tasks weakly
        self._tasks = set()

    async def connect(self) -> bool:
        """Connect to IRC server."""
        if not self.server:
            self.logger.info("IRC_SERVER not set, not connecting to IRC")
            return False

        try:
            # IRC3 configuration
            config = {
                'nick': self.nickname,
                # irc3 1.x: username is the ident, one word; realname is the
                # free text. This used to put the realname in the ident slot,
                # sending 'USER J4NE Chat Bot 0 * :...'
                'username': 'j4ne',
                'realname': self.realname,
                'host': self.server,
                'port': self.port,
                'ssl': self.port == 6697,  # Use SSL for port 6697
                'autojoins': self.channels,
                'includes': [
                    'irc3.plugins.core',
                    'irc3.plugins.ctcp',
                    'irc3.plugins.autojoins',
                ],
                # Run on this event loop, the one the web server and Slack share
                'loop': asyncio.get_running_loop(),
            }

            if self.password:
                config['password'] = self.password

            # Create IRC3 bot
            self.bot = irc3.IrcBot.from_config(config)

            # Add event handlers
            self._setup_handlers()

            # Schedules the connection on the loop and returns. Not bot.run():
            # that also calls run_forever() and takes over SIGINT. irc3
            # reconnects by itself when the connection drops.
            self.bot.create_connection()
            self.logger.info(f"Connecting to IRC server {self.server}:{self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to IRC: {e}")
            return False

    async def disconnect(self):
        """Disconnect from IRC server."""
        if self.bot and getattr(self.bot, 'protocol', None):
            # irc3 reconnects after any lost connection, including the one a
            # server closes in answer to QUIT; this time it is meant
            self.bot.create_connection = lambda *args, **kwargs: None
            if self.connected:
                self.bot.quit("Goodbye!")
                # Closing at once can drop the QUIT (seen on Windows)
                await asyncio.sleep(0.2)
            self.bot.protocol.close()

        self.connected = False
        self.logger.info("Disconnected from IRC")

    async def send_message(self, channel: str, message: str):
        """Send a message to an IRC channel or, by nick, to a user."""
        if not self.connected or not self.bot:
            self.logger.warning("Not connected to IRC")
            return

        if len(message) > MAX_REPLY_CHARS:
            message = message[:MAX_REPLY_CHARS].rstrip() + " …"

        # irc3 splits long messages and turns newlines into spaces, so one
        # call per paragraph keeps a reply's structure without blank lines
        for line in message.split('\n'):
            if line.strip():
                self.bot.privmsg(channel, line)

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

    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _setup_handlers(self):
        """Setup IRC event handlers."""

        def on_connected(srv=None, me=None, data=None):
            """End of the MOTD: registered and ready to talk"""
            self.connected = True
            self.logger.info(f"Connected to IRC server {self.server}:{self.port} as {me}")

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
            self._spawn(self._dispatch_message(message))

            # Handle AI response
            self._spawn(self._handle_irc_message(message))

        def on_join(mask, channel):
            """Handle join events."""
            if mask.nick == self.bot.nick:
                self.logger.info(f"Successfully joined {channel}")

        def on_part(mask, channel, data=None):
            """Handle part events."""
            if mask.nick == self.bot.nick:
                self.logger.info(f"Left {channel}")

        def on_kick(mask, channel, target, data=None):
            """Handle kick events."""
            if target == self.bot.nick:
                self.logger.warning(f"Kicked from {channel}: {data}")

        # Bind handlers to the bot. attach_events takes irc3.event objects;
        # given the decorated functions themselves it raises, which is why
        # connect() always failed before.
        self.bot.attach_events(
            irc3.event(irc3.rfc.CONNECTED, callback=on_connected),
            irc3.event(irc3.rfc.PRIVMSG, callback=on_privmsg),
            irc3.event(irc3.rfc.JOIN, callback=on_join),
            irc3.event(irc3.rfc.PART, callback=on_part),
            irc3.event(irc3.rfc.KICK, callback=on_kick),
        )

    async def _handle_irc_message(self, message: NetworkMessage):
        """Handle incoming IRC message and generate AI response if needed."""
        own_nick = self.bot.nick if self.bot else self.nickname

        # Skip messages from ourselves
        if message.user == own_nick:
            return

        # A DM is addressed to our nick, and is answered to its sender
        is_dm = not message.channel.startswith(CHANNEL_PREFIXES)
        reply_to = message.user if is_dm else message.channel
        history_key = f"dm:{message.user.lower()}" if is_dm else message.channel.lower()

        # Initialize channel history if needed
        if history_key not in self.channel_histories:
            self.channel_histories[history_key] = deque(maxlen=self.max_history)

        # Add message to history
        self.channel_histories[history_key].append({
            'role': 'user',
            'content': f"{message.user}: {message.content}"
        })

        # Check if bot was mentioned or if it's a direct message
        should_respond = (
            is_dm or
            own_nick.lower() in message.content.lower() or
            message.content.startswith(self.command_prefix)  # Configurable command prefix
        )

        if should_respond and self.chat_client:
            try:
                # Get conversation history for this channel
                history = list(self.channel_histories[history_key])

                # Generate AI response
                response = await self.chat_client.process_query(history, session_key=f"irc:{history_key}")

                # Send response back to IRC
                if response and response.strip():
                    await self.send_message(reply_to, response)

                    # Add bot response to history
                    self.channel_histories[history_key].append({
                        'role': 'assistant',
                        'content': response
                    })

            except Exception as e:
                # The details go to the log, not to the channel
                self.logger.error(f"Error generating AI response: {e}")
                await self.send_message(reply_to, "Sorry, I ran into an error answering that.")

    def set_chat_client(self, chat_client):
        """Set the chat client for AI responses."""
        self.chat_client = chat_client
