import os
join = os.path.join
exists = os.path.exists
import json
import feedparser
from random import choice
from logging import info, debug
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.web import HTTPError
from markdown import markdown


# because of EFnet, per Joel Rosdahl's irclib
import re
_linesep_regexp = re.compile("\r?\n")


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

        self._write(('NICK', self.botname))
        self._write(('USER', self.botname, '+iw', self.botname), self.botname)
        self._write(('JOIN',), '#test')

        self._stream.read_until_regex(_linesep_regexp, self._on_read)

    def _write(self, args, text=None):
        if text is not None:
            self._stream.write('%s :%s\r\n' % (' '.join(args), text))
        else:
            self._stream.write('%s\r\n' % ' '.join(args))

    RE_ORIGIN = re.compile(r'([^!]*)!?([^@]*)@?(.*)')

    def _on_read(self, data):
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
            self.on_invite(nickname, username, data.strip())

        elif args[0] == 'PRIVMSG':
            # this is where we should hook in plugins
            self.on_msg(nickname, args[1], data.strip())

            if 'suck' in data:
                self.on_triggered(args[1])

        self._stream.read_until('\r\n', self._on_read)

    def on_invite(self, nickname, username, channel):

        info('Received invitation to %s from %s' % (channel, nickname))
        # check that it's from owner.. but this is moot on twitch
        self._write(('JOIN',), channel)

    def on_msg(self, from_nick, channel, msg):
        info('[%s] < %s> %s' % (channel, from_nick, msg))
        # self.say(channel, 'ACK')

    def say(self, channel, msg):
        self._write(('PRIVMSG', channel), msg)

    def on_triggered(self, channel):
        ''' someone said the magic word! '''

        posts = feedparser.parse('http://feeds2.feedburner.com/fmylife')
        post = choice(posts.entries)
        post = re.sub(r'<[^>]*?>', '', post.description).replace('FML', '')

        self.say(channel, str(post))


class App (tornado.web.Application, IRC):
    def __init__(self, botname, app_debug=False):
        """
        Settings for our application
        """
        settings = dict(
            cookie_secret="changemeplz",  # ideally load this from elsewhere
            login_url="/login",
            template_path="templates",
            static_path="static",
            xsrf_cookies=False,
            autoescape=None,
            debug=app_debug,  # autoreloads on changes, among other things
        )

        """
        map URLs to Handlers, with regex patterns
        """

        handlers = [
            (r"/", MainHandler),
            (r"/auth/?", AuthHandler),
            (r"(?!\/static.*)(.*)/?", DocHandler),
        ]

        tornado.web.Application.__init__(self, handlers, **settings)

        # connect to whatever IRC network
        self.connect_irc('pearachute.net', 6667)
        self.botname = botname  # should maybe just snag this out of options globally?


class MainHandler(tornado.web.RequestHandler):
    def get(self):

        txt = open('docs/hello.txt').read()
        doc = markdown(txt)
        self.render('index.html', doc=doc)

class AuthHandler(tornado.web.RequestHandler):
    def get(self):

        self.render('auth.html', twitch_key='2jgz7axdvzidve3ipaa3gggig3zaj0t')

    def post(self):

        token = self.get_argument('token')
        username = self.get_argument('name')

        info('got token %s for user %s' % (token, username))

        self.redirect('/')


class DocHandler(tornado.web.RequestHandler):
    """ Main blog post handler.  Look in /docs/ for whatever
        the request is trying for, render it as markdown
    """

    def get(self, path):

        path = 'docs/' + path.replace('.', '').strip('/')
        if exists(path):
            # a folder
            lastname = os.path.split(path)[-1]
            txt = open('%s/%s.txt' % (path, lastname)).read()

        elif exists(path+'.txt'):
            txt = open(path+'.txt').read()

        else:
            # does not exist!
            raise HTTPError(404)

        doc = markdown(unicode(txt, 'utf-8'))
        self.render('doc.html', doc=doc)


def main():
    from tornado.options import define, options
    define("port", default=8888, help="run on the given port", type=int)
    define("debug", default=False, help="run server in debug mode", type=bool)
    define("runtests", default=False, help="run tests", type=bool)
    define("botname", default='Test Bot', help="name of the bot")

    tornado.options.parse_command_line()

    if options.runtests:
        """ put tests in the tests folder """
        import tests
        import unittest
        import sys
        sys.argv = ['pearachute.py', ]  # unittest messes with argv
        unittest.main('tests')
        return

    http_server = tornado.httpserver.HTTPServer(App(options.botname, app_debug=options.debug))
    http_server.listen(options.port)
    info('Serving on port %d' % options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
