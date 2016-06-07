import logging
import json
from datetime import datetime

import tornado
from tornado.websocket import websocket_connect
from tornado.platform.asyncio import to_asyncio_future

from keys import twitch_name, twitch_token, twitch_key
from loggers.handlers import Twitch as Tlogger
Tlogger = Tlogger()
from loggers.models import Event
from commands import Twitch_commands as Commands

class TwitchParser(object):

    async def connect(self):

        self.conn = await websocket_connect('ws://irc-ws.chat.twitch.tv:80')

        await self.conn.write_message('CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership')
        await self.conn.write_message('PASS oauth:{}'.format(twitch_token))
        await self.conn.write_message('NICK {}'.format(twitch_name))

        await self.conn.write_message('JOIN #{}'.format(twitch_name))
        follows = await self.application.TwitchAPI.follows()
        for channel in follows:
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
        # kind of silly, TODO refactor the Logger function into here
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
            meta, msg = msg[1:].split(' ', 1)
            meta = {foo:bar for foo,bar in [row.split('=') for row in meta.split(';')]}

        else:
            meta = {}

        parts = msg.split(' ', 3)
    
        user = parts[0][1:].split('!')[0]  # strip leading ':' and fake hostname stuff
        event = parts[1]
        channel = parts[2] if len(parts) > 2 else ''
        body = parts[3] if len(parts) > 3 else ''

        # this is gross
        if event == 'PART':
            self.on_part(user, channel, body)
        elif event == 'JOIN':
            self.on_join(user, channel, body)

        elif event == 'PRIVMSG':
            # either a new sub or a resub; we've already filtered out chat messages 
            logging.warning(msg)
            self.on_sub(user, channel, body)

        elif event == 'CLEARCHAT':
            self.on_timeout(user, channel, body, meta)

        else:
            logging.warning('[{}] <{}:{}> {}'.format(event, channel, user, body))

    def on_part(self, user, channel, body):

        e = Event(
            network = "twitch",
            channel = channel,
            user = user,
            type = 'PART',
            timestamp = datetime.now()
        )

        e.save()

    def on_join(self, user, channel, body):

        e = Event(
            network = "twitch",
            channel = channel,
            user = user,
            type = 'JOIN',
            timestamp = datetime.now()
        )

        e.save()

    def on_sub(self, user, channel, body):

        # message is sent as user 'twitchnotify', pull this out of the body
        user =  body[1:].split(' ')[0]

        e = Event(
            network = "twitch",
            channel = channel,
            user = user,
            type = 'SUB',
            timestamp = datetime.now()
        )

        if 'subscribed for' in body:
            # wats regex
            e.length = int(body.split('for')[1].strip().split(' ',1)[0])

        elif 'just subscribed!' in body:
            e.length = 1

        e.save()

    def on_timeout(self, user, channel, body, meta):

        user = body[1:]
        
        e = Event(
            network = "twitch",
            channel = channel,
            user = user,
            type = 'TIMEOUT',
            timestamp = datetime.now()
        )

        if 'ban-duration' in meta:
            e.length = int(meta['ban-duration'])
            e.save()

            logging.warning('{} banned from chat for a hot {}'.format(user,e.length))

        else:

            e.length = 0  # kind of magical, use 0 to represent a ban
            e.save()

            logging.warning('{} PERMABANNED'.format(user))


class TwitchAPI(object):

    headers = { 
        'Accept': 'application/vnd.twitchtv.v3+json',  # specify v3, json
        'Client-ID': twitch_key,
        'Authorization': 'OAuth {}'.format(twitch_token)
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
        response = await to_asyncio_future(self.client.fetch(path, headers=self.headers))
        data = json.loads( response.body.decode('utf-8'))

        return data

    async def live(self):
        response = await self.query('https://api.twitch.tv/kraken/streams/followed'.format(twitch_name))

        return response['streams']

