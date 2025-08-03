from commands import discord_command as command
from random import choice
from time import time
from terminaltables import AsciiTable, SingleTable, DoubleTable, GithubFlavoredMarkdownTable
import asyncio
import datetime
from tornado.httpclient import HTTPError

import giphypop
G = giphypop.Giphy()

from keys import discord_app_id
from discord_invite import invite_link
from peewee import fn
from commands.models import Quote, Command

# Simple decorator to replace the removed Twitch mod_only functionality
def mod_only(func):
    """Placeholder decorator - mod functionality removed with Twitch integration"""
    return func


@command('wizard')
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
async def shrug(network, channel, message):
    await network.send_file(channel, 'static/lul.PNG')


@command('shame')
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


@command('megapracejudge')
async def megajudge(network, channel, message):
    await network.send_file(channel, 'static/megapracejudge.png')

@command('megapracefail')
async def megafail(network, channel, message):
    await network.send_file(channel, 'static/megapracefail.png')

@command('lewd')
async def lewd(network, channel, message):
    lewds = ['anneLewd1.jpg', 'anneLewd2.gif', 'anneLewd3.png', 'anneLewd4.gif', 'sledgeLewd.gif', 'beanLewd.gif']  # TODO get some randint() action in here
    await network.send_file(channel, 'static/{}'.format(choice(lewds)))

@command('dance')
async def dance(network, channel, message):
    await network.send_file(channel, 'static/mculdance.gif')


@command('blush')
async def blush(network, channel, message):
    await network.send_file(channel, 'static/anneBlush.png')

@command('hm')
async def youropinion(network, channel, message):
    await network.send_file(channel, 'static/hm.gif')

@command('vote')
async def youropinion(network, channel, message):
    await network.send_file(channel, 'static/NOVOTES.gif')

@command('cool')
async def youropinion(network, channel, message):
    await network.send_file(channel, 'static/anneCool.gif')

@command('nani')
async def nani(network, channel, message):
    await network.send_file(channel, 'static/nani.gif')

# Twitch-dependent commands removed: live, watch


@command('neat')
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
async def wgaff(network, channel, message):
    await network.send_file(channel, 'static/WGAFFgif.gif')

@command('panic')
async def wgaff(network, channel, message):
    await network.send_file(channel, 'static/panic.gif')

# Twitch-specific commands removed: twitchwgaff, twitchfollowing


@command('invite')
async def bot_invite(network, channel, message):
    link = invite_link(discord_app_id)
    await network.send_message(channel, 'Invite me to your server here: {}'.format(link))


@command('8ball')
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
@mod_only
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
@mod_only
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


# @command('addcommand')
async def addcommand(network, channel, message):
    parts = message.content.split('addcommand',1)[1].strip().split(' ', 1)

    if not len(parts) == 2:
        return await network.send_message(channel, 
            'I was looking for something like "addcommand <trigger> <message (with $count)>", {}'.format(message.author.name))

    count_obj, created = Command.get_or_create(
        network=message.server.name,
        channel=channel.name,
        trigger=parts[0].lower(),
        defaults = {'count':0, 'message':'Hello $count'}
        )

    count_obj.message = parts[1]
    count_obj.save()

    if created:
        return await network.send_message(channel, 'Command "{}" is now active.'.format(count_obj.trigger))

    else:
        return await network.send_message(channel, '"{}" has been edited.'.format(count_obj.trigger))


async def custom(network, channel, message):

    trigger = message.content.split(' ')[0].strip('|')

    countQ = Command.select().where( Command.trigger == trigger )

    if not countQ.exists():
        return

    cmd = countQ.get()
    cmd.count += 1
    cmd.save()

    return await network.send_message(channel, cmd.message.replace('$count', str(cmd.count)))
