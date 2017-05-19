import asyncio
import unittest
import feedparser
from random import choice
from logging import info, debug, warning, error

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.testing
import tornado.platform.asyncio
from tornado.web import HTTPError, authenticated
from markdown import markdown

# from networks.irc import IRC  # TODO

from db import db
from api.handlers import APIHandler
from commands.jukebox import WebPlayer
from charts import ChartHandler
from webchat import WebHandler as ChatHandler
from webchat import ChatSocketHandler


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
            (r"/?", HomeHandler),
            (r"/login/?", LoginHandler),
            (r"/logout/?", LogoutHandler),
            (r"/jukebox/?", WebPlayer),
            (r"/stats/?", ChartHandler),
            (r"/chat/?", ChatHandler),
            (r"/chatsocket/?", ChatSocketHandler),
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
    define("debug", default=False, help="run server in debug mode", type=bool)
    define("mktables", default=False, help="bootstrap a new sqlite database")
    define("migration", default='', help="run a named database migration")
    define("archive", default=False, help="archive live database")

    define("twitch", default=True, help="Connect to Twitch chat servers")
    define("twitchapi", default=True, help="Connect to Twitch API")
    define("discord", default=True, help="Connect to Discord chat servers")
    define("twitter_setup", default=False, help="setup twitter account integration")
    define("twitter", default=True, help="Connect to Twitter")
    define("newbot", default=False, help="Generates a Discord server invite link for a new bot instance")

    define("runtests", default=False, help="Run tests")

    tornado.options.parse_command_line()

    if options.mktables:
        from loggers.models import Message, Event
        from commands.models import Quote, Command
        from networks.models import User, Moderator

        from peewee import OperationalError
        from networks.models import DiscordChannel, Tooter

        tables = [
            Message,
            Event,
            Quote,
            Command,
            User,
            Moderator,
            Tooter,
            DiscordChannel,
            DiscordChannel.tooters.get_through_model() # many-to-many 
        ]

        # ensure tables exist in db including intermediate tables for many to many relations
        try:
            """
            When `safe=True`, checks table exists before creating
            """
            db.create_tables(tables, safe=True)
        except OperationalError as e:
            # table (probably/hopefully) exists, dump this into the console
            warning(e)

    if options.migration:
        from db import Migrations
        if options.migration not in Migrations:
            error('No migration named "{}", ignoring.'.format(options.migration))

        else:
            info('Attempting migration {}'.format(options.migration))
            return Migrations[options.migration]()

    if options.archive:
        from loggers.archive import shuffle2archive
        from loggers import models

        # (live_models, archive_models)
        models2archive = [models.Message,
                          models.Event]

        for LiveModel in models2archive:
            info('Starting archive shuffle with model {}'.format(LiveModel))

            try:
                number_of_records = shuffle2archive(LiveModel, False, 224)  # temporary cutoff period
                info('Shuffle finished with {} records archived'
                 'and {} records deleted from model {}'
                 .format(number_of_records[0],
                         number_of_records[1],
                         LiveModel))
            except LiveModel.DoesNotExist:
                info('No records exist before archivable date')

    if options.runtests:
        tornado.testing.main()
        return

    tornado.platform.asyncio.AsyncIOMainLoop().install()  # uses default asyncio.loop()

    app = App(app_debug=options.debug)
    http_server = tornado.httpserver.HTTPServer(app)

    http_server.listen(options.port)
    info('Serving on port %d' % options.port)

    # Discord options:
    ## new bot instance authentication
    if options.newbot:
        from keys import discord_app_id
        from discord_invite import invite_link
        info("Please go to the following link to authorize the bot, then press `Enter`:\n")
        print(invite_link(discord_app_id))
        info("\nPress `Enter` to continue...")

    ## connect to discord 
    if options.discord:
        from networks.deescord import Discord
        app.Discord = Discord()
        app.Discord.application = app

        @asyncio.coroutine
        def Drunner():
            errcount = 0
            while errcount < 3:
                try:
                    yield from app.Discord.connect()
                except Exception as e:
                    error(e)
                    continue
                errcount += 1
        asyncio.ensure_future(Drunner())


        # tornado.ioloop.IOLoop.instance().add_callback(app.Discord.connect)  

    # connect to Twitch API
    if options.twitchapi:
        from networks.twitch import TwitchParser, TwitchAPI
        app.TwitchAPI = TwitchAPI()
        app.TwitchAPI.application = app

        from tornado.httpclient import AsyncHTTPClient
        app.TwitchAPI.client = AsyncHTTPClient()

        tornado.ioloop.IOLoop.instance().add_callback(app.TwitchAPI.connect)  

    # connect to Twitch chat
    if options.twitch:
        app.Twitch = TwitchParser()
        app.Twitch.application = app

        tornado.ioloop.IOLoop.instance().add_callback(app.Twitch.connect)  

    if options.twitter_setup:
        import keys
        from twython import Twython

        twitter = Twython(keys.twitter_appkey, keys.twitter_appsecret)

        auth = twitter.get_authentication_tokens()
        #Grab intermediate tokens. These are not the final tokens
        ioauth_token = auth['oauth_token']
        ioauth_token_secret = auth['oauth_token_secret']


        print("\nPlease go to the following link to authorize Twitter account access, then record the authorization PIN:\n")
        print(auth['auth_url'])
        
        pin = input("\nEnter the PIN then press `Enter`: ")
        twitter = Twython(keys.twitter_appkey,
                          keys.twitter_appsecret,
                          ioauth_token,
                          ioauth_token_secret)

        final_auth = twitter.get_authorized_tokens(pin)

        oauth_token = final_auth['oauth_token']
        oauth_token_secret = final_auth['oauth_token_secret']

        print("token: {}\n token secret: {}".format(oauth_token, oauth_token_secret))

        return  # remove this eventually

    if options.twitter:
        from networks.twatter import Twitter
        app.Twitter = Twitter(app)

        tornado.ioloop.IOLoop.instance().add_callback(app.Twitter.connect)

    # link the Jukebox to the application
    from commands.jukebox import J  # our instance of the Jukebox
    app.Jukebox = J  # on our instance of the Application
    
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
