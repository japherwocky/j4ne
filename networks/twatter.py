from twython import Twython,TwythonStreamer
from keys import twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret
from logging import debug, info

twitter = Twython(twitter_appkey, twitter_appsecret, twitter_token, twitter_tokensecret)
twitter.verify_credentials()


