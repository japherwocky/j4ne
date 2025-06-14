import logging
import json
from datetime import datetime

import tornado
from tornado.websocket import websocket_connect
from tornado.platform.asyncio import to_asyncio_future

from env_keys import twitch_name, twitch_token, twitch_key

from loggers.models import Event
from commands import Twitch_commands as Commands
import commands.twitch
from loggers.handlers import Twitch as Tlogger
Tlogger = Tlogger()


class TwitchParser(object):

    async def connect(self):

        self.conn = await websocket_connect('ws://irc-ws.chat.twitch.tv:80')

        await self.conn.write_message('CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership')
        await self.conn.write_message('PASS oauth:{}'.format(twitch_token))
        await self.conn.write_message('NICK {}'.format(twitch_name))

        await self.conn.write_message('JOIN #{}'.format(twitch_name))
        follows = await self.application.TwitchAPI.follows()
        for channel in follows:
            logging.info('joining #{}'.format(channel))
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
                        except:  # noqa: E722
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
        except:  # noqa: E722
            logging.error(msg)
            raise

        # message == None for events
        if message and '|' in message.content:
            cmd = message.content.split('|')[1].split(' ')[0]

            if cmd in Commands:
                await Commands[cmd](self, message.channel, message)

            # TODO put this somewhere else
            elif message.content.startswith('|'):
                # look for custom counting commands
                await commands.twitch.custom(self, message.channel, message)

    async def on_event(self, msg):
        msg = msg.strip()  # make sure newlines are gone

        if msg.startswith('@'):
            meta, msg = msg[1:].split(' ', 1)
            meta = {foo: bar for foo, bar in [row.split('=') for row in meta.split(';')]}

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
            # logging.warning(msg)
            self.on_sub(user, channel, body)

        elif event == 'CLEARCHAT':
            self.on_timeout(user, channel, body, meta)

        else:
            # logging.warning('[{}] <{}:{}> {}'.format(event, channel, user, body))
            pass

    def on_part(self, user, channel, body):

        e = Event(
            network="twitch",
            channel=channel,
            user=user,
            type='PART',
            timestamp=datetime.now()
        )

        e.save()

    def on_join(self, user, channel, body):

        e = Event(
            network="twitch",
            channel=channel,
            user=user,
            type='JOIN',
            timestamp=datetime.now()
        )

        e.save()

    def on_sub(self, user, channel, body):

        # message is sent as user 'twitchnotify', pull this out of the body
        user = body[1:].split(' ')[0]

        e = Event(
            network="twitch",
            channel=channel,
            user=user,
            type='SUB',
            timestamp=datetime.now()
        )

        if 'subscribed for' in body:
            # wats regex
            e.length = int(body.split('subscribed for')[1].strip().split(' ', 1)[0])

        elif 'just subscribed!' in body:
            e.length = 1

        e.save()

    def on_timeout(self, user, channel, body, meta):

        user = body[1:]
        
        e = Event(
            network="twitch",
            channel=channel,
            user=user,
            type='TIMEOUT',
            timestamp=datetime.now()
        )

        if 'ban-duration' in meta:
            e.length = int(meta['ban-duration'])
            e.save()

            logging.warning('{} banned from chat for a hot {}'.format(user, e.length))

        else:

            e.length = 0  # kind of magical, use 0 to represent a ban
            e.save()

            logging.warning('{} PERMABANNED'.format(user))


class TwitchAPI(object):

    headers = { 
        'Accept': 'application/vnd.twitchtv.v5+json',  # specify v3, json
        'Client-ID': twitch_key,
        'Authorization': 'OAuth {}'.format(twitch_token)
        }

    async def connect(self):

        # the response says that we're authorized, not clear if it's necessary
        data = await self.query('https://api.twitch.tv/kraken')



    async def follows(self):
        follows = []
        twitch_id = await self.name2id(twitch_name)
        offset = 0
        nxt = 'https://api.twitch.tv/kraken/users/{}/follows/channels?offset={}'.format(twitch_id, offset)
        while nxt:
            response = await self.query(nxt)
            follows += [row['channel']['name'] for row in response['follows']]

            if response['_total'] > len(follows):
                offset += 25
                nxt = 'https://api.twitch.tv/kraken/users/{}/follows/channels?offset={}'.format(twitch_id, offset)
            else:
                nxt = False

        return follows

    async def query(self, path):
        # util method to make api reqs with the correct headers
        response = await to_asyncio_future(self.client.fetch(path, headers=self.headers))
        data = json.loads( response.body.decode('utf-8'))

        return data

    async def name2id(self, name):
        path = 'https://api.twitch.tv/kraken/users?login={}'.format(name)
        response = await self.query(path)

        return int(response['users'][0]['_id'])

    async def live(self):
        # get streams of anyone the bot is following
        response = await self.query('https://api.twitch.tv/kraken/streams/followed')

        return response['streams']

    async def detail(self, streamer):

        if type(streamer) == type('string'):
            #legacy, convert screen name to an id
            streamer = await self.name2id(streamer)

        response = await self.query('https://api.twitch.tv/kraken/streams/{}'.format(streamer))
        stream = response['stream']  # None if they are not live
        channel = await self.query('https://api.twitch.tv/kraken/channels/{}'.format(streamer))

        chan_id = channel['_id']
        hosts = await self.query('http://tmi.twitch.tv/hosts?include_logins=1&target={}'.format(chan_id))
        chatters = await self.query('http://tmi.twitch.tv/group/user/{}/chatters'.format(streamer))

        return {
            'channel': channel,
            'stream': stream,
            'hosts': hosts,
            'chatters': chatters,
        }
