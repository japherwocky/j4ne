import tornado.web

class ChartHandler(tornado.web.RequestHandler):
    """
    super awkward naming now, basically a util to auth with twitch
    and spit the oauth token out to stdout
    """

    def get(self):
        self.render('charts.html')

