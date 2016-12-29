import loggers.models as models
from db import db, archive_db
import loggers.archive_models as archives

from peewee import fn, IntegrityError
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


def get_single(Model):
    msgs = (Model
            .select()
            .group_by(Model)
            .having(fn.Min(Model.timestamp))
            .get())
    return msgs


def convert_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp)


def is_archivable(timestamp):
    delta = timedelta(days=2)
    now = datetime.now()
    return (now - timestamp) > delta


def archivable_date_limit(days=2):
    delta = timedelta(days=days)
    return datetime.now() - delta




def archive(cutoff_period=2, rows=3):
    cutoff = datetime.now() - timedelta(days=cutoff_period)
    msgs = (models.Message
            .select()
            .where(models.Message.timestamp < cutoff)
            .limit(rows))

    try:
        with archive_db.atomic():
            archive_db.connect()
            archives.Message.insert_many(msgs.dicts()).execute()
            archive_db.close()

            with db.atomic():
                for row in msgs:
                    (models.Message
                     .delete()
                     .where(models.Message.id == row.id))
        return 'Archive successful.'

    except IntegrityError:
        return 'Archiving failed: Records may already exist in archive.'
