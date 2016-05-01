from commands import command
from random import choice
import asyncio

@command('wizard')
async def wizard(client, message):

    wizards = [
        '`(∩｀-´)⊃━☆ﾟ.･｡ﾟ`',
        '`(⊃｡•́‿•̀｡)⊃━☆ﾟ.･｡ﾟ`',
        '`(∩ ͡° ͜ʖ ͡°)⊃━☆ﾟ . * ･ ｡ﾟ`',
        '`(∩ ͡°╭͜ʖ╮͡ ͡°)⊃━☆ﾟ. * ･ ｡ﾟ`',
        '`( ✿ ⊙ ͜ʖ ⊙ ✿ )━☆ﾟ.*･｡ﾟ`',
        '`( ∩ ✿⊙ ͜ʖ ⊙✿)⊃ ━☆ﾟ.*･｡ ﾟ`',
    ]

    await client.send_message(message.channel, choice(wizards))


@command('shrug')
async def shrug(client, message):
    await client.send_message(message.channel, '`¯\_(ツ)_/¯`')


@command('shame')
async def shrug(client, message):
    await client.send_message(message.channel, '`ಠ_ಠ`')


@command('feelsbadfam')
async def feelsbadfam(client, message):
    await client.send_file(message.channel, 'static/feelsbadfam.png')


@command('youropinion')
async def youropinion(client, message):
    await client.send_file(message.channel, 'static/youropinion.png')


@command('lewd')
async def lewd(client, message):
    lewds = ['anneLewd1.jpg', 'anneLewd2.gif', 'anneLewd3.png']  # TODO get some randint() action in here
    await client.send_file(message.channel, 'static/{}'.format(choice(lewds)))


@command('blush')
async def blush(client, message):
    await client.send_file(message.channel, 'static/anneBlush.png')


@command('neat')
async def neat(client, message):
    verbs = ['dandy', 'glorious', 'hunky-dory', 'keen', 'marvelous', 'neat', 'nifty', 'sensational', 'swell', 'spiffy']

    templates = [
        '{}!',
        'what a {} thing!',
        'that sure is {}!'
    ]

    out = choice(templates).format(choice(verbs))
    await client.send_message(message.channel, out)


@command('wgaff')
async def wgaff(client, message):
    await client.send_message(message.channel, '┏(--)┓┏(--)┛┗(--﻿ )┓ WGAFF! ┏(--)┓┏(--)┛┗(--﻿ )┓')


@command('invite')
async def bot_invite(client, message):
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

    link = 'https://discordapp.com/oauth2/authorize?&client_id=176104440372133888&scope=bot&permissions={}'.format(perm_int)
    await client.send_message(message.channel, 'Invite me to your server here: {}'.format(link))


@command('8ball')
async def magicball(client, message):
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

    if not message.content.split('8ball')[1]:
        return await client.send_message(message.channel, 'What do you want me to ask the magic 8 ball?')

    msg = await client.send_message(message.channel, '_shakes the magic 8 ball_')
    await asyncio.sleep(3)
    await client.edit_message(msg, choice(responses))


@command('help')
@command('halp')
async def help(client, message):
    from commands import Commands
    cmds = ', '.join(['|{}'.format(k) for k in Commands.keys()])

    await client.send_message(message.channel, 'I am programmed to respond to the following commands: `{}`'.format(cmds))