import logging
import tornado
from tornado.websocket import websocket_connect

from keys import twitch_name, twitch_token
from loggers.handlers import Twitch as Tlogger
Tlogger = Tlogger()

from commands import Twitch_commands as Commands

class TwitchParser(object):

    async def connect(self):

        self.conn = await websocket_connect('ws://irc-ws.chat.twitch.tv:80')

        await self.conn.write_message('CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership')
        await self.conn.write_message('PASS oauth:{}'.format(twitch_token))
        await self.conn.write_message('NICK {}'.format(twitch_name))
        await self.conn.write_message('JOIN #{}'.format(twitch_name))


        while True:
            msg = await self.conn.read_message()
            if msg is None: break

            # chat messages
            if 'PRIVMSG' in msg:
                await self.on_message(msg)

            elif msg.startswith('PING'):
                # i think per the spec we're supposed to reply with whatever comes after the PING
                # in the case of twitch, I think that's always ':tmi.twitch.tv'
                await self.conn.write_message('PONG :tmi.twitch.tv')

            # server status messages, and who knows what else?
            else:
                logging.warning(msg.strip())

    async def send_message(self, channel, message):

        out = 'PRIVMSG {} :{}'.format(channel, message)
        response = await self.conn.write_message(out)
        logging.info(out)
                

    async def on_message(self, msg):
        message = Tlogger(msg)

        if '|' in message.content:
            cmd = message.content.split('|')[1].split(' ')[0]

            if cmd in Commands:
                await Commands[cmd](self, message.channel, message)

