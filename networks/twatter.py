import json
import tornado.ioloop
import asyncio
import html
import os
from dotenv import load_dotenv

from commands import discord_command

from twython import Twython
from logging import debug, info, warning

# Load environment variables
load_dotenv()

# Get Twitter API credentials from environment
twitter_appkey = os.getenv('TWITTER_APPKEY', '')
twitter_appsecret = os.getenv('TWITTER_APPSECRET', '')
twitter_token = os.getenv('TWITTER_TOKEN', '')
twitter_tokensecret = os.getenv('TWITTER_TOKENSECRET', '')

from networks.models import Retweets
from networks import Network
from networks.models import Channels, Servers

from loggers.models import Event

class Twitter(Network):
    """ subclass to handle connecting to the Twitter API """

    def __init__(self, j4ne):
        super().__init__(j4ne)
        self.twitter = Twython(twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret)
        self.twitter_conf = {}
        self.twitter_stream = None
        self.twitter_task = None

    async def connect(self):
        """ Connect to the Twitter API """
        # Load the Twitter configuration
        try:
            with open('twitter.json', 'r') as f:
                self.twitter_conf = json.load(f)
        except FileNotFoundError:
            self.twitter_conf = {}

        # Start the Twitter stream
        self.twitter_task = asyncio.create_task(self.twitter_loop())

    async def twitter_loop(self):
        """ Loop to check for new tweets """
        while True:
            try:
                # Check for new tweets from accounts we're following
                for servstring in [k for k in self.twitter_conf.keys()]:
                    try:
                        servobj = Servers.get(Servers.name == servstring)
                    except Servers.DoesNotExist:
                        warning("Server {} not found".format(servstring))
                        continue

                    for chanstring in [k for k in self.twitter_conf[servobj.name].keys()]:
                        try:
                            chanobj = Channels.get(Channels.name == chanstring, Channels.server == servobj)
                        except Channels.DoesNotExist:
                            warning("Channel {} not found".format(chanstring))
                            continue

                        for retweet in self.twitter_conf[servobj.name][chanobj.name]:
                            try:
                                # Get the latest tweets from this user
                                tweets = self.twitter.get_user_timeline(screen_name=retweet['screen_name'], count=5, include_rts=True)
                                
                                # Get the latest tweet ID we've seen
                                try:
                                    rt = Retweets.get(Retweets.tooter == retweet['screen_name'], Retweets.discord_channel == chanobj.id)
                                    last_id = rt.last_tweet_id
                                except Retweets.DoesNotExist:
                                    last_id = retweet['last']

                                # Check if there are new tweets
                                new_tweets = []
                                for tweet in tweets:
                                    if str(tweet['id']) > last_id:
                                        new_tweets.append(tweet)

                                # If there are new tweets, send them to the channel
                                if new_tweets:
                                    # Sort by ID (oldest first)
                                    new_tweets.sort(key=lambda x: x['id'])
                                    
                                    # Update the last tweet ID
                                    try:
                                        rt = Retweets.get(Retweets.tooter == retweet['screen_name'], Retweets.discord_channel == chanobj.id)
                                        rt.last_tweet_id = str(new_tweets[-1]['id'])
                                        rt.save()
                                    except Retweets.DoesNotExist:
                                        rt = Retweets.create(tooter=retweet['screen_name'], discord_channel=chanobj.id, last_tweet_id=str(new_tweets[-1]['id']))

                                    # Send the tweets to the channel
                                    for tweet in new_tweets:
                                        # Format the tweet
                                        text = html.unescape(tweet['text'])
                                        url = "https://twitter.com/{}/status/{}".format(tweet['user']['screen_name'], tweet['id'])
                                        message = "**@{}**: {} {}".format(tweet['user']['screen_name'], text, url)
                                        
                                        # Send the message to the channel
                                        discord_channel = self.j4ne.networks['DeescordNetwork'].client.get_channel(chanobj.snowflake)
                                        if discord_channel:
                                            await self.j4ne.networks['DeescordNetwork'].send_message(discord_channel, message)
                                        else:
                                            warning("Channel {} not found".format(chanobj.snowflake))

                            except Exception as e:
                                warning("Error getting tweets for {}: {}".format(retweet['screen_name'], e))
                                continue

            except Exception as e:
                warning("Error in Twitter loop: {}".format(e))

            # Wait before checking again
            await asyncio.sleep(60)

@discord_command('twitter')
async def load_twitter_config(network, channel, message):
    """ Load the Twitter configuration """
    try:
        with open('twitter.json', 'r') as f:
            conf = json.load(f)
    except FileNotFoundError:
        conf = {}

    # Get the server and channel
    server = message.guild.name
    chan = message.channel.name

    # Get the command arguments
    args = message.content.split(' ')
    if len(args) < 3:
        await network.send_message(channel, "Usage: !twitter add|remove <screen_name>")
        return

    # Add or remove a Twitter account
    if args[1] == 'add':
        screen_name = args[2]
        
        # Add the server if it doesn't exist
        if server not in conf:
            conf[server] = {}
        
        # Add the channel if it doesn't exist
        if chan not in conf[server]:
            conf[server][chan] = []
        
        # Check if we're already following this account
        for rt in conf[server][chan]:
            if rt['screen_name'] == screen_name:
                await network.send_message(channel, "Already following @{}".format(screen_name))
                return
        
        # Add the account
        conf[server][chan].append({
            'screen_name': screen_name,
            'last': '0'
        })
        
        # Save the configuration
        with open('twitter.json', 'w') as f:
            json.dump(conf, f)
        
        # Update the network's configuration
        network.j4ne.networks['Twitter'].twitter_conf = conf
        
        # Add to the database
        try:
            servobj = Servers.get(Servers.name == server)
            chanobj = Channels.get(Channels.name == chan, Channels.server == servobj)
            
            try:
                rt = Retweets.get(Retweets.tooter == screen_name, Retweets.discord_channel == chanobj.id)
                rt.last_tweet_id = '0'
                rt.save()
            except Retweets.DoesNotExist:
                new_retweet = Retweets.insert(tooter=screen_name, discord_channel=chanobj.id, last_tweet_id='0').execute()
        
        except Exception as e:
            warning("Error adding Twitter account to database: {}".format(e))
        
        await network.send_message(channel, "Now following @{}".format(screen_name))
    
    elif args[1] == 'remove':
        screen_name = args[2]
        
        # Check if we're following this account
        if server in conf and chan in conf[server]:
            for i, rt in enumerate(conf[server][chan]):
                if rt['screen_name'] == screen_name:
                    # Remove the account
                    del conf[server][chan][i]
                    
                    # Save the configuration
                    with open('twitter.json', 'w') as f:
                        json.dump(conf, f)
                    
                    # Update the network's configuration
                    network.j4ne.networks['Twitter'].twitter_conf = conf
                    
                    # Remove from the database
                    try:
                        servobj = Servers.get(Servers.name == server)
                        chanobj = Channels.get(Channels.name == chan, Channels.server == servobj)
                        
                        try:
                            rt = Retweets.get(Retweets.tooter == screen_name, Retweets.discord_channel == chanobj.id)
                            rt.delete_instance()
                        except Retweets.DoesNotExist:
                            pass
                    
                    except Exception as e:
                        warning("Error removing Twitter account from database: {}".format(e))
                    
                    await network.send_message(channel, "No longer following @{}".format(screen_name))
                    return
        
        await network.send_message(channel, "Not following @{}".format(screen_name))
    
    else:
        await network.send_message(channel, "Usage: !twitter add|remove <screen_name>")

