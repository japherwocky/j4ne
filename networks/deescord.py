from logging import info, debug, error
from random import choice, shuffle
from cleverbot import Cleverbot

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

from loggers.handlers import Discord as Dlogger
Dlogger = Dlogger()


class ErrorCatcher(discord.Client):

    async def on_error(event, *args, **kwargs):
        import sys
        sys.exc_info()

        import pdb;pdb.set_trace()


# instantiate this here to use decorators
client = discord.Client()  # loop defaults to asyncio.get_event_loop()

# We need to wrap connect() as a task to prevent timeout error at runtime.
# based on the following suggested fix: https://github.com/KeepSafe/aiohttp/issues/1176
def taskify(func):
    async def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().create_task(func(*args, **kwargs))
    return wrapper

class Discord(object):
    CB = Cleverbot()

    client = client  # so that network specific commands can access lower levels

    @taskify
    async def connect(self):

        self.client = client

        @client.event
        async def on_ready():
            info('Logged into Discord as {} {}'.format(client.user.id, client.user.name) )

            if getattr(self.application, 'Twitter', False):
                self.application.Twitter.setup_retweets()
                info('Retweet config loaded')

                await self.application.Twitter.check_tweets()

        @client.event
        async def on_message(message):
            # info(message) 
            await self.on_message(message)


        # this lived in a while True loop for a bit, to handle restarting
        info('Connecting to Discord..')
        await client.start(discord_token)

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

        posts = feedparser.parse('http://feeds2.feedburner.com/fmylife')
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
            reply = self.CB.ask(query)
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

        tooter = message.content.split('|retweet')[1]
        if not tooter:
            return await self.say(message.channel, 'Who should I retweet?')

        tooter = tooter.strip()

        this_server = message.server

        conf = self.application.Twitter._twitter_conf

        if not this_server in conf:
            conf[this_server] = {message.channel: []}

        if not message.channel in conf[this_server]:
            conf[this_server][message.channel] = []

        if message.channel in conf[this_server] and tooter in [t['screen_name'] for t in conf[this_server][message.channel]]:
            return await self.say(message.channel, 'I am already retweeting {} here.'.format(tooter))

        conf[this_server][message.channel].append( {'screen_name':tooter, 'last':1})

        self.application.Twitter.save_twitter_config()

        await self.say(message.channel, "I will start retweeting {} in this channel.".format(tooter))

        await self.application.Twitter.check_tweets()


