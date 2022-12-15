from db import Model
from peewee import CharField, IntegerField, TextField
import logging
import re


class Feed(Model):
    """ A source of content, RSS feeds for now """

    class Meta:
        db_table = 'feeds'

    # integer id by default
    address = CharField(null=False, unique=True)

    name = CharField(unique=True)
    last_seen = IntegerField(default=1)  # 
    type = CharField(default='domain')

    conf = TextField(null=True)  # JSON blob for feeds that require extra config

    @classmethod
    def add(cls, input):
        # try to create a feed from raw user input

        # pass a .txt with one feed per line
        if input.endswith('txt'):
            for line in open(input).readlines():
                try:
                    cls.add(line.strip('\r\n'))
                except:
                    logging.exception('Could not create feed from {}'.format(line))
                    raise

        else:
            # by default try to find a domain and a sitemap
            Sitemap.add(input)

        return 'OK'

    @classmethod
    def extract(cls):
        # check for new content, 

        # grab a copy if we need to

        # return the raw data, or False if we found nothing
        return False

    @classmethod
    def transform(cls, data):
        # sanitize data as needed
        pass

        # break it into individual components and yield one at a time
        yield data

    @classmethod
    def load(cls, row):
        # load/create one row at a time
        pass

        # return an instance of the Model
        return cls()


class Sitemap(Feed):

    @classmethod
    def add(cls, input):

        domain = Sitemap.parse(input)
        logging.info('Found domain: {}'.format(domain))

    @classmethod
    def parse(cls, input):
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        domains = re.findall(regex, input)
        domains = [x[0] for x in domains]
        # return [x[0] for x in url]

        if not domains:
            domain = input  # the regex won't find, eg, "wsjm.org"
        else:
            domain = domains[0]

        reDomain = r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)"
        domain = re.findall(reDomain, domain)[0]

        return domain
