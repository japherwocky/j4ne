import asyncio
import unittest
import feedparser
from random import choice
from logging import info, debug, warning
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.testing
import tornado.platform.asyncio
from tornado.web import HTTPError, authenticated
from markdown import markdown

# from networks.irc import IRC

from db import db

class App (tornado.web.Application):
    def __init__(self, app_debug=False):
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
            (r"/login/?", LoginHandler),
            (r"/logout/?", LogoutHandler),
        ]

        tornado.web.Application.__init__(self, handlers, **settings)


class AuthMixin(object):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    @property
    def user(self):
        return self.get_current_user()


class LoginHandler(tornado.web.RequestHandler):
    """
    super awkward naming now, basically a util to auth with twitch 
    and spit the oauth token out to stdout
    """
    def get(self):
        from keys import twitch_key
        self.render('auth.html', twitch_key=twitch_key)

    def post(self):

        token = self.get_argument('token')
        username = self.get_argument('name')

        info('got token %s for user %s' % (token, username))



class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        """ this is slightly weird, because we'll log the user out of this app
        but _not_ out of twitch.  If they (or anyone) hits a route with
        with @authenticated, and they're still signed into twitch, it will
        auto sign them back in.  yolo.
        """
        self.clear_cookie('user')

        self.finish('o/')


def all():
    return unittest.defaultTestLoader.discover('tests')


def main():
    from tornado.options import define, options
    define("port", default=8888, help="serve web requests from the given port", type=int)
    define("debug", default=False, help="run server in debug mode", type=bool)
    define("mktables", default=False, help="bootstrap a new sqlite database")

    define("twitch", default=True, help="Connect to Twitch chat servers")
    define("twitchapi", default=True, help="Connect to Twitch API")
    define("discord", default=True, help="Connect to Discord chat servers")

    define("runtests", default=False, help="Run tests")

    tornado.options.parse_command_line()

    if options.mktables:
        from loggers.models import Message, Event
        from commands.models import Quote

        from peewee import OperationalError

        for table in [Message, Event, Quote]:
            try:
                db.create_table(table)
            except OperationalError as e:
                # table (probably/hopefully) exists, dump this into the console 
                warning(e)
                continue

    if options.runtests:
        tornado.testing.main()
        return

    app = App(app_debug=options.debug)

    http_server = tornado.httpserver.HTTPServer(app)
    tornado.platform.asyncio.AsyncIOMainLoop().install()  # uses default asyncio.loop()

    http_server.listen(options.port)
    info('Serving on port %d' % options.port)

    # connect to discord 
    if options.discord:
        from networks.deescord import Discord
        app.Discord = Discord()
        tornado.ioloop.IOLoop.instance().add_callback(app.Discord.connect)  

    # connect to Twitch API
    if options.twitchapi:
        from networks.twitch import TwitchParser, TwitchAPI

        app.TwitchAPI = TwitchAPI()
        app.TwitchAPI.app = app

        from tornado.httpclient import AsyncHTTPClient
        app.TwitchAPI.client = AsyncHTTPClient()

        tornado.ioloop.IOLoop.instance().add_callback(app.TwitchAPI.connect)  

    # connect to Twitch
    if options.twitch:
        app.Twitch = TwitchParser()
        app.Twitch.app = app

        tornado.ioloop.IOLoop.instance().add_callback(app.Twitch.connect)  

    
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
