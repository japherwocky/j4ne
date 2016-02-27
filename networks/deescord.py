from logging import info, debug
from random import choice
import asyncio
import feedparser
import re

import discord
from tornado import gen

from keys import discord_email, discord_pass

client = discord.Client()  # loop defaults to asyncio.get_event_loop()

class Discord(object):
    """ Mixin for the main App """

    @gen.coroutine
    def go(self):
        self.DiscordParser = DiscordParser()  # not sure what magic actually hooks up the handlers

        @client.event
        async def on_message(message):
            await self.DiscordParser.on_message(message)

        yield client.start(discord_email, discord_pass)

    @client.event
    async def on_ready():
        info('Logged in as {} {}'.format(client.user.id, client.user.name) )


class DiscordParser(object):
    voice = None
    voicechan = None

    async def say(self, channel, message):
        msg = await client.send_message(channel, message)


    async def on_triggered(self, channel):
        ''' someone said the magic word! '''
    
        posts = feedparser.parse('http://feeds2.feedburner.com/fmylife')
        post = choice(posts.entries)
        post = re.sub(r'<[^>]*?>', '', post.description).replace('FML', '')
    
        await self.say(channel, str(post))


    async def on_summon(self, message):
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


    async def on_banish(self, message):
        ''' Clear out any pre-existing voice connections '''
        if client.is_voice_connected():
            await self.voice.disconnect()

        self.voicechan = self.voice = None
    
    
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
    
        elif message.content.startswith('|go'):
           
            channel = message.author.voice_channel
     
            voice = await client.join_voice_channel(channel)
            player = await voice.create_ytdl_player('https://www.youtube.com/watch?v=as68y7xmjr8')
            player.start()

        elif message.content.startswith('|summon'):
            await self.on_summon(message)

        elif message.content.startswith('|banish'):
            await self.on_banish(message)
    
    
