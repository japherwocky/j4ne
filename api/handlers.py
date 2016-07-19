import datetime
import tornado.web
import json
from loggers.models import Message, Event
from commands.models import Quote
from playhouse.shortcuts import model_to_dict

from tornado.web import HTTPError


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if getattr(obj, 'isoformat'):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")


class APIHandler(tornado.web.RequestHandler):

    # straight model lookups
    models = {
        'events': Event,
        'messages': Message,
        'quotes': Quote
    }

    def get(self, model, id=None):

        # things like channels which don't necessarily have a model (though maybe they should)
        methods = {
            'channels': self.channels,
        }

        if model in self.models:
            if id:
                Q = self.get_one(model, id)

            else:
                Q = self.query(model)

        elif model in methods:
            return methods[model]()

        else:
            raise HTTPError(404)

        out = [model_to_dict(row) for row in Q]

        # can't return lists, see http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write
        out = {
                'count':len(out), 
                'data':out,
            }

        if out['count'] > 0:
            out['oldest'] = out['data'][-1]['timestamp']
            out['newest'] = out['data'][0]['timestamp']

        out = json.dumps(out, default=json_serial)

        self.set_header('Content-Type', 'application/json')
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

            if not ('before' in self.request.query_arguments or 'after' in self.request.query_arguments):

                Q = self.models[model] \
                    .filter(**self.request.query_arguments) \
                    .order_by(self.models[model].timestamp.desc()) \
                    .limit(5000)

            else:
                times = {}
                for query in ('before', 'after'):
                    if query in self.request.query_arguments:
                        times[query] = self.request.query_arguments[query][0].decode('utf-8').strip('Z').replace('T', ' ')
                        del self.request.query_arguments[query]

                Q = self.models[model] \
                    .filter(**self.request.query_arguments) \
                    .order_by(self.models[model].timestamp.desc()) \
                    .limit(500)

                if 'before' in times:
                    Q = Q.filter(self.models[model].timestamp < times['before'])

                if 'after' in times:
                    Q = Q.filter(self.models[model].timestamp > times['after'])

        else:
            Q = self.models[model]

        return Q

    def channels(self):

        message_chans = [m.channel for m in Message.select(Message.channel).where(Message.network=='twitch').distinct()]
        event_chans = [e.channel for e in Event.select(Event.channel).where(Event.network=='twitch').distinct()]

        chans = [channel for channel in set(message_chans).union( set(event_chans))]

        out = {'data':chans}
        self.set_header('Content-Type', 'application/json')
        return self.finish(out) 

