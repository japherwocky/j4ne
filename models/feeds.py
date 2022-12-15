from db import Model
from peewee import CharField, IntegerField, TextField


class Feed(Model):
    """ A source of content, RSS feeds for now """

    # integer id by default
    address = CharField(null=False, unique=True)

    name = CharField(unique=True)
    last_seen = IntegerField(default=1)  # 
    type = CharField(default='domain')

    conf = TextField(null=True)  # JSON blob for feeds that require extra config

    @classmethod
    def extract(cls):
        # check for new content, 

        # grab a copy if we need to

        # return the raw data, or False if we found nothing
        return False

    @classmethod
    def transform(cls, data):
        # sanitize data as needed
        pass

        # break it into individual components and yield one at a time
        yield data

    @classmethod
    def load(cls, row):
        # load/create one row at a time
        pass

        # return an instance of the Model
        return cls()