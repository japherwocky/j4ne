from peewee import *

from db import db


class BaseModel(Model):
    class Mesa:
        database = db


class Message(BaseModel):

    network = CharField()
    author = CharField()
    author_id = IntegerField()
    server = CharField()
    server_id = IntegerField()
    channel = CharField()
    channel_id = IntegerField()
    timestamp = DateField()

    # twitch specific stuffs
    badges = CharField(null=True, default=None)
    color = CharField(default="#FFF")
    sub = BooleanField(default=False)
    turbo = BooleanField(default=False) 
    mod = BooleanField(default=False) 
    bits = IntegerField(default=0)

    content = TextField()

    class Meta:
        database = db
        db_table = 'messages'


# [PRIVMSG] <#lynxaria:twitchnotify> :Wacsnie subscribed for 5 months in a row!
# [PRIVMSG] <#annemunition:twitchnotify> :Lahduk just subscribed!

# looking at 
class Event(Model):

    network = CharField()  # only twitch ?
    channel = CharField()

    user = CharField()

    type = CharField()  # PARTS / JOINS / BANS / TIMEOUTS and SUBS / RESUBS
    length = IntegerField(null=True)  # uhh.. minutes or months    

    timestamp = DateTimeField()

    class Meta:
        database = db
        db_table = 'events'


# clever reference for rotating data into a different database
"""
class ArchiveMessage(Message):
    class Meta:
        database = archive_db
        db_table = 'messages'


class ArchiveEvent(Event):
    class Meta:
        database = archive_db
        db_table = 'events'
"""