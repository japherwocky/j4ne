import json
import tornado.ioloop
import asyncio
import html

from twython import Twython,TwythonStreamer
from keys import twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret
from logging import debug, info, warning

# twitter = Twython(twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret)
# twitter.verify_credentials()


# We need to wrap connect() as a task to prevent timeout error at runtime.
# based on the following suggested fix: https://github.com/KeepSafe/aiohttp/issues/1176
def taskify(func):
    async def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().create_task(func(*args, **kwargs))
    return wrapper

from networks import Network
class Twitter(Network):
    """
    Common interface for connecting and receiving realtimey events
    """

    _twitter_conf = None  

    async def connect(self):

        self._twitter = Twython(
            twitter_appkey, 
            twitter_appsecret, 
            twitter_token, 
            twitter_tokensecret
            )

        # kick off a periodic task for our ghetto ass Twitter polling
        self._twitter = Twython(twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret)
        self._twitter.verify_credentials()

        # schedule polling for tweeters
        tornado.ioloop.PeriodicCallback( self.check_tweets , 1*60*1000).start()
        info('Twitter connected')


    async def disconnect(self):
        pass

    async def reconnect(self):
        self.disconnect()
        self.connect()

    async def on_message(self, msg):
        #handle logging
    
        # classify & normalize
        self.parse(msg)  

        # archive
        self.log(msg)  

        # trigger any tasks
        self.process(msg)


    async def parse(self, tweet):
        
        tweet['text'] = html.unescape(tweet['text'])

        return tweet


    async def log(self, msg):
        pass


    async def process(self, msg):
        pass


    @taskify
    async def check_tweets(self):
        """ Parse our stupid homebrew conf file """

        if not self._twitter_conf:
            warning('_twitter_conf not (yet?) loaded!')

            return

        for serv in self._twitter_conf.keys():
            debug(serv)

            for chann in self._twitter_conf[serv].keys():
                debug(chann)

                for tooter in self._twitter_conf[serv][chann]:

                    tweets = self._twitter.get_user_timeline(screen_name = tooter['screen_name'])
                    tweets.reverse()

                    # this will be the first tweet in the channel
                    if tooter['last'] == 1:
                        tweets = [tweets[-1],]


                    for tweet in tweets:
                        if tooter['last'] > 1 and tweet['id'] <= tooter['last']:
                            continue

                        info('new tweet from {}'.format(tweet['user']['screen_name']))

                        tooter['last'] = tweet['id']

                        if tweet['in_reply_to_status_id']:
                            # don't show tweets that are replies to other users
                            continue

                        tweet = await self.parse(tweet)

                        if 'retweeted_status' in tweet:
                            user = tweet['retweeted_status']['user']['screen_name']
                            tweet_id = tweet['retweeted_status']['id']
                            retweet_link = 'https://twitter.com/{}/status/{}'.format(user, tweet_id)

                            if not tweet['is_quote_status']:
                                await self.application.Discord.say(chann, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                                continue

                            else:
                                await self.application.Discord.say(chann, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                                continue

                        await self.application.Discord.say(chann, '{} tweets:\n\n{}\n\n'.format(tweet['user']['screen_name'], tweet['text']))

                    self.save_twitter_config()

        
    def setup_retweets(self):

        # this is all moot if we're not connected to Discord
        if not getattr(self.application, 'Discord'):
            warning('No discord connection, not retweeting')

            return

        # look up where we're supposed to be retweeting to
        with open('./twitterconf.json') as f:
            conf = json.loads(f.read())

            # replace server strings with proper objects
            servers = {server.name:server for server in self.application.Discord.client.servers}
            for servstring in [k for k in conf.keys()]:
                debug('Loading server {}'.format(servstring))

                if servstring in servers:

                    servobj = servers[servstring]
                    conf[servobj] = conf[servstring]
                    del conf[servstring]

                    for chanstring in [k for k in conf[servobj].keys()]:
                        channels = {channel.name:channel for channel in servers[servstring].channels}
                        chanobj = channels[chanstring]
                        conf[servobj][chanobj] = conf[servobj][chanstring]
                        del conf[servobj][chanstring]

            self._twitter_conf = conf

        info('Twitter conf loaded')


    def save_twitter_config(self):

        out = {}
        servers = {server.name:server for server in self.application.Discord.client.servers}

        for serv in self._twitter_conf.keys():
            out[serv.name] = {}
       
            for chann in self._twitter_conf[serv].keys():
                out[serv.name][chann.name] = []

                for tooter in self._twitter_conf[serv][chann]:
                    out[serv.name][chann.name].append(tooter)
                 
        with open('./twitterconf.json', 'w') as f:
            out = json.dumps(out, sort_keys=True, indent=4)

            f.write(out)





