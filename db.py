"""
Centralized db connection to avoid circular imports
"""
import logging
import threading
from peewee import SqliteDatabase
from peewee import CharField, IntegerField, BooleanField
from playhouse.migrate import SqliteMigrator, migrate

# Use thread-local storage for database connections
_thread_local = threading.local()

def get_db():
    """Get a thread-local database connection."""
    if not hasattr(_thread_local, 'db'):
        _thread_local.db = SqliteDatabase('database.db')
    return _thread_local.db

def get_archive_db():
    """Get a thread-local archive database connection."""
    if not hasattr(_thread_local, 'archive_db'):
        _thread_local.archive_db = SqliteDatabase('archive.db')
    return _thread_local.archive_db

# For backward compatibility
db = SqliteDatabase('database.db', check_same_thread=False)
archive_db = SqliteDatabase('archive.db', check_same_thread=False)

# Don't connect at import time
# db.connect()

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


@migration('bits')
def bits():
    """ bits, badges, colors, yolo """
    db = get_db()
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
