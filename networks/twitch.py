import logging
import json

import tornado
from tornado.websocket import websocket_connect

from keys import twitch_name, twitch_token, twitch_key
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
        for channel in await self.app.TwitchAPI.follows():
            await self.conn.write_message('JOIN #{}'.format(channel))


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

            elif 'JOIN' in msg or 'PART' in msg:
                logging.info('{} parts/joins'.format(len(msg.split('\n'))))

            # server status messages, and who knows what else?
            else:
                logging.warning(msg.strip())

    async def send_message(self, channel, message):

        out = 'PRIVMSG {} :{}'.format(channel, message)
        response = await self.conn.write_message(out)
        logging.info(out)
                

    async def on_message(self, msg):
        try:
            message = Tlogger(msg)
        except Exception as e:
            logging.error(msg)
            raise

        if '|' in message.content:
            cmd = message.content.split('|')[1].split(' ')[0]

            if cmd in Commands:
                await Commands[cmd](self, message.channel, message)


# from tornado.httpclient import AsyncHTTPClient
# client = AsyncHTTPClient()
class TwitchAPI(object):

    headers = { 
        'Accept': 'application/vnd.twitchtv.v3+json',  # specify v3, json
        'Client-ID': twitch_key,  # TODO, not clear why this doesn't work
        }


    async def connect(self):

        data = await self.query('https://api.twitch.tv/kraken')

        # on the extremely off chance that these endpoints actually change
        self.links = data['_links']


    async def follows(self):
        response = await self.query('https://api.twitch.tv/kraken/users/{}/follows/channels'.format(twitch_name))
        return [row['channel']['name'] for row in response['follows']]

    async def query(self, path):
        # util method to make api reqs with the correct headers
        response = await self.client.fetch(path, headers=self.headers)
        data = json.loads( response.body.decode('utf-8'))

        return data


