from commands import twitch_command as command
from networks.models import User, Moderator
from commands.models import Command
import logging

from tornado.httpclient import HTTPError

def owner_only(func):
    """
    Decorator for channel owner commands
    """

    async def __decorator(network, channel, message):
        # easy on twitch - check that the author of the message == the channel
        author = message.author
        if '#{}'.format(author.lower()) != channel:
            logging.warning( 'Nice try, {}.'.format(message.author) )
            return
            # await network.send_message(channel, 'Nice try, {}.'.format(message.author))

        else:
            return await func(network, channel, message)

    return __decorator


def mod_only(func):

    async def __decorator(network, channel, message):

        auth = False
        author = message.author

        # only enforce this on Twitch
        if network != network.application.Twitch:
            auth = True

        elif '#{}'.format(author.lower()) == channel:
            auth = True

        else:
            modQ = Moderator.select().join(User).where( (User.twitch_name == message.author) & (channel == channel))
            if modQ.count() == 1:
                auth = True

        if not auth:
            logging.warning( 'Nice try, {}.'.format(message.author) )
            return
            # await network.send_message(channel, 'Nice try, {}.'.format(message.author))

        else: 
            return await func(network, channel, message)

    return __decorator


@command('mod')
@owner_only
async def mod(network, channel, message):

    parts = message.content.split('mod',1)[1].strip().split(' ', 1)

    if not parts[0]:
        return await network.send_message(channel, 'Who did you want to mod, {}?'.format(message.author))

    # get user data from the API / check that it exists
    try:
        twitch_user = await network.application.TwitchAPI.query('https://api.twitch.tv/kraken/users/{}/'.format(parts[0]))

        # a valid user - see if we have them in the database yet
        user, created = User.get_or_create(twitch_id=twitch_user['_id'], twitch_name=parts[0].lower())
        if created:
            user.name = twitch_user['display_name']
            user.save()

        mod = Moderator.get_or_create(user_id=user, channel=channel, network='twitch')

        await network.send_message(channel, '{} now has moderator powers in this channel.'.format(user.name))

    except HTTPError:
        return await network.send_message(channel, 'I could not find that user on twitch.')
        

@command('unmod')
@owner_only
async def unmod(network, channel, message):

    parts = message.content.split('mod',1)[1].strip().split(' ', 1)

    if not parts[0]:
        return await network.send_message(channel, 'Who did you want to unmod, {}?'.format(message.author))

    target = parts[0].lower()  # normalize to lowercase for lookups

    modQ = Moderator.select().join(User).where((User.twitch_name==target) & (channel==channel))
    if modQ.count() == 0:
        return await network.send_message(channel, '{} was not a moderator, and remains so.'.format(target))
        
    modQ.get().delete_instance()
    return await network.send_message(channel, '{} has lost their moderator powers in this channel.'.format(target))


@command('addcommand')
@mod_only
async def addcommand(network, channel, message):
    parts = message.content.split('addcommand',1)[1].strip().split(' ', 1)

    if not len(parts) == 2:
        return await network.send_message(channel, 'I was looking for something like "|addcommand <trigger> <message (with $count)>", {}'.format(message.author))

    count_obj, created = Command.get_or_create(
        network='twitch', 
        channel=channel,
        trigger=parts[0].lower(),
        defaults = {'count':0, 'message':'Hello $count'}
        )

    count_obj.message = parts[1]
    count_obj.save()

    if created:
        return await network.send_message(channel, 'Count command "{}" is now active.'.format(count_obj.trigger))

    else:
        return await network.send_message(channel, '"{}" has been edited.'.format(count_obj.trigger))


@mod_only
async def custom(network, channel, message):

    trigger = message.content.split(' ')[0].strip('|')

    countQ = Command.select().where( Command.network == 'twitch', Command.channel == channel, Command.trigger == trigger )

    if not countQ.exists():
        return

    cmd = countQ.get()
    cmd.count += 1
    cmd.save()

    return await network.send_message(channel, cmd.message.replace('$count', str(cmd.count)))
