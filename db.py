"""
Centralized db connection to avoid circular imports
"""

from peewee import SqliteDatabase
db = SqliteDatabase('database.db')
db.connect()
