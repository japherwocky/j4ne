class Network (object):
    """
    Common interface for connecting and receiving realtimey events
    """

    def __init__(self, application):
        self.application = application

    def credentials(self):
        """
        Get any credentials this network will require to call `self.connect()`

        return True if we should connect, False if we're missing credentials
        """
        return True

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def reconnect(self):
        self.disconnect()
        self.connect()

    async def on_message(self, msg):
        #handle logging

        # classify & normalize
        msg = self.parse(msg)

        # archive
        self.log(msg)

        # trigger any tasks
        self.process(msg)

    async def parse(self, msg):
        """
        Normalize the raw message:
            * HTML encoding
            * unicode
            * timezones
        """
        return msg

    async def log(self, msg):
        pass

    async def process(self, msg):
        pass

