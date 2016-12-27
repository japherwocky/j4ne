from loggers.archive_models import Message, ArchiveMessage
from db import db, archive_db
from datetime import datetime, timedelta
from loremipsum import get_sentences
from random import randrange


def msg_row_fn(timestamp, content):
    row = {'network': 'networkone',
           'author': 'author',
           'author_id': 1,
           'server': 'server',
           'server_id': 1,
           'channel': 'channel',
           'channel_id': 1,
           'timestamp': timestamp,
           'content': content}
    return row


def gen_batch_msg_data():
    timedeltas = ([3 for x in range(5)] +
                  [2 for x in range(5)] +
                  [1 for x in range(5)] +
                  [0 for x in range(5)])

    dates = list(map(lambda x: datetime.now() - timedelta(x), timedeltas))
    contents = get_sentences(20)
    batch_data = list(map(msg_row_fn, dates, contents))

    return batch_data


def batch_insert(batch_data, model, database):
    with database.atomic():
        model.insert_many(batch_data).execute()
