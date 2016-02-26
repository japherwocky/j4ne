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
        yield client.start(discord_email, discord_pass)



@client.event
async def on_ready():
    info('Logged in as {} {}'.format(client.user.id, client.user.name) )


async def on_triggered(channel):
    ''' someone said the magic word! '''

    posts = feedparser.parse('http://feeds2.feedburner.com/fmylife')
    post = choice(posts.entries)
    post = re.sub(r'<[^>]*?>', '', post.description).replace('FML', '')

    await client.send_message(channel, str(post))


@client.event
async def on_message(message):
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
        await on_triggered(message.channel)

    elif message.content.startswith('|go'):
       
        channel = message.author.voice_channel
 
        voice = await client.join_voice_channel(channel)
        player = await voice.create_ytdl_player('https://www.youtube.com/watch?v=as68y7xmjr8')
        player.start()


