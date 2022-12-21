import asyncio
import unittest
from random import choice
from logging import info, debug, warning, error

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.testing
import tornado.platform.asyncio
from tornado.web import HTTPError, authenticated

# from networks.irc import IRC  # TODO

from db import db

from api.handlers import APIHandler

# from commands.jukebox import WebPlayer
# from charts import ChartHandler
# from webchat import WebHandler as ChatHandler
# from webchat import ChatSocketHandler


class App (tornado.web.Application):
    def __init__(self, debug=False):
        """
        Settings for our application
        """
        settings = dict(
            cookie_secret="changeme_in_production",  # ideally load this from elsewhere
            login_url="/login",
            template_path="templates",
            static_path="static",
            xsrf_cookies=False,
            autoescape=None,
            debug=debug,  # autoreloads on changes, among other things
        )

        """
        map URLs to Handlers, with regex patterns
        """

        handlers = [
            (r"/?", HomeHandler),
            (r"/login/?", LoginHandler),
            (r"/logout/?", LogoutHandler),
            (r"/api/(\w+)/(\w+)?/?", APIHandler),
        ]

        tornado.web.Application.__init__(self, handlers, **settings)


class AuthMixin(object):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    @property
    def user(self):
        return self.get_current_user()


class HomeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')


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
    define("serve", default=True, help="serve web requests on --port")
    define("debug", default=False, help="run server in debug mode", type=bool)
    define("mktables", default=False, help="bootstrap a new sqlite database")
    define("migration", default='', help="run a named database migration")
    define("addFeed", default='', help="attempt to create a feed from an address")

    define("runtests", default=False, help="Run tests")

    tornado.options.parse_command_line()

    if options.mktables:
        from db import seed
        return seed()

    if options.migration:
        from db import Migrations
        if options.migration not in Migrations:
            error('No migration named "{}", ignoring.'.format(options.migration))

        else:
            info('Attempting migration {}'.format(options.migration))
            return Migrations[options.migration]()

    if options.addFeed:
        from models.feeds import Feed
        return Feed.add(options.addFeed)

    if options.runtests:
        tornado.testing.main()
        return

    if options.serve:

        http_server = tornado.httpserver.HTTPServer(App(debug=options.debug), xheaders=True)
        http_server.listen(options.port)
        info('Serving web interface on port %d' % options.port)

    # use asyncio directly since tornado 6.2
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
