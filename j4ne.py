import os
import asyncio
join = os.path.join
exists = os.path.exists
import feedparser
from random import choice
from logging import info, debug
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.platform.asyncio
from tornado.web import HTTPError, authenticated
from markdown import markdown
from networks.irc import IRC
from networks.deescord import Discord
from networks.twitch import TwitchParser




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
            (r"/login/?", LoginHandler),
            (r"/logout/?", LogoutHandler),
            (r"(?!\/static.*)(.*)/?", DocHandler),
        ]

        tornado.web.Application.__init__(self, handlers, **settings)


class AuthMixin(object):
    def get_current_user(self):
        return self.get_secure_cookie("user")

    @property
    def user(self):
        return self.get_current_user()


class MainHandler(AuthMixin, tornado.web.RequestHandler):

    @authenticated
    def get(self):

        txt = open('docs/hello.txt').read()
        doc = markdown(txt)
        self.render('index.html', doc=doc)


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

        """
        self.application.botname = str(username)
        self.application.twitchtoken = str(token)
        self.application.connect_irc('irc.twitch.tv', 6667)

        self.set_secure_cookie('user', self.application.botname)

        self.redirect('/')
        """


class LogoutHandler(tornado.web.RequestHandler):
    def get(self):
        """ this is slightly weird, because we'll log the user out of this app
        but _not_ out of twitch.  If they (or anyone) hits a route with
        with @authenticated, and they're still signed into twitch, it will
        auto sign them back in.  yolo.
        """
        self.clear_cookie('user')

        self.finish('o/')


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
    define("port", default=8888, help="serve web requests from the given port", type=int)
    define("debug", default=False, help="run server in debug mode", type=bool)
    define("botname", default='Test Bot', help="name of the bot")
    define("mktables", default=False, help="bootstrap a new sqlite database")

    tornado.options.parse_command_line()

    if options.mktables:
        from loggers.models import db, Message
        db.create_tables([Message,])


    app = App(options.botname, app_debug=options.debug)

    http_server = tornado.httpserver.HTTPServer(app)
    tornado.platform.asyncio.AsyncIOMainLoop().install()  # uses default asyncio.loop()

    http_server.listen(options.port)
    info('Serving on port %d' % options.port)

    # connect to discord 
    app.Discord = Discord()
    tornado.ioloop.IOLoop.instance().add_callback(app.Discord.connect)  

    # connect to Twitch ... to mixin or not to mixin
    app.Twitch = TwitchParser()
    tornado.ioloop.IOLoop.instance().add_callback(app.Twitch.connect)  

    # connect to IRC
    
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
