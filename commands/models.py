from peewee import *

from db import db


class Quote(Model):

    author = CharField()
    content = TextField()
    timestamp = DateField()

    class Meta:
        database = db
        db_table = 'quotes'
