from peewee import *

from db import db, get_db


class Quote(Model):

    author = CharField()
    content = TextField()
    timestamp = DateField()

    class Meta:
        database = db
        db_table = 'quotes'

    def save(self, *args, **kwargs):
        # Use thread-local database connection
        self._meta.database = get_db()
        return super().save(*args, **kwargs)

"""
|addcount command message
|addcount hooks Sledge the REAPER has hooked $count unfortunate souls.

|wipecount command
|setcount command <number>

"""

class Command(Model):

    network = CharField()  # only twitch for now
    channel = CharField()
    message = CharField()
    count = IntegerField(default=0)
    trigger = CharField()  # command to trigger the count

    class Meta:
        database = db
        db_table = 'commands'
        
    def save(self, *args, **kwargs):
        # Use thread-local database connection
        self._meta.database = get_db()
        return super().save(*args, **kwargs)
