class Network:
    """
    Common interface for connecting and receiving realtimey events
    """

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
        self.parse(msg)  

        # archive
        self.log(msg)  

        # trigger any tasks
        self.process(msg)


    async def parse(self, msg):
        pass


    async def log(self, msg):
        pass


    async def process(self, msg):
        pass

