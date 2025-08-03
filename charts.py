import tornado.web

class ChartHandler(tornado.web.RequestHandler):
    """
    Chart handler for data visualizations
    """

    def get(self):
        self.render('charts.html')
