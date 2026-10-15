"""
IRC delivery (card #986), against a fake IRC server on localhost: the bot
runs on the caller's own loop, answers a channel in the channel and a DM to
the person who sent it, and stays down after disconnect.
"""

import asyncio

import pytest

from networks.irc import IRCClient


class FakeChat:
    def __init__(self):
        self.calls = []

    async def process_query(self, history, session_key=None):
        self.calls.append((list(history), session_key))
        return f"reply to {history[-1]['content']}"


class FakeIRCServer:
    """Welcomes one client, then records every line it sends"""

    def __init__(self):
        self.lines = []
        self.connections = 0
        self.writer = None
        self.got_line = asyncio.Event()

    async def start(self):
        self.server = await asyncio.start_server(self.handle, "127.0.0.1", 0)
        return self.server.sockets[0].getsockname()[1]

    async def handle(self, reader, writer):
        self.connections += 1
        self.writer = writer
        self.say(":fake 001 j4ne-bot :Welcome")
        self.say(":fake 376 j4ne-bot :End of MOTD")
        try:
            while line := await reader.readline():
                self.lines.append(line.decode().rstrip("\r\n"))
                self.got_line.set()
        finally:
            # Server.wait_closed() waits for every connection to be closed
            writer.close()

    def say(self, line):
        self.writer.write((line + "\r\n").encode())

    async def wait_for(self, prefix, timeout=5):
        async def poll():
            while not any(line.startswith(prefix) for line in self.lines):
                self.got_line.clear()
                await self.got_line.wait()
        await asyncio.wait_for(poll(), timeout)
        return [line for line in self.lines if line.startswith(prefix)]

    async def stop(self):
        self.server.close()
        if self.writer:
            self.writer.close()
        await asyncio.wait_for(self.server.wait_closed(), 5)


async def wait_until(condition, timeout=5):
    async def poll():
        while not condition():
            await asyncio.sleep(0.02)
    await asyncio.wait_for(poll(), timeout)


def test_irc_is_off_without_a_server(monkeypatch):
    monkeypatch.delenv("IRC_SERVER", raising=False)
    client = IRCClient()
    assert client.server is None
    assert asyncio.run(client.connect()) is False


def test_irc_round_trip(monkeypatch):
    async def scenario():
        server = FakeIRCServer()
        port = await server.start()
        monkeypatch.setenv("IRC_SERVER", "127.0.0.1")
        monkeypatch.setenv("IRC_PORT", str(port))
        monkeypatch.setenv("IRC_CHANNELS", "#chan")

        chat = FakeChat()
        client = IRCClient(chat_client=chat)
        try:
            assert await client.connect()
            await wait_until(lambda: client.connected)
            await server.wait_for("JOIN #chan")

            # A mention in the channel is answered in the channel
            server.say(":bob!b@host PRIVMSG #chan :j4ne-bot: what time is it")
            [reply] = await server.wait_for("PRIVMSG #chan")
            assert reply == "PRIVMSG #chan :reply to bob: j4ne-bot: what time is it"

            # A DM is answered to its sender, not to a channel named after the bot
            server.say(":alice!a@host PRIVMSG j4ne-bot :hello there")
            [dm_reply] = await server.wait_for("PRIVMSG alice")
            assert dm_reply == "PRIVMSG alice :reply to alice: hello there"
            assert not any(line.startswith("PRIVMSG #j4ne-bot") for line in server.lines)

            # Each conversation has its own history and session
            assert chat.calls[0][1] == "irc:#chan"
            assert chat.calls[1][1] == "irc:dm:alice"
            assert [m["content"] for m in chat.calls[1][0]] == ["alice: hello there"]

            # Chatter that does not address the bot gets no answer
            server.say(":carol!c@host PRIVMSG #chan :just talking")
            await asyncio.sleep(0.2)
            assert len(chat.calls) == 2
        finally:
            await client.disconnect()

        await server.wait_for("QUIT")
        # irc3 reconnects after 2 seconds unless the connection was closed on purpose
        await asyncio.sleep(2.5)
        assert server.connections == 1
        await server.stop()

    asyncio.run(scenario())
