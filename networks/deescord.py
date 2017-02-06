from logging import info, debug, error
from random import choice, shuffle
from cleverbot import Cleverbot
from twython.exceptions import TwythonError

import cl3ver
from keys import cleverbot_key as cleverkey

import aiohttp
import asyncio
import re
import os
import json
import requests

import discord

import feedparser  # for depressing j4ne

from tornado import gen
import tornado.ioloop

from keys import discord_token

from commands import Discord_commands as Commands
from commands import discord_command as command
import commands.deescord
import commands.jukebox

from networks.models import Tooter, DiscordServer, DiscordChannel

from loggers.handlers import Discord as Dlogger
Dlogger = Dlogger()


class ErrorCatcher(discord.Client):

    async def on_error(event, *args, **kwargs):
        import sys
        sys.exc_info()

        import pdb;pdb.set_trace()


# instantiate this here to use decorators
client = discord.Client()  # loop defaults to asyncio.get_event_loop()

class Discord(object):
    CB = cl3ver.Cl3ver(cleverkey)

    client = client  # so that network specific commands can access lower levels

    async def connect(self):

        self.client = client

        @client.event
        async def on_ready():
            info('Logged into Discord as {} {}'.format(client.user.id, client.user.name) )

            if getattr(self.application, 'Twitter', False):
                await self.application.Twitter.check_tweets()

        @client.event
        async def on_message(message):
            # info(message) 
            await self.on_message(message)



        """ eventually, when the connection gets reset (when, not if),
            it bubbles up as aiohttp.errors.ClientResponseError
        """
        while True:
            # force the thing to reconnect?
            info('Connecting to Discord..')
            try:
                await client.start(discord_token)
            except aiohttp.errors.ClientResponseError as e:
                error(e)
                continue

    async def send_message(self, channel, message):
        return await client.send_message(channel, message)

    async def send_file(self, channel, filepath):
        return await client.send_file(channel, filepath)

    async def say(self, channel, message, destroy=0):
        msg = await client.send_message(channel, message)

        if destroy:
            await asyncio.sleep(destroy)
            await client.delete_message(msg)

    async def on_triggered(self, channel):
        ''' someone said the magic word! '''

        posts = feedparser.parse('http://www.fmylife.com/rss')
        post = choice(posts.entries)
        post = re.sub(r'<[^>]*?>', '', post.description).replace('FML', '')

        await self.say(channel, str(post))

    async def on_message(self, message):
        Dlogger(message)

        if 'j4ne' in message.content.lower() and 'day' in message.content.lower():
            await self.on_triggered(message.channel)

        elif message.content.lower().startswith('j4ne'):
            query = message.content.lower().split('j4ne', 1)[1]
            if not query:
                return await client.send_message(message.channel, "Yes?")

            debug(query)
            reply = self.CB.say(query, message.author.name)
            reply = reply[:1].lower() + reply[1:]
            reply = '{}, {}'.format(message.author.name, reply)
            await client.send_message(message.channel, reply)

        # TODO refactor this out of here
        elif message.content.startswith('|retweet'):
            await self.retweet(message)

        elif '|' in message.content:
            cmd = message.content.split('|')[1].split(' ')[0].lower()
            # message.clean_content = message.clean_content.lower()
            if cmd in Commands:
                await Commands[cmd](self, message.channel, message)

            elif message.content.startswith('|'):
                await commands.deescord.custom(self, message.channel, message)


    async def retweet(self, message):
        screen_name = message.content.split('|retweet')[1].strip()

        if not screen_name:
            return await self.say(message.channel, 'Who should I retweet?')

        else:
            try:
                tooter_profile = (self.application.Twitter._twitter
                                  .show_user(screen_name=screen_name))

            except TwythonError as e:
                error('Twython Error: {}'.format(e))

                return await self.say(message.channel, 'There was a problem searching for the Twitter user with the screen name {}. Is this spelled correctly?')

        this_server = message.server
        this_channel = message.channel

        #  get_or_create() method returns (instance, created? = bool)
        tooter = Tooter.get_or_create(screen_name=screen_name)[0]
        server_in_db = DiscordServer.get_or_create(name=this_server)
        server = server_in_db[0]

        if not server_in_db[1]:
            info('Discord server {} added to database'.format(server.name))

            info('Adding channel: {} to database for retweeting'.format(this_channel))
            channel = DiscordChannel.create(name=this_channel,
                                            server=server)

        elif tooter.channels.where(DiscordChannel == this_channel).exists():
            return await self.say(this_channel,
                                  'I am already retweeting {} here.'
                                  .format(tooter.screen_name))

        else:
            channel = DiscordChannel.get_or_create(name=this_channel,
                                                   server=server)[0]

        tooter.servers.add(server, clear_existing=False)
        tooter.channels.add(channel, clear_existing=False)

        info('Tooter {} succesufully added'.format(tooter.screen_name))
        await self.say(message.channel, "I will start retweeting {} in this channel.".format(tooter.screen_name))

        await self.application.Twitter.check_tweets()
