
import feedparser
from random import randint
import re


def propagandize():
    d = feedparser.parse('http://feeds2.feedburner.com/fmylife')
    last_propaganda = d.entries[randint(0, len(d.entries)-1)]
    return strip_tags(last_propaganda.description).replace('FML', '')


def strip_tags(value):
    "Return the given HTML with all tags stripped."
    return re.sub(r'<[^>]*?>', '', value)
