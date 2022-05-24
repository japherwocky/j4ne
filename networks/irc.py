import os
import feedparser
from random import choice
from logging import info, debug


# because of EFnet, per Joel Rosdahl's irclib
import re
# _linesep_regexp = re.compile("\r?\n")
_linesep_regexp = "\r?\n"

join = os.path.join
exists = os.path.exists


class IRC(object):

    def connect_irc(self, host, port, ssl=False):
        import socket
        from tornado import iostream
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        if ssl:
            self._stream = iostream.SSLIOStream(s)
        else:
            self._stream = iostream.IOStream(s)

        self._stream.connect((host, port), self._handle_connect)

    def _handle_connect(self):
        # Send nick and channels

        self._write(('PASS', 'oauth:%s' % self.twitchtoken))
        self._write(('NICK', self.botname))
        self._write(('JOIN',), '#%s' % self.botname)

        self._stream.read_until("\r\n".encode('utf-8'), self._on_read)
        # self._stream.read_until_regex(_linesep_regexp, self._on_read)

    def _write(self, args, text=None):
        if text is not None:
            out = '%s :%s' % (' '.join(args), text)
        else:
            out = '%s' % ' '.join(args)

        debug('IRC> %s' % out)
        
        self._stream.write((out + '\r\n').encode('utf-8'))  # python3 required

    RE_ORIGIN = re.compile(r'([^!]*)!?([^@]*)@?(.*)')

    def _on_read(self, data):
        data = data.decode('utf-8')

        debug(data.strip())

        # Split source from data
        if data.startswith(':'):
            source, data = data[1:].split(' ', 1)
        else:
            source = None

        # Split arguments from message
        if ' :' in data:
            args, data = data.split(' :', 1)
        else:
            args, data = data, ''
        args = args.split()

        def parse_origin(raw_origin):
            """Parse a string similar to 'FSX!~FSX@hostname'
            into 'FSX', '~FSX' and 'hostname'"""

            match = self.RE_ORIGIN.match(raw_origin or '')

            return match.groups()  # Nickname, username, hostname

        # Parse the source (where the data comes from)
        nickname, username, hostname = parse_origin(source)

        # Respond to server ping to keep connection alive
        if args[0] == 'PING':
            self._write(('PONG', data))

        elif args[0] == 'INVITE':
            self.on_invite(nickname, data.strip())

        elif args[0] == 'PRIVMSG':
            # this is where we should hook in plugins
            self.on_msg(nickname, args[1], data.strip())

            if 'suck' in data:
                self.on_triggered(args[1])

            if username == 'japherwocky':
                # we want to iterate over regex patterns to match for commands
                if data.strip().startswith('join'):
                    channel = data.strip().split()[1]
                    if not channel.startswith('#'):
                        channel = '#' + channel

                    self.on_invite(username, channel)

        self._stream.read_until('\r\n'.encode('utf-8'), self._on_read)

    def on_invite(self, nickname, channel):

        info('Received invitation to %s from %s' % (channel, nickname))
        # check that it's from owner.. but this is moot on twitch
        self._write(('JOIN',), channel)

    def on_msg(self, from_nick, channel, msg):
        info('[%s] < %s> %s' % (channel, from_nick, msg))
        # self.say(channel, 'ACK')

    def say(self, channel, msg):
        info('[%s] < %s> %s' % (channel, self.botname, msg))
        self._write(('PRIVMSG', channel), msg)

    def on_triggered(self, channel):
        ''' someone said the magic word! '''

        posts = feedparser.parse('http://feeds2.feedburner.com/fmylife')
        post = choice(posts.entries)
        post = re.sub(r'<[^>]*?>', '', post.description).replace('FML', '')

        self.say(channel, str(post))
