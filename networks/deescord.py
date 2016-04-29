from logging import info, debug, error
from random import choice, shuffle
from array import array
import asyncio
import re
import os
import json

import discord
from youtube_dl.utils import DownloadError
import feedparser

from tornado import gen
import tornado.ioloop

from websockets.exceptions import InvalidState

from keys import discord_email, discord_pass
from commands import Commands, command
import commands.deescord

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
                yield client.start(discord_email, discord_pass)
            except InvalidState:
                error('websocket closed, will try to reconnect')
                self.DiscordParser.stop()
                continue
    

    @client.event
    async def on_ready():
        info('Logged in as {} {}'.format(client.user.id, client.user.name) )

        # try to load tweeters if they exist
        await parser.load_twitter_config()



class VolumeBuff(object):
    """
        Kind of a volume aware buffer mixin.
    """

    def __init__(self, player, buff):
        self.player = player
        self.buff = buff
        self.frame_count = 0

    def read(self, frame_size):
        self.frame_count += 1
        frame = self.buff.read(frame_size)

        volume = self.player.volume
        # Only make volume go down. Never up.
        if volume < 1.0:
            # Ffmpeg returns s16le pcm frames.
            frame_array = array('h', frame)

            for i in range(len(frame_array)):
                frame_array[i] = int(frame_array[i] * volume)

            frame = frame_array.tobytes()

        return frame


class DiscordParser(object):
    voice = None
    voicechan = None
    player = None

    keep_playing = True

    _volume = 69  # store this as 1-100
    playlist = []  # seeded with __init__
    requests = []

    def __init__(self):
        with open('playlist.txt') as f:
            self.playlist = f.readlines()
            shuffle(self.playlist)

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


    async def summon(self, message):
        ''' Try to join the author's voice channel '''
        authorchan = message.author.voice_channel

        if not authorchan:
            return await self.say(message.channel, 'You must join a voice channel first, {}'.format(message.author.name))

        # check if this is new or we're moving
        if client.is_voice_connected():

            # already connected somewhere - here?
            if authorchan == self.voicechan:
                return await self.say(message.channel, 'I am already in your channel, {}'.format(message.author.name))

            # or leave so we can join the new channel
            else:
                await self.voice.disconnect()

        # join the author's voice channel
        self.voicechan = authorchan
        self.voice = await client.join_voice_channel(authorchan)


    async def banish(self, message):
        ''' Clear out any pre-existing voice connections '''
        if client.is_voice_connected():
            await self.voice.disconnect()

        self.voicechan = self.voice = None


    async def request(self, message):
        req = message.content.split('|request ')[1]

        # they didn't manage to request a song
        if not req:
            await self.say(message.channel, "What would you like to request, {}?".format(message.author.name))
            return

        if not self.voice:
            await self.say(message.channel, "I am not in a voice channel, {}".format(message.author.name))
            return

        # let's see if it works
        try:
            player = await self.voice.create_ytdl_player(req, options='-bufsize 520k', after=self.on_end)
            player._url = req
        except DownloadError as exc:
            await self.say(message.channel, "I could not find that, {}".format(message.author.name))
        
        await self.say(message.channel, '{} has been added to the queue.'.format(player.title))

        self.requests.append(player)


    async def play(self, message):

        if not (self.voice and self.voicechan):
            await self.say(message.channel, 'I am not in a voice channel, {}'.format(message.author.name))
            return 

        # check if we are already playing something
        if self.player and self.player.is_playing():
            await self.say(message.channel, 'I am already playing, {}'.format(message.author.name))
            return

        self.keep_playing = True

        self.playchan = message.channel  # reset the channel we want to talk in
        await self.playsong()


    async def nextsong(self):
        """ 
        Get the next song, whether from a request or the stock playlist
        """
        player = False

        if not self.requests:
            while not player:
                url = self.playlist.pop()
                try:
                    player = await self.voice.create_ytdl_player(url, options='-bufsize 520k', after=self.on_end)
                    self.playlist.insert(0, url)  # put it back in the end of the list
                except DownloadError as exc:
                    info('{} was invalid, discarding from list'.format(url))
                    continue

        else:
            player = self.requests.pop(0)

            # re-init the player, we get TLS errors if it has been in the request list for too long
            player = await self.voice.create_ytdl_player(player._url, options='-bufsize 520k', after=self.on_end)

        return player


    async def playsong(self):

        try:
            player = await self.nextsong()
 
            # instantiate player, hack in volume controls   
            player.buff = VolumeBuff(player, player.buff)  # so awkward
            player.volume = self._volume / 100.0  # not to be confused with the command

            self.player = player
            player.start()

            # update our status 
            await client.change_status( discord.Game(name = player.title[:128]) )
        except InvalidState:
            # eep, we got disconnected mid song
            await self.stop()

    async def song(self, message):
        if not (self.player and self.player.is_playing()):
            return await self.say(message.channel, 'I am not playing right now.')

        await self.say(message.channel, 'Now playing **{}**'.format(self.player.title))
       


    def on_end(self):
        if self.keep_playing:
            tornado.ioloop.IOLoop.instance().add_callback(lambda: self.playsong())

 
    async def stop(self, message=None):

        # set this before calling .stop(), the end callback will check for it
        self.keep_playing = False

        if self.player:
            self.player.stop()
            self.player = None

        await client.change_status(None)

        if message:
            await self.say( message.channel, ':hammer: time')


    async def skip(self, message):

        if self.player:
            self.player.stop()


    async def volume(self, message):

        txt = message.content.strip('|volume')

        if txt:
            try:
                vol = int(txt)
            except ValueError:
                return await self.say(message.channel, 'Please try a number between 1 and 100, {}'.format(message.author.name))

            self._volume = vol

        if self.player:
            self.player.volume = self._volume / 100.0

        return await self.say(message.channel, 'The volume is set at {}'.format(self._volume))


    async def queue(self, message):

        if not self.requests:
            await self.say(message.channel, 'There are no requests right now, {}'.format(message.author.name))

        else:
            await self.say(message.channel, 'There are {} requests, next up is {}'.format(len(self.requests), self.requests[0].title))

    
    async def on_message(self, message):
        info('[{}] <{}> {}'.format( message.channel.name, message.author.name, message.content )) 
    
        if 'j4ne' in message.content.lower() and 'day' in message.content.lower():
            await self.on_triggered(message.channel)

        elif message.content.startswith('|summon'):
            await self.summon(message)

        elif message.content.startswith('|banish'):
            await self.banish(message)
    
        elif message.content.startswith('|play'):
            await self.play(message)

        elif message.content.startswith('|song'):
            await self.song(message)

        elif message.content.startswith('|request'):
            await self.request(message)

        elif message.content.startswith('|queue'):
            await self.queue(message)

        elif message.content.startswith('|skip'):
            await self.skip(message)

        elif message.content.startswith('|stop'):
            await self.stop(message)

        elif message.content.startswith('|volume'):
            await self.volume(message)

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

        await self.say(message.channel, "I will start retweeting {} in this channel.  Brace for incoming tweets.".format(tooter))

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
