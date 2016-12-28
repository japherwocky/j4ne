from peewee import SqliteDatabase
from loggers.models as models

from db import archive_db


class Message(models.Message):

    class Meta:
        database = archive_db


class Event(models.Event):

    class Meta:
        database = archive_db
