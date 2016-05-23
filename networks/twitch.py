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

            if msg.startswith('PING'):
                # i think per the spec we're supposed to reply with whatever comes after the PING
                # in the case of twitch, it seems to always be ':tmi.twitch.tv'
                await self.conn.write_message('PONG :tmi.twitch.tv')

            # chat messages
            elif msg.startswith('@') and 'PRIVMSG' in msg:
                await self.on_message(msg)

            else:
                for line in msg.split('\r\n'):
                    if line:
                        try:
                            await self.on_event(line)
                        except:
                            logging.error(line)
                            raise


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

        # message == None for events
        if message and '|' in message.content:
            cmd = message.content.split('|')[1].split(' ')[0]

            if cmd in Commands:
                await Commands[cmd](self, message.channel, message)

    async def on_event(self, msg):
        msg = msg.strip()  # make sure newlines are gone

        if msg.startswith('@'):
            meta, msg = msg.split(' ', 1)
            meta = {foo:bar for foo,bar in [row.split('=') for row in meta.split(';')]}

        else:
            meta = {}

        parts = msg.split(' ', 3)
    
        user = parts[0][1:].split('!')[0]  # strip leading ':' and fake hostname stuff
        event = parts[1]
        channel = parts[2] if len(parts) > 2 else ''
        body = parts[3] if len(parts) > 3 else ''

        # logging.warning('[{}] <{}:{}> {}'.format(event, channel, user, body))


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


