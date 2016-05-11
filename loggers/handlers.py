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
            server_id = int(message.server.id),
            server = message.server.name,
            channel_id = int(message.channel.id),
            channel = message.channel.name,
            timestamp = time(),
            content = message.content,
        )

        echo(msg)


class Twitch(object):
    def __call__(self, message):
        # break messages down into metadata
        meta = meta[1:]  # strip leading @

        # hrm, regex might be safer here
        meta = {foo:bar for foo,bar in [row.split('=') for row in meta.split(';')]}

        msg = Message.create(
            network = 'twitch',
            author_id = int(meta['user-id']),
            author = msg.split('!',1)[0][1:],
            server_id = 1, # magic for twitch
            server = 'tmi.twitch.tv',
            channel_id = meta['room-id'],
            channel = msg.split('PRIVMSG')[1].split(':')[0].strip(),
            timestamp = time(),
            content = msg.rsplit(':',1)[1].strip(),
        )

        echo(msg)

