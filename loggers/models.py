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
