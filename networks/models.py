from peewee import *
from playhouse.fields import ManyToManyField

from db import db

"""
flow is something like: 

|mod <twitch_user_name>
bot confirms account exists -> gets id, creates User account and Permission

from discord:
|sync <twitch_username>
bot whispers link to discord linker ?
-> grab official twitch ID
"""


class User(Model):

    name = CharField(null=True)
    twitch_id = IntegerField()
    twitch_name = CharField() 
    discord_id = IntegerField(null=True)
    discord_name = CharField(null=True)
    discord_invite = CharField(null=True)

    class Meta:
        database = db
        db_table = 'users'


class Moderator(Model):

    channel = CharField() # will we regret not making this a proper FK?
    network = CharField()
    user_id = ForeignKeyField(User)

    class Meta:
        database = db
        db_table = 'moderators'


#Twitter related tables
'''
twatter tables with many to many relations:
create_tables([
    Tooter,
    DiscordServer,
    DiscordServer.tooters.get_through_model(),
    DiscordChannel,
    DiscordChannel.tooters.get_through_model()  ])
'''
class Tooter(Model):
    screen_name = CharField(unique=True)
    last_tweet_id = IntegerField(default=0)
    retweeted_id = IntegerField(default=0)

    class Meta:
        database = db
        db_table = 'tooters'


class DiscordServer(Model):
    name = CharField()
    tooters = ManyToManyField(Tooter, related_name='servers')

    class Meta:
        database = db
        db_table = 'servers'


class DiscordChannel(Model):
    name = CharField()
    server = ForeignKeyField(DiscordServer, related_name='channels')
    tooters = ManyToManyField(Tooter, related_name='channels')

    class Meta:
        database = db
        db_table = 'channels'
   
