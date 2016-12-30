from peewee import fn, IntegrityError
from db import db, archive_db
from datetime import datetime, timedelta

import loggers.archive_models as archives
import loggers.models as models


def convert_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp)


def oldest_record_query(Model):
    record = (Model
              .select()
              .group_by(Model)
              .having(fn.Min(Model.timestamp)))
    return record


def archive_row(LiveModel, ArchiveModel):
    livedb_query = oldest_record_query(LiveModel)
    # ensure Table exists in archive
    ArchiveModel.create_table(fail_silently=True)
    try:
        with archive_db.atomic():
            record_data = livedb_query.dicts().get()
            archive_db.connect()
            ArchiveModel.insert(record_data).execute()
            archive_db.close()

            with db.atomic():
                (LiveModel
                 .delete()
                 .where(LiveModel.id == livedb_query.get().id)
                 .execute())
        return 'Record archived successfully.'

    except IntegrityError:
        return "Archiving failed: there was an issue with either saving the record to archive or deleting from live database."


def shuffle2archive(cutoff_period=2):
    cutoff = datetime.now() - timedelta(days=cutoff_period)

    oldest_msg = oldest_record_query(models.Message).get()

    while convert_timestamp(oldest_msg.timestamp) < cutoff:
        archive_row(models.Message, archives.Message)
        oldest_msg = oldest_record_query(models.Message).get()

    oldest_event = oldest_record_query(models.Event).get()

    while oldest_event.timestamp < cutoff:
        archive_row(models.Event, archives.Event)
        oldest_event = oldest_record_query(models.Event).get()
