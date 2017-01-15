import json
import tornado.ioloop
import asyncio
import html

from twython import Twython,TwythonStreamer
from keys import twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret
from logging import debug, info, warning

from networks.models import DiscordChannel, Tooter

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

    async def connect(self):

        # kick off a periodic task for our ghetto ass Twitter polling
        self._twitter = Twython(
            twitter_appkey,
            twitter_appsecret,
            twitter_token,
            twitter_tokensecret
            )

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
        info('Checking Tweets')

        tooters = Tooter.select()

        if not tooters.exists():
            info('No Tooters exist in the database yet')
            return

        for tooter in tooters:
            tweets = self._twitter.get_user_timeline(screen_name = tooter.screen_name)
            tweets.reverse()

            last_tweet = tooter.last_tweet_id

            for tweet in tweets:
                if last_tweet == 0:
                    last_tweet = tweets[-2]['id']

                if tweet['id'] <= last_tweet:
                    continue

                info('new tweet from {}'.format(tweet['user']['screen_name']))
                tooter.last_tweet_id = tweet['id']
                tooter.save()

                if tweet['in_reply_to_status_id']:
                    # don't show tweets that are replies to other users
                    continue

                tweet = await self.parse(tweet)

                for channel in tooter.channels:

                    destination = (self.application.Discord.client
                                   .get_channel(channel.discord_id))

                    if 'retweeted_status' in tweet:
                        user = tweet['retweeted_status']['user']['screen_name']
                        tweet_id = tweet['retweeted_status']['id']
                        retweet_link = ('https://twitter.com/{}/status/{}'
                                        .format(user, tweet_id))

                        if not tweet['is_quote_status']:
                            await self.application.Discord.say(destination, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                            continue

                        await self.application.Discord.say(destination, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                        continue

                    await self.application.Discord.say(destination, '{} tweets:\n\n{}\n\n'.format(tweet['user']['screen_name'], tweet['text']))
