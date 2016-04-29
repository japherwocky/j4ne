from commands import command
from random import choice

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
    lewds = ['anneLewd1.jpg','anneLewd2.gif','anneLewd3.png']  # TODO get some randint() action in here
    await client.send_file(message.channel, 'static/{}'.format(choice(lewds)))


@command('blush')
async def blush(client, message):
    await client.send_file(message.channel, 'static/anneBlush.png')


@command('help')
@command('halp')
async def help(client, message):
    from commands import Commands
    cmds = ', '.join(['|{}'.format(k) for k in Commands.keys()])

    await client.send_message(message.channel, 'I am programmed to respond to the following commands: `{}`'.format(cmds))