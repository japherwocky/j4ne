import tornado.web
from loggers.models import Message, Event
from commands.models import Quote
from playhouse.shortcuts import model_to_dict

from tornado.web import HTTPError

class APIHandler(tornado.web.RequestHandler):

    models = {
        'events': Event,
        'messages': Message,
        'quotes': Quote
    }

    def get(self, model, id=None):

        if model not in self.models:
            raise HTTPError(404)

        if id:
            Q = self.get_one(model, id)

        else:
            Q = self.query(model)

        out = [model_to_dict(row) for row in Q]

        # can't return lists, see http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write
        out = {'count':len(out), 'data':out}
        return self.finish(out) 


    def get_one(self, model, id):
        Q = self.models[model].filter(id=id)

        if Q.count() == 0:
            raise HTTPError(404)

        return Q

    def query(self, model):

        if self.request.query_arguments:
            # prepend channels with a #
            if 'channel' in self.request.query_arguments:
                channs = ['#{}'.format(chann.decode('utf-8')) for chann in self.request.query_arguments['channel']]
                self.request.query_arguments['channel'] = channs

            Q = self.models[model].filter(**self.request.query_arguments)
        else:
            Q = self.models[model]

        return Q


