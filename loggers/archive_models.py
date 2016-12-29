from db import archive_db 
import loggers.models as models




class Message(models.Message):

    class Meta:
        database = archive_db
        db_table = 'messages'
