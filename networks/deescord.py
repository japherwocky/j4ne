from logging import info, debug, error
from random import choice, shuffle
from cleverbot import Cleverbot
CB = Cleverbot()

import asyncio
import re
import os
import json

import discord

import feedparser

from tornado import gen
import tornado.ioloop

from keys import discord_token

from commands import Commands, command
import commands.deescord
import commands.jukebox

from websockets.exceptions import ConnectionClosed

# instantiate this here to use decorators
client = discord.Client()  # loop defaults to asyncio.get_event_loop()


class Discord(object):
    """ Mixin for the main App """
    _Twitter = None

    @gen.coroutine
    def discord_connect(self):
        self.DiscordParser = parser  # not sure what magic actually hooks up the handlers

        @client.event
        async def on_message(message):
            await self.DiscordParser.on_message(message)

        while True:
            try:
                yield client.start(discord_token)
            except ConnectionClosed:
                error('websocket closed, will try to reconnect')
                self.DiscordParser.stop()
                continue

    @client.event
    async def on_ready():
        info('Logged in as {} {}'.format(client.user.id, client.user.name) )

        # try to load tweeters if they exist
        await parser.load_twitter_config()


class DiscordParser(object):

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
        info('[{}] <{}> {}'.format(message.channel.name, message.author.name, message.content))

        if 'j4ne' in message.content.lower() and 'day' in message.content.lower():
            await self.on_triggered(message.channel)

        elif message.content.lower().startswith('j4ne'):
            query = message.content.lower().split('j4ne', 1)[1]
            if not query:
                return await client.send_message(message.channel, "Yes?")

            reply = CB.ask(query)
            reply = reply[:1].lower() + reply[1:]
            reply = '{}, {}'.format(message.author.name, reply)
            await client.send_message(message.channel, reply)

        elif message.content.startswith('|retweet'):
            await self.retweet(message)

        elif '|' in message.content:
            cmd = message.content.split('|')[1].split(' ')[0]
            if cmd in Commands:
                await Commands[cmd](client, message)


    async def retweet(self, message):

        tooter = message.content.split('|retweet')[1]
        if not tooter:
            return await self.say(message.channel, 'Who should I retweet?')

        tooter = tooter.strip()

        this_server = message.server

        conf = self._twitter_conf

        if not this_server in conf:
            conf[this_server] = {message.channel: []}

        if not message.channel in conf[this_server]:
            conf[this_server][message.channel] = []

        if message.channel in conf[this_server] and tooter in [t['screen_name'] for t in conf[this_server][message.channel]]:
            return await self.say(message.channel, 'I am already retweeting {} here.'.format(tooter))

        conf[this_server][message.channel].append( {'screen_name':tooter, 'last':None})

        await self.save_twitter_config()

        await self.say(message.channel, "I will start retweeting {} in this channel.  Brace for incoming tweet backlog!".format(tooter))

        await self.check_tweets()


    async def save_twitter_config(self):

        out = {}
        servers = {server.name:server for server in client.servers}

        for serv in self._twitter_conf.keys():
            out[serv.name] = {}
       
            for chann in self._twitter_conf[serv].keys():
                out[serv.name][chann.name] = []

                for tooter in self._twitter_conf[serv][chann]:
                    out[serv.name][chann.name].append(tooter)
                 
        with open('./twitterconf.json', 'w') as f:
            out = json.dumps(out, sort_keys=True, indent=4)

            f.write(out)


    async def load_twitter_config(self):

        from networks.twatter import twitter
        self._twitter = twitter

        with open('./twitterconf.json') as f:
            conf = json.loads(f.read())

            # replace server strings with proper objects
            servers = {server.name:server for server in client.servers}
            for servstring in [k for k in conf.keys()]:
                debug('Loading server {}'.format(servstring))

                if servstring in servers:

                    servobj = servers[servstring]
                    conf[servobj] = conf[servstring]
                    del conf[servstring]

                    for chanstring in [k for k in conf[servobj].keys()]:
                        channels = {channel.name:channel for channel in servers[servstring].channels}
                        chanobj = channels[chanstring]
                        conf[servobj][chanobj] = conf[servobj][chanstring]
                        del conf[servobj][chanstring]

            self._twitter_conf = conf

        # schedule polling for tweeters

        info('Twitter config loaded, polling for new tweets...')
        await self.check_tweets()
        tornado.ioloop.PeriodicCallback(self.check_tweets, 5*60*1000).start()


    async def check_tweets(self):

        for serv in self._twitter_conf.keys():
            debug(serv)

            for chann in self._twitter_conf[serv].keys():
                debug(chann)

                for tooter in self._twitter_conf[serv][chann]:

                    tweets = self._twitter.get_user_timeline(screen_name = tooter['screen_name'])
                    tweets.reverse()

                    for tweet in tweets:
                        if tooter['last'] and tweet['id'] <= tooter['last']:
                            continue

                        if tweet['in_reply_to_status_id']:
                            continue

                        await self.say(chann, '{} tweets: {}'.format(tweet['user']['screen_name'],tweet['text']))

                        tooter['last'] = tweet['id']

        await self.save_twitter_config()


parser = DiscordParser()
