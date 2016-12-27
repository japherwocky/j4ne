"""
Centralized db connection to avoid circular imports
"""
import logging
from peewee import SqliteDatabase
from peewee import CharField, IntegerField, BooleanField

db = SqliteDatabase('database.db')
archive_db = SqliteDatabase('archive.db')

db.connect()

Migrations = {}
def migration(name):

    def __decorator(func):
        Migrations[name] = func
        return func

    return __decorator


@migration('nothing')
def foo():
    """ An example migration that does nothing.  Run it like:
    `python j4ne.py --migration=foo`
    """

    logging.info('Migrating nothing...')

from playhouse.migrate import SqliteMigrator, migrate
@migration('bits')
def bits():
    """ bits, badges, colors, yolo """
    migrator = SqliteMigrator(db)

    badges = CharField(null=True, default=None)
    color = CharField(default="#FFF")
    bits = IntegerField(default=0)
    sub = BooleanField(default=False)
    turbo = BooleanField(default=False)
    mod = BooleanField(default=False)

    migrate(
        migrator.add_column('messages', 'bits', bits),
        migrator.add_column('messages', 'badges', badges),
        migrator.add_column('messages', 'color', color),
        migrator.add_column('messages', 'sub', sub),
        migrator.add_column('messages', 'turbo', turbo),
        migrator.add_column('messages', 'mod', mod),
    )
