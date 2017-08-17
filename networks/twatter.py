import json
import tornado.ioloop
import asyncio
import html

from twython import Twython,TwythonStreamer
from keys import twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret
from logging import debug, info, warning

from networks.models import DiscordChannel, Tooter, Retweets


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

        verify = self._twitter.verify_credentials()

        # schedule polling for tweeters
        # TODO, not like this, see j4ne.py for scheduling callbacks w/ tornado
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
        debug('checking tweets')

        tooters = Retweets.select().distinct(Retweets.tooter)

        if not tooters.exists():
            info('No Tooters exist in the database yet')
            return

        for tooter in tooters:
            tweets = self._twitter.get_user_timeline(screen_name=tooter.tooter)
            tweets.reverse()

            last_tweet = tooter.last_tweet_id

            for tweet in tweets:
                if last_tweet == 0:
                    last_tweet = tweets[-2]['id']

                if tweet['id'] <= last_tweet:
                    continue

                if tweet['in_reply_to_status_id']:
                    # don't show tweets that are replies to other users
                    continue

                info('new tweet from {}'.format(tweet['user']['screen_name']))

                tweet = await self.parse(tweet)

                # kind of sloppy, but find any/all channels we're supposed to post this in
                channels = Retweets.select().where(Retweets.tooter == tooter.tooter)

                for channel in channels:

                    destination = (self.application.Discord.client.get_channel(channel.discord_channel))

                    # save last posted .. better if we did this after it works so we don't lose toots
                    channel.last_tweet_id = tweet['id']
                    channel.save()

                    if 'retweeted_status' in tweet:
                        user = tweet['retweeted_status']['user']['screen_name']
                        tweet_id = tweet['retweeted_status']['id']
                        retweet_link = ('https://twitter.com/{}/status/{}'
                                        .format(user, tweet_id))

                        # skip self retweets for tiny
                        if user.lower() == channel.tooter.lower():
                            continue

                        if not tweet['is_quote_status']:
                            await self.application.Discord.say(destination, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                            continue

                        await self.application.Discord.say(destination, '{} retweets:\n\n{}'.format(tweet['user']['screen_name'], retweet_link))
                        continue

                    await self.application.Discord.say(destination, '{} tweets:\n\n{}\n\n'.format(tweet['user']['screen_name'], tweet['text']))


from commands import discord_command

@discord_command('retweet')
async def retweet(network, channel, message):

    tooter = message.content.split('|retweet')[1]
    if not tooter:
        return await network.say(message.channel, 'Who should I retweet?')

    tooter = tooter.strip()

    existing = Retweets().select().where(Retweets.tooter==tooter, Retweets.discord_channel==channel.id)

    if len(existing) > 0:
        return await network.say(message.channel, 'I am already retweeting {} here.'.format(tooter))

    new_retweet = Retweets.insert(tooter=tooter, discord_channel=channel.id).execute()

    await network.say(message.channel, "I will start retweeting {} in this channel.".format(tooter))

