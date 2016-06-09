from commands import discord_command as command
from commands import twitch_command as tcommand
from commands.models import Quote
from random import choice
from time import time
from terminaltables import AsciiTable, SingleTable, DoubleTable, GithubFlavoredMarkdownTable
import asyncio
import datetime
from tornado.httpclient import HTTPError

import giphypop
G = giphypop.Giphy()

from keys import discord_app
from peewee import fn


@command('wizard')
@tcommand('wizard')
async def wizard(network, channel, message):

    wizards = [
        '`(∩｀-´)⊃━☆ﾟ.･｡ﾟ`',
        '`(⊃｡•́‿•̀｡)⊃━☆ﾟ.･｡ﾟ`',
        '`(∩ ͡° ͜ʖ ͡°)⊃━☆ﾟ . * ･ ｡ﾟ`',
        '`(∩ ͡°╭͜ʖ╮͡ ͡°)⊃━☆ﾟ. * ･ ｡ﾟ`',
         '`( ✿ ⊙ ͜ʖ ⊙ ✿ )━☆ﾟ.*･｡ﾟ`',
         '`( ∩ ✿⊙ ͜ʖ ⊙✿)⊃ ━☆ﾟ.*･｡ ﾟ`',
    ]

    await network.send_message(channel, choice(wizards))


@command('shrug')
@tcommand('shrug')
async def shrug(network, channel, message):
    await network.send_message(channel, '`¯\_(ツ)_/¯`')


@command('shame')
@tcommand('shame')
async def shrug(network, channel, message):
    await network.send_message(channel, '`ಠ_ಠ`')


@command('feelsbadfam')
async def feelsbadfam(network, channel, message):
    await network.send_file(channel, 'static/feelsbadfam.png')

@command('role')
async def role(network, channel, message):
    await network.send_file(channel, 'static/Sledge-Hook.gif')


@command('youropinion')
async def youropinion(network, channel, message):
    await network.send_file(channel, 'static/youropinion.png')


@command('lewd')
async def lewd(network, channel, message):
    lewds = ['anneLewd1.jpg', 'anneLewd2.gif', 'anneLewd3.png', 'sledgeLewd.gif', 'beanLewd.gif']  # TODO get some randint() action in here
    await network.send_file(channel, 'static/{}'.format(choice(lewds)))


@command('blush')
async def blush(network, channel, message):
    await network.send_file(channel, 'static/anneBlush.png')


@command('live')
async def live(network, channel, message):
    streams = await network.application.TwitchAPI.live()

    headers = ['Streamer', 'Game', 'Viewers', 'Uptime']

    out = [headers,]
    now = datetime.datetime.utcnow()
    for stream in streams:

        started = datetime.datetime.strptime(stream['created_at'],'%Y-%m-%dT%H:%M:%SZ')
        hours = (now-started).seconds // 3600
        minutes = ( (now-started).seconds // 60 ) % 60

        oneline = '{} has been live for {}:{}, now playing {} w/ {} viewers.\n'.format( 
            stream['channel']['display_name'], 
            hours,
            minutes,
            stream['game'], 
            stream['viewers']
            )

        oneline = [
            stream['channel']['display_name'], 
            stream['game'], 
            str(stream['viewers']), 
            '{}h{}m'.format(hours,minutes),
        ]

        out.append(oneline)

    table = AsciiTable(out)
    for i in range(len(out[0])):
        table.justify_columns[i] = 'center'

    await network.send_message(channel, '\n`{}`'.format(table.table))

@command('watch')
async def watch(network, channel, message):
    # details on a particular streamer
    if not message.content.lower().split('watch')[1]:
        return await network.send_message(channel, 'Which streamer did you want to watch?')

    # grab data from the twitch API
    strimmer = message.content.lower().split('watch')[1].strip()

    try:
        data = await network.application.TwitchAPI.detail( strimmer )
    except HTTPError:
        return await network.send_message(channel, "I could not find a streamer named {}".format(strimmer))

    if not data['stream']:

        out = """{} is offline right now, but you can follow them at <http://twitch.tv/{}/profile>""".format(
                data['channel']['display_name'], 
                strimmer
            )

    else:

        out = """{} is live, w/ {} viewers!\nWatch them at: http://twitch.tv/{}/""".format(
            data['channel']['display_name'], 
            str(data['stream']['viewers']), 
            data['channel']['name']
        )

    await network.send_message(channel, out)


@command('neat')
@tcommand('neat')
async def neat(network, channel, message):
    verbs = ['dandy', 'glorious', 'hunky-dory', 'keen', 'marvelous', 'neat', 'nifty', 'sensational', 'swell', 'spiffy']

    templates = [
        '{}!',
        'what a {} thing!',
        'that sure is {}!'
    ]

    out = choice(templates).format(choice(verbs))
    await network.send_message(channel, out)


@command('wgaff')
@tcommand('wgaff')
async def wgaff(network, channel, message):
    await network.send_message(channel, '┏(--)┓┏(--)┛┗(--﻿ )┓ WGAFF! ┏(--)┓┏(--)┛┗(--﻿ )┓')


@command('invite')
async def bot_invite(network, channel, message):
    perms = [
        '0x0000400',  # READ_MESSAGES
        '0x0000800',  # SEND_MESSAGES
        '0x0002000',  # DELETE_MESSAGES
        '0x0008000',  # ATTACH_FILES
        '0x0004000',  # EMBED_LINKS ?
        '0x0100000',  # CONNECT (to voice)
        '0x0200000',  # SPEAK
        '0x2000000',  # DETECT VOICE
    ]

    perm_int = sum([int(perm, 0) for perm in perms])

    link = 'https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions={}'.format(discord_app, perm_int)
    await network.send_message(channel, 'Invite me to your server here: {}'.format(link))


@command('8ball')
@tcommand('8ball')
async def magicball(network, channel, message):
    responses = [
        'It is certain',
        'It is decidedly so',
        'Without a doubt',
        'Yes, definitely',
        'You may rely on it',
        'As I see it, yes',
        'Most likely',
        'Outlook good',
        'Yes',
        'Signs point to yes',
        'Reply hazy try again',
        'Ask again later',
        'Better not tell you now',
        'Cannot predict now',
        'Concentrate and ask again',
        "Don't count on it",
        "My reply is no",
        "My sources say no",
        "Outlook not so good",
        "Very doubtful",
    ]

    if not message.content.lower().split('8ball')[1]:
        return await network.send_message(channel, 'What do you want me to ask the magic 8 ball?')

    await network.send_message(channel, choice(responses))


@command('giphy')
@tcommand('giphy')
async def giphy(network, channel, message):
    if not message.content.split('giphy')[1]:
        return await network.send_message(channel, 'What kind of GIF were you looking for?')

    results = G.search(message.content.split('giphy')[1])

    results = [r for r in results][:5]

    if not results:
        await network.send_message(channel, 'I could not find a GIF for that, {}'.format(message.author.name))
    else:
        result = choice(results)
        await network.send_message(channel, result)


@command('help')
@command('halp')
async def help(network, channel, message):
    from commands import Discord_commands as Commands
    cmds = ', '.join(['|{}'.format(k) for k in Commands.keys()])

    await network.send_message(channel, 'I am programmed to respond to the following commands: `{}`'.format(cmds))


@command('quote')
@tcommand('quote')
async def quote(network, channel, message):

    if not message.content.split('quote')[1]:
        return await network.send_message(channel, 'Quote who?')

    parts = message.content.split('quote',1)[1].strip().split(' ', 1)

    # exactly one arg
    if len(parts) == 1:

        # check if it's a user, random, or a specific quote
        author = parts[0].lower()

        try:
            # awkward, maybe use regex instead, check if it's an integer
            quote_id = int(author)
            Q = Quote.filter(id=quote_id)

        except ValueError:
            if author != 'random':
                Q = Quote.filter(author=author).order_by(fn.Random())

            else:
                # look for a quote from that specific user
                Q = Quote.select().order_by(fn.Random())

        if not Q.count():
            return await network.send_message(channel, 'I could not find a quote for {}'.format(author))

        out = Q.get()

        return await network.send_message(channel, '#{}: "{}" -- {}'.format(out.id, out.content, out.author.capitalize()))
                
    else:
        # add a quote for that user
        author, quote = parts
        author = author.lower()

        # TODO: guard against malicious quotes, probably?
        new = Quote(author=author, content=quote, timestamp=time())
        new.save()

        return await network.send_message(channel, 'Quote {} added: "{}" -- {}'.format(new.id, new.content, new.author.capitalize()))

