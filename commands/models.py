from peewee import *

from db import db


class Quote(Model):

    author = CharField()
    content = TextField()
    timestamp = DateField()

    class Meta:
        database = db
        db_table = 'quotes'

"""
|addcount command message
|addcount hooks Sledge the REAPER has hooked $count unfortunate souls.

|wipecount command
|setcount command <number>

"""

class Command(Model):

    network = CharField()  # network identifier
    channel = CharField()
    message = CharField()
    count = IntegerField(default=0)
    trigger = CharField()  # command to trigger the count

    class Meta:
        database = db
        db_table = 'commands'
