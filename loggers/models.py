from peewee import *

from db import db


class Message(Model):

    network = CharField()
    author = CharField()
    author_id = IntegerField()
    server = CharField()
    server_id = IntegerField()
    channel = CharField()
    channel_id = IntegerField()
    timestamp = DateField()

    content = TextField()

    class Meta:
        database = db
        db_table = 'messages'
