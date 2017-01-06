from peewee import Using, fn
from db import db, archive_db
from loggers import models
from datetime import datetime, timedelta
import logging


def ensure_datetime(timestamp):
    if isinstance(timestamp, datetime):
        return timestamp
    else:
        return datetime.fromtimestamp(timestamp)


class custom_fn(fn):
    def datetime(timestamp):
        return ensure_datetime(timestamp)


def archivable_records_query(Model, cutoff):
    query = (Model
             .select()
             .where(custom_fn.datetime(Model.timestamp) < cutoff)
             .order_by(Model.timestamp.asc())
             .dicts())  # we want a dict for easily ceating new records
    return query


@archive_db.atomic()
def archive_record(record_as_dict, ArchiveModel):

    # ensure Table exists in archive
    ArchiveModel.create_table(fail_silently=True)
    result = (ArchiveModel
              .get_or_create(id=record_as_dict['id'],
                             defaults=record_as_dict))
    if result[1]:
        return 1
    else:
        return 0


@db.atomic()
def shuffle2archive(LiveModel, limit_one_row=True, cutoff_period=2):
    cutoff = datetime.now() - timedelta(days=cutoff_period)
    archivable_records = archivable_records_query(LiveModel, cutoff)

    logging.info('Attempting to archive model {} older than {}.\n'
                 'Please wait, the initial query will take some time'
                 ' to complete if there is a large number of records'
                 ' to be archived.'
                 .format(LiveModel, cutoff))

    if limit_one_row:
        archivable_records = archivable_records.limit(1)

    archived = 0
    deleted = 0

    for record in archivable_records:
        with Using(archive_db, [LiveModel]):
            archived += archive_record(record, LiveModel)
        #  delete the archived record from live database
        deleted += (LiveModel
                    .get(id=record['id'])
                    .delete_instance())

        if (archived % 1000 == 1) | (deleted % 1000 == 1):
            logging.info('Archived recrod from {} with date {}.\n'
                         'Total records archived: {}\n'
                         'Total records deleted: {}\n'
                         .format(LiveModel,
                                 ensure_datetime(record['timestamp']),
                                 archived,
                                 deleted))

    return (archived, deleted)


# for testing
class Message(models.Message):

    class Meta:
        database = archive_db
        db_table = 'messages'


class Event(models.Event):

    class Meta:
        database = archive_db
        db_table = 'events'
