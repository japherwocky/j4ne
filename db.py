"""
Centralized db connection to avoid circular imports
"""
import logging
from peewee import SqliteDatabase
from peewee import CharField, IntegerField, BooleanField
from playhouse.migrate import SqliteMigrator, migrate


db = SqliteDatabase('database.db')
db.connect()


def mktables():
    # utility for bootstrapping a database
    from models.feeds import Feed

    return [
        Feed,
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


from peewee import Model as protoModel
class Model(protoModel):
    """base model for our classes, control database strings here"""

    class Meta:
        database = db


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
