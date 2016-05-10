import logging
import tornado
from tornado.websocket import websocket_connect

from keys import twitch_name, twitch_token
from loggers.handlers import Twitch as Tlogger
Tlogger = Tlogger()

class TwitchParser(object):

    async def connect(self):

        conn = await websocket_connect('ws://irc-ws.chat.twitch.tv:80')
        await conn.write_message('CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership')
        await conn.write_message('PASS oauth:{}'.format(twitch_token))
        await conn.write_message('NICK {}'.format(twitch_name))
        await conn.write_message('JOIN #{}'.format(twitch_name))

        self.conn = conn

        while True:
            msg = await conn.read_message()
            if msg is None: break

            # chat messages
            if 'PRIVMSG' in msg:
                await self.on_message(msg)

            elif msg.startswith('PING'):
                # i think per the spec we're supposed to reply with whatever comes after the PING
                # in the case of twitch, I think that's always ':tmi.twitch.tv'
                await conn.write_message('PONG :tmi.twitch.tv')

            # server status messages, and who knows what else?
            else:
                print(msg)
                

    async def on_message(self, msg):
        Tlogger(msg)

def main():
    T = TwitchParser()
    tornado.ioloop.IOLoop.instance().run_sync(T.connect)

if __name__=="__main__":
    main()


