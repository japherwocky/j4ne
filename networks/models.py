from peewee import *
from db import db


class User(Model):

    """ A generic user model, used by the |trust system """

    name = CharField(null=True)
    twitch_id = IntegerField()
    twitch_name = CharField()
    discord_id = IntegerField(null=True)  # these are stubs, pending cross network linking somehow
    discord_name = CharField(null=True)
    discord_invite = CharField(null=True)

    class Meta:
        database = db
        db_table = 'users'


class Moderator(Model):

    """ A "trusted" user """

    channel = CharField()  # will we regret not making this a proper FK?
    network = CharField()
    user_id = ForeignKeyField(User)

    class Meta:
        database = db
        db_table = 'moderators'


class Retweets(Model):

    """ Twitter accounts to be retweeted into discord channels, see |retweet """

    tooter = CharField()
    last_tweet_id = IntegerField(default=0)
    discord_channel = CharField()  # maybe this is actually an integer?

    class Meta:
        database = db
        db_table = 'retweets'
