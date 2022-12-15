"""
Centralized db connection to avoid circular imports
"""
import logging
from peewee import SqliteDatabase
from peewee import CharField, IntegerField, BooleanField
from playhouse.migrate import SqliteMigrator, migrate


db = SqliteDatabase('database.db')
db.connect()


def mktables(destroy=False):
    # pass destroy=True to do the inverse (for testing)
    from loggers.models import Message, Event
    from commands.models import Quote, Command
    from networks.models import User, Moderator

    return [
        Message, Event, Quote, Command, User, Moderator
    ]


def seed():

    Tables = mktables()
    from peewee import OperationalError

    # ensure tables exist in db including intermediate tables for many to many relations
    try:
        """
        When `safe=True`, checks table exists before creating
        """
        db.create_tables(Tables, safe=True)
    except OperationalError as e:
        # table (probably/hopefully) exists, dump this into the console
        logging.warning(e)


Migrations = {}


def migration(name):

    def __decorator(func):
        Migrations[name] = func
        return func

    return __decorator


@migration('nothing')
def foo():
    """ An example migration that does nothing.  Run it like:
    `python j4ne.py --migration=nothing`
    """

    logging.info('Migrating nothing...')
