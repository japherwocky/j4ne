from peewee import *

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
