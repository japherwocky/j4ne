from logging import debug, info
from time import time

from loggers.models import Message

class Discord(object):
    def __init__(self):
        pass

    def __call__(self, message):
        """Take a raw message, break it into fields and insert into our database"""

        # todo - links/embeds/attachments, as URLs? or something?
        Message.create(
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
