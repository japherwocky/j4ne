from ircbot import SingleServerIRCBot

last_propaganda = False

def invited(ServerConnection, Event): #both are irclib. instances
   """
   Event.arguments() == ['#hello']
   """
   for arg in Event.arguments(): #(there's only one though)
      ServerConnection.join( arg)

import time
def chatparse(ServerConnection, Event):
	#print dir(Event)
	#print Event.arguments()
	#print Event.source() # nick!~user@domain
	#print Event.target() # #channel

	if 'suck' in Event.arguments()[0]:
		time.sleep(.5)
		ServerConnection.privmsg( Event.target(), propagandize())

	#ServerConnection.privmsg(Event.target(), 'haaayyy, you said %s'%Event.arguments())

import feedparser
from random import randint
def propagandize():
	global last_propaganda
	d = feedparser.parse('http://feeds2.feedburner.com/fmylife')
	#i = randint( 0, len(d.entries))
	last_propaganda = d.entries[randint( 0, len(d.entries)-1)]
	return strip_tags( last_propaganda.description).replace( 'FML', '')

def strip_tags(value):
	import re
	"Return the given HTML with all tags stripped."
	return re.sub(r'<[^>]*?>', '', value)


Eeyore = SingleServerIRCBot([('pearachute.net', 6668)], 'Eeyore', 'I AM A ROBOT')
Eeyore.connection.add_global_handler('invite', invited, -10)
Eeyore.connection.add_global_handler('pubmsg', chatparse, -10)
#join/part/privmsg/pubmsg/privnotice/pubnotice
Eeyore.start()

