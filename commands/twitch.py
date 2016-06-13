from commands import twitch_command as command

from tornado.httpclient import HTTPError


@command('mod')
async def mod(network, channel, message):

    parts = message.content.split('mod',1)[1].strip().split(' ', 1)

    if not parts[0]:
        return await network.send_message(channel, 'Who did you want to mod, {}?'.format(message.author))

    # get user data from the API / check that it exists
    try:
        user = await network.application.TwitchAPI.query('https://api.twitch.tv/kraken/users/{}/'.format(parts[0]))
    except HTTPError:
        return await network.send_message(channel, 'I could not find that user on twitch.')
        

    # import pdb;pdb.set_trace()


