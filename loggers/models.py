from peewee import *

# TODO - put connections elsewhere
db = SqliteDatabase('logs.db')
db.connect()  # peewee supports connection pooling, but we are single threaded


class Message(Model):

    network = CharField()
    author = CharField()
    author_id = IntegerField()
    server = CharField()
    server_id = IntegerField()
    channel = CharField()
    channel_id = IntegerField()
    timestamp = DateField()

    content = TextField()

    class Meta:
        database = db # This model uses the "people.db" database.
        db_table = 'messages'
