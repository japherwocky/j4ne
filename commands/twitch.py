from commands import twitch_command as command
import logging

from tornado.httpclient import HTTPError

def auth_owner(func):
    """
    Decorator for registering commands
    """

    async def __decorator(network, channel, message):
        # easy on twitch - check that the author of the message == the channel
        author = message.author
        if '#{}'.format(author.lower()) != channel:
            await network.send_message(channel, 'Nice try, {}.'.format(message.author))

        else:
            return await func(network, channel, message)

    return __decorator


@command('mod')
@auth_owner
async def mod(network, channel, message):

    parts = message.content.split('mod',1)[1].strip().split(' ', 1)

    if not parts[0]:
        return await network.send_message(channel, 'Who did you want to mod, {}?'.format(message.author))

    # get user data from the API / check that it exists
    try:
        user = await network.application.TwitchAPI.query('https://api.twitch.tv/kraken/users/{}/'.format(parts[0]))
        logging.info(user)
        
    except HTTPError:
        return await network.send_message(channel, 'I could not find that user on twitch.')
        

    # import pdb;pdb.set_trace()


