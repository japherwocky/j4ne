from logging import info, debug, error
from random import choice, shuffle
from cleverbot import Cleverbot

import asyncio
import re
import os
import json
import requests
import html

import discord

import feedparser

from tornado import gen
import tornado.ioloop

from keys import discord_token

from commands import Discord_commands as Commands
from commands import discord_command as command
import commands.deescord
import commands.jukebox

from loggers.handlers import Discord as Dlogger
Dlogger = Dlogger()

# instantiate this here to use decorators
client = discord.Client()  # loop defaults to asyncio.get_event_loop()

# We need to wrap connect() as a task to prevent timeout error at runtime.
# based on the following suggested fix: https://github.com/KeepSafe/aiohttp/issues/1176
def connect_deco(func):
    async def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().create_task(func(*args, **kwargs))
    return wrapper

class Discord(object):
    _Twitter = None
    CB = Cleverbot()

    client = client  # so that network specific commands can access lower levels

    @connect_deco
    async def connect(self):

        """
        @client.event
        async def on_message(message):
            await self.on_message(message)
        """
        self.client = client

        @client.event
        async def on_ready():
            info('Logged in as {} {}'.format(client.user.id, client.user.name) )

            # try to load tweeters if they exist
            await self.load_twitter_config()

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

        conf = self._twitter_conf

        if not this_server in conf:
            conf[this_server] = {message.channel: []}

        if not message.channel in conf[this_server]:
            conf[this_server][message.channel] = []

        if message.channel in conf[this_server] and tooter in [t['screen_name'] for t in conf[this_server][message.channel]]:
            return await self.say(message.channel, 'I am already retweeting {} here.'.format(tooter))

        conf[this_server][message.channel].append( {'screen_name':tooter, 'last':1})

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

    def normalize_tweet(self, tweet):

        tweet['text'] = html.unescape(tweet['text'])

        """
        # twitter sets a cookie in the redirect, so this is basically moot
        # for attachments.  
        if 'https://t.co/' in tweet['text']:
            link = tweet['text'].split('https://t.co/', 1)[1].strip(')').split()[0]
            link = 'https://t.co/' + link

            resp = requests.head(link)

            if 'location' not in resp.headers:
                # we grabbed the URL wrong somehow, abort
                return tweet

            real_link = '<{}>'.format(resp.headers['location'])

            tweet['text'] = tweet['text'].replace(link, real_link)
        """

        return tweet

    async def check_tweets(self):

        for serv in self._twitter_conf.keys():
            debug(serv)

            for chann in self._twitter_conf[serv].keys():
                debug(chann)

                for tooter in self._twitter_conf[serv][chann]:

                    tweets = self._twitter.get_user_timeline(screen_name = tooter['screen_name'])
                    tweets.reverse()
                    if tooter['last'] == 1:
                        tweets = [tweets[-1],]

                    for tweet in tweets:
                        if tooter['last'] > 1 and tweet['id'] <= tooter['last']:
                            continue

                        tooter['last'] = tweet['id']

                        if tweet['in_reply_to_status_id']:
                            continue

                        tweet = self.normalize_tweet(tweet)

                        if 'retweeted_status' in tweet:
                            user = tweet['retweeted_status']['user']['screen_name']
                            tweet_id = tweet['retweeted_status']['id']
                            retweet_link = 'https://twitter.com/{}/status/{}'.format(user, tweet_id)

                            if not tweet['is_quote_status']:
                                await self.say(chann, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                                continue

                            else:
                                await self.say(chann, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                                continue

                        await self.say(chann, '{} tweets:\n\n{}\n\n'.format(tweet['user']['screen_name'], tweet['text']))


        await self.save_twitter_config()

