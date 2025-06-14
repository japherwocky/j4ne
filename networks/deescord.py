from twython import Twython
from twython.exceptions import TwythonError

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys from environment
cleverkey = os.getenv('CLEVERBOT_KEY', '')
discord_token = os.getenv('DISCORD_TOKEN', 'your-secret-token')

import cl3ver

import aiohttp
import asyncio
import discord
import json
import logging
import random
import re
import time
import traceback
import urllib

from tornado import gen
import tornado.ioloop

from commands import Discord_commands as Commands
from commands import discord_command as command
from commands import deescord

from networks import Network
from networks.models import Channels, Servers

from loggers.models import Event

class DeescordNetwork(Network):
    def __init__(self, j4ne):
        super().__init__(j4ne)
        self.client = discord.Client()
        self.client.event(self.on_ready)
        self.client.event(self.on_message)
        self.client.event(self.on_reaction_add)
        self.client.event(self.on_reaction_remove)
        self.client.event(self.on_member_join)
        self.client.event(self.on_member_remove)
        self.client.event(self.on_member_update)
        self.client.event(self.on_guild_join)
        self.client.event(self.on_guild_remove)
        self.client.event(self.on_guild_update)
        self.client.event(self.on_guild_role_create)
        self.client.event(self.on_guild_role_delete)
        self.client.event(self.on_guild_role_update)
        self.client.event(self.on_guild_emojis_update)
        self.client.event(self.on_guild_available)
        self.client.event(self.on_guild_unavailable)
        self.client.event(self.on_voice_state_update)
        self.client.event(self.on_member_ban)
        self.client.event(self.on_member_unban)
        self.client.event(self.on_typing)
        self.client.event(self.on_group_join)
        self.client.event(self.on_group_remove)
        self.client.event(self.on_relationship_add)
        self.client.event(self.on_relationship_remove)
        self.client.event(self.on_relationship_update)

    async def connect(self):
        await self.client.login(discord_token)
        await self.client.connect()

    async def on_ready(self):
        logging.info('Logged in as')
        logging.info(self.client.user.name)
        logging.info(self.client.user.id)
        logging.info('------')

        # Create database entries for servers and channels
        for server in self.client.guilds:
            try:
                s = Servers.get(Servers.snowflake == server.id)
            except Servers.DoesNotExist:
                s = Servers.create(snowflake=server.id, name=server.name)

            for channel in server.channels:
                if str(channel.type) == 'text':
                    try:
                        c = Channels.get(Channels.snowflake == channel.id)
                    except Channels.DoesNotExist:
                        c = Channels.create(snowflake=channel.id, server=s, name=channel.name)

    async def send_message(self, channel, message):
        await channel.send(message)

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.client.user:
            return

        # log the message
        if message.guild:
            try:
                server = Servers.get(Servers.snowflake == message.guild.id)
                channel = Channels.get(Channels.snowflake == message.channel.id)
                Event.create(server=server, channel=channel, type='discord_message', content=message.content, user=message.author.name)
            except Exception as e:
                logging.error(e)

        # handle commands
        if message.content.startswith('!'):
            command = message.content.split(' ')[0][1:]
            if command in Commands:
                try:
                    await Commands[command](self, message.channel, message)
                except Exception as e:
                    logging.error(e)
                    traceback.print_exc()
                    await message.channel.send("Error: {}".format(e))

            elif message.content.startswith('!'):
                await commands.deescord.custom(self, message.channel, message)

            elif message.content.startswith('|'):
                await commands.deescord.custom(self, message.channel, message)

