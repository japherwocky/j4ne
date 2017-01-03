from peewee import fn, IntegrityError
from db import db, archive_db
from datetime import datetime, timedelta
import logging


def ensure_datetime(timestamp):
    if isinstance(timestamp, datetime):
        return timestamp
    else:
        return datetime.fromtimestamp(timestamp)


@db.atomic()
def archivable_records_query(Model, cutoff):
    query = (Model
             .select()
             .where(Model.timestamp < cutoff)
             .order_by(Model.timestamp.asc())
             .dicts())  # we want a dict for ceating new record
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


# @db.atomic() reminder: talk about the trade offs of this decorator and if its wanted
def shuffle2archive(LiveModel, ArchiveModel, limit_one_row=True, cutoff_period=2):
    cutoff = datetime.now() - timedelta(days=cutoff_period)
    archivable_records = archivable_records_query(LiveModel, cutoff) # todo: see what happens when nothing is archivable

    logging.info('Attempting to archive model {} older than {}.\n'
                 'Please wait, the initial query will take some time'
                 'to complete if there is a large number of recrods'
                 'to be archived.'
                 .format(LiveModel, cutoff))

    if limit_one_row:
        archivable_records = archivable_records.limit(1)

    archived = 0
    deleted = 0
    for record in archivable_records:
        archived += archive_record(record, ArchiveModel)

        #  delete the archived record from live database
        deleted += (LiveModel
                    .get(id=record['id'])
                    .delete_instance())

        if True: #(archived % 100 == 1) | (deleted % 100 == 1):
            logging.info('Archived model {} with date {}.\n'
                         'Total records archived: {}\n'
                         'Total records deleted: {}\n'
                         .format(LiveModel,
                                 record['timestamp'],
                                 archived,
                                 deleted))

    return (archived, deleted)
