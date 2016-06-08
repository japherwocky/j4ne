from logging import debug, info
from time import time

from loggers.models import Message


# the first thought was to bake this into a base class, but maybe that's overengineered
def echo(msg):
    """ dump a copy of the chat into the console / stdout """
    info('[{}:{}] <{}> {}'.format(
        msg.server,
        msg.channel,
        msg.author,
        msg.content
        ))


class Discord(object):

    def __call__(self, message):
        """Take a raw message, break it into fields and insert into our database"""

        # TODO - links/embeds/attachments, as URLs? or something?
        msg = Message.create(
            network = 'discord',
            author_id = int(message.author.id),
            author = message.author.name,
            server_id = int(message.server.id) if message.server else 0,
            server = message.server.name if message.server else 'discord',
            channel_id = int(message.channel.id),
            channel = message.channel.name if hasattr(message.channel, 'name') else 'private',
            timestamp = time(),
            content = message.content,
        )

        echo(msg)

        return msg


class Twitch(object):
    def __call__(self, message):

        debug(message)

        # hrm, regex might be safer here

        # break messages down into metadata
        meta, user, event, channel, body = message.split(' ',4)

        meta = meta[1:]  # strip leading @
        meta = {foo:bar for foo,bar in [row.split('=') for row in meta.split(';')]}

        body = body.strip()[1:]  # clear endlines and leading ':'

        if meta and event == 'PRIVMSG':

            username = user.split('!')[0][1:]

            msg = Message.create(
                network = 'twitch',
                author_id = int(meta['user-id']),
                author = username,
                server_id = 1, # magic for twitch
                server = 'tmi.twitch.tv',
                channel_id = meta['room-id'],
                channel = channel,
                timestamp = time(),
                content = body,  # broken on links / comments with ':' actually
            )

            echo(msg)

            return msg


# a sub says <3
# @badges=subscriber/1;color=#FF69B4;display-name=Volpar;emotes=9:0-1;mod=0;room-id=51533859;subscriber=1;turbo=0;user-id=74043437;user-type= :volpar!volpar@volpar.tmi.twitch.tv PRIVMSG #annemunition :<3

# timeouts
# @ban-duration=5;ban-reason= :tmi.twitch.tv CLEARCHAT #annemunition :craqzviiper

# resubs 
# :twitchnotify!twitchnotify@twitchnotify.tmi.twitch.tv PRIVMSG #2mgovercsquared :raldain subscribed to Anthony_Kongphan for 2 months in a row!

