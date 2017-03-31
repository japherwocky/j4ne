import requests
from collections import defaultdict

class Cl3ver(object):

    API_URL = "https://www.cleverbot.com/getreply"
    IDENTITY = "cl3ver"
    VERSION = "0.1"

    STATE = defaultdict(str)

    def __init__(self, key):
        self.KEY = key  # user's API key


    def say(self, text, name=None):
        """
        Main interface, pass it a string of text, and see what the bot has to say.

        To keep multiple conversations threaded, pass a name,
        eg user ID or alias
        """

        ask = {
            'input': text,
            'key': self.KEY,
            'cs': self.STATE[name],
            'wrapper': '{}v{}'.format(self.IDENTITY, self.VERSION)
        }

        # synchronous :(
        reply = requests.get(self.API_URL, params=ask)
        reply = reply.json()

        self.STATE[name] = reply['cs']

        return reply['output']

