from logging import info, debug
from random import choice, shuffle
from array import array
import asyncio
import re

import discord
from youtube_dl.utils import DownloadError
import feedparser

from tornado import gen
import tornado.ioloop

from keys import discord_email, discord_pass

client = discord.Client()  # loop defaults to asyncio.get_event_loop()


class Discord(object):
    """ Mixin for the main App """

    @gen.coroutine
    def discord_connect(self):
        self.DiscordParser = DiscordParser()  # not sure what magic actually hooks up the handlers

        @client.event
        async def on_message(message):
            await self.DiscordParser.on_message(message)

        yield client.start(discord_email, discord_pass)

    @client.event
    async def on_ready():
        info('Logged in as {} {}'.format(client.user.id, client.user.name) )



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

    _volume = 13  # store this as 1-100 
    playlist = []  # seeded with __init__
    requests = []

    def __init__(self):
        with open('playlist.txt') as f:
            self.playlist = f.readlines()
            shuffle(self.playlist)


    async def say(self, channel, message):
        msg = await client.send_message(channel, message)


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
        req = message.content.strip('|request ')

        # they didn't manage to request a song
        if not req:
            await self.say(message.channel, "What would you like to request, {}?".format(message.author.name))
            return

        if not self.voice:
            await self.say(message.channel, "I am not in a voice channel, {}".format(message.author.name))
            return

        # let's see if it works
        try:
            player = await self.voice.create_ytdl_player(req, ytdl_options={'default-search':'ytsearch'}, after=self.on_end)
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
                    player = await self.voice.create_ytdl_player(url, after=self.on_end)
                    self.playlist.insert(0, url)  # put it back in the end of the list
                except DownloadError as exc:
                    info('{} was invalid, discarding from list'.format(url))
                    continue

        else:
            player = self.requests.pop(0)

        return player


    async def playsong(self):

        player = await self.nextsong()
 
        # instantiate player, hack in volume controls   
        player.buff = VolumeBuff(player, player.buff)  # so awkward
        player.volume = self._volume / 100.0  # not to be confused with the command

        self.player = player
        player.start()

        await self.say(self.playchan, 'Now playing {}'.format(player.title))


    def on_end(self):
        if self.keep_playing:
            tornado.ioloop.IOLoop.instance().add_callback(lambda: self.playsong())

 
    async def stop(self, message):

        # set this before calling .stop(), the end callback will check for it
        self.keep_playing = False

        if self.player:
            self.player.stop()
            self.player = None


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
    
        if message.content.startswith('!test'):
            counter = 0
            tmp = await client.send_message(message.channel, 'Calculating messages...')
            async for log in client.logs_from(message.channel, limit=100):
                if log.author == message.author:
                    counter += 1
    
            await client.edit_message(tmp, 'You have {} messages.'.format(counter))

        elif message.content.startswith('!sleep'):
            await asyncio.sleep(5)
            await client.send_message(message.channel, 'Done sleeping')
    
        elif 'eeyore' in message.content:
            await self.on_triggered(message.channel)
    

        elif message.content.startswith('|summon'):
            await self.summon(message)

        elif message.content.startswith('|banish'):
            await self.banish(message)
    
        elif message.content.startswith('|play'):
            await self.play(message)

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
    
