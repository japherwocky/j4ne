from commands import discord_command as command
from random import shuffle
from array import array
from collections import deque
from logging import info, debug, error
import asyncio
import audioop
import discord
import tornado

import youtube_dl as ytdl
from youtube_dl.utils import DownloadError
from websockets.exceptions import InvalidState

from concurrent.futures import ProcessPoolExecutor
from functools import partial


class Jukebox:
    """ music playing commands """

    voice = None
    voicechan = None
    player = None

    keep_playing = True

    _volume = 53  # store this as 1-100
    playlist = []  # seeded with __init__
    requests = []

    client = None  # used to set playing status

    def __init__(self):
        with open('playlist.txt') as f:
            self.playlist = f.readlines()
            shuffle(self.playlist)

        self.executor = ProcessPoolExecutor(max_workers=2)
        self.loop = asyncio.get_event_loop()


Jukebox = J = Jukebox()  # completely unenforced singleton


class FancyVolumeBuff(object):
    """
        PatchedBuff monkey patches a readable object, allowing you to vary what the volume is as the song is playing.
    """

    def __init__(self, buff, *, draw=False):
        self.buff = buff
        self.frame_count = 0
        self.volume = 1.0

        self.draw = draw
        self.use_audioop = True
        self.frame_skip = 2
        self.rmss = deque([2048], maxlen=90)

    def __del__(self):
        if self.draw:
            print(' ' * (get_terminal_size().columns-1), end='\r')

    def read(self, frame_size):
        self.frame_count += 1

        frame = self.buff.read(frame_size)

        if self.volume != 1:
            frame = self._frame_vol(frame, self.volume, maxv=2)

        if self.draw and not self.frame_count % self.frame_skip:
            # these should be processed for every frame, but "overhead"
            rms = audioop.rms(frame, 2)
            self.rmss.append(rms)

            max_rms = sorted(self.rmss)[-1]
            meter_text = 'avg rms: {:.2f}, max rms: {:.2f} '.format(self._avg(self.rmss), max_rms)
            self._pprint_meter(rms / max(1, max_rms), text=meter_text, shift=True)

        return frame

    def _frame_vol(self, frame, mult, *, maxv=2, use_audioop=True):
        if use_audioop:
            return audioop.mul(frame, 2, min(mult, maxv))
        else:
            # ffmpeg returns s16le pcm frames.
            frame_array = array('h', frame)

            for i in range(len(frame_array)):
                frame_array[i] = int(frame_array[i] * min(mult, min(1, maxv)))

            return frame_array.tobytes()

    def _avg(self, i):
        return sum(i) / len(i)

    def _pprint_meter(self, perc, *, char='#', text='', shift=True):
        tx, ty = get_terminal_size()

        if shift:
            outstr = text + "{}".format(char * (int((tx - len(text)) * perc) - 1))
        else:
            outstr = text + "{}".format(char * (int(tx * perc) - 1))[len(text):]

        print(outstr.ljust(tx - 1), end='\r')

    @property
    def progress(self):
        # untested
        return round(buff.frame_count * 0.02)



async def say(client, channel, message, destroy=0):
    """ kind of silly helper method"""
    msg = await client.send_message(channel, message)

    if destroy:
        await asyncio.sleep(destroy)
        await client.delete_message(msg)


#@command('summon')
async def summon(network, channel, message):
    ''' Try to join the author's voice channel '''
    authorchan = message.author.voice_channel

    if not authorchan:
        return await network.send_message(channel, 'You must join a voice channel first, {}'.format(message.author.name))

    if J.voicechan:

        # already connected somewhere - here?
        if authorchan == J.voicechan:
            return await network.send_message(channel, 'I am already in your channel, {}'.format(message.author.name))

        # or leave so we can join the new channel
        elif J.voice:
            await J.voice.disconnect()
            J.voice = None

    # join the author's voice channel
    J.voicechan = authorchan
    J.voice = await network.client.join_voice_channel(authorchan)


#@command('banish')
async def banish(network, channel, message):
    ''' Clear out any pre-existing voice connections '''
    await stop()

    if network.client.is_voice_connected(message.server):
        await J.voice.disconnect()

    J.voicechan = J.voice = None


J.ytdl = ytdl.YoutubeDL(
    {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'default_search': 'auto',
}
)


#@command('request')
async def request(network, channel, message):
    req = message.content.split('|request')[1].strip()

    # they didn't manage to request a song
    if not req:
        await network.send_message(channel, "What would you like to request, {}?".format(message.author.name))
        return

    if not J.voice:
        await network.send_message(channel, "I am not in a voice channel, {}".format(message.author.name))
        return

    # let's see if it works
    try:

        meta = J.ytdl.extract_info(req, download=False, process=False) 

        if 'playlist' in meta['extractor']:
            # they've requested a playlist
            song_urls = [song['url'] for song in meta['entries']]
        else:
            song_urls = [meta['webpage_url'],]
            
        for song_url in song_urls:

            ytdlopts = {'default_search': 'auto'}
            player = await J.voice.create_ytdl_player(song_url, options='-bufsize 520k', ytdl_options=ytdlopts, after=on_end)
            player._query = song_url
            await network.send_message(channel, '{} has been added to the queue.'.format(player.title))
            J.requests.append(player)

    except DownloadError as exc:
        return await network.send_message(channel, "I could not download that, {}".format(message.author.name))



#@command('play')
async def play(network, channel, message):

    if not (J.voice and J.voicechan):
        await network.send_message(channel, 'I am not in a voice channel, {}'.format(message.author.name))
        return

    # check if we are already playing something
    if J.player and J.player.is_playing():
        await network.send_message(channel, 'I am already playing, {}'.format(message.author.name))
        return

    J.keep_playing = True

    J.playchan = message.channel  # reset the channel we want to talk in
    J.client = network.client
    await playsong()


#@command('song')
async def song(network, channel, message):
    if not (J.player and J.player.is_playing()):
        return await network.send_message(channel, 'I am not playing right now.')

    await network.send_message(channel, 'Now playing **{}**'.format(J.player.title))


#@command('stop')
async def stop(network=None, channel=None, message=None):  # defaults, sometimes we call this directly

    # set this before calling .stop(), the end callback will check for it
    J.keep_playing = False

    if J.player:
        J.player.stop()
        J.player = None

    if J.client:
        await J.client.change_status(None)  # set our "playing" status to nothing
    J.client = None

    if message:
        await network.send_message(channel, ':hammer: time')


#@command('skip')
async def skip(network, channel, message):
    """ Skip whatever is playing right now - TODO, votes? """

    if J.player:
        J.player.stop()


#@command('volume')
async def volume(network, channel, message):
    """ Set the volume """

    txt = message.content.strip('|volume')

    if txt:
        try:
            vol = int(txt)
        except ValueError:
            return await network.send_message(channel, 'Please try a number between 1 and 100, {}'.format(message.author.name))

        J._volume = vol

    if J.player:
        J.player.buff.volume = J._volume / 100.0

    return await network.send_message(channel, 'The volume is set at {}'.format(J._volume))


#@command('queue')
async def queue(network, channel, message):

    if not J.requests:
        await network.send_message(channel, 'There are no requests right now, {}'.format(message.author.name))

    else:
        await network.send_message(channel, 'There are {} requests, next up is {}'.format(len(J.requests), J.requests[0].title))


#@command('pause')
async def pause(network, channel, message):
    import time
    time.sleep(10)
    info('unblocking')


#@command('tangle')
async def tangle(network, channel, message):
    player = J.voice.create_ffmpeg_player(
                    'test.mp3',
                    before_options="-nostdin",
                    options="-vn -b:a 128k",
            )

    J.player = player
    player.start()
    

import livestreamer
from livestreamer.exceptions import NoPluginError
#@command('stream')
async def stream(network, channel, message):
    req = message.content.split('stream')[1].strip()


    if not req:
        return await network.send_message(channel, 'What stream did you want to listen to, {}?'.format(message.author.name))

    try:
        # this actually blocks.. for a while :|
        streams = livestreamer.streams('twitch.tv/{}'.format(req))
    except NoPluginError:
        # we should/could actually check that this is a twitch streamer in particular
        return await network.send_message(channel, 'I could not find a streamer named {}, {}'.format(req, message.author.name))
        
    audio_url = streams['audio'].url 

    # uhh.. yeah, fake a player object to work with the request system
    class Foo(object):
        pass

    fake_player = Foo()
    fake_player._query = audio_url

    J.requests.append(fake_player)
    return await network.send_message(channel, "{}'s stream has been added to the queue.".format(req, message.author.name))


# maybe put these on the Jukebox class
async def nextsong():
    """ 
    Queue up the next song, whether from a request or the stock playlist
    """
    player = False

    if not J.requests:
        while not player:
            url = J.playlist.pop()
            try:
                player = await J.voice.create_ytdl_player(url, options='-bufsize 520k', after=on_end)
                J.playlist.insert(0, url)  # put it back in the end of the list
            except DownloadError as exc:
                error('{} was invalid, discarding from list'.format(url))
                continue

    else:
        player = J.requests.pop(0)

        # re-init the player, we get TLS errors if it has been in the request list for too long
        ytdlopts = {'default_search': 'auto'}
        player = await J.voice.create_ytdl_player(player._query, options='-bufsize 520k', ytdl_options=ytdlopts, after=on_end)

    return player


async def playsong():
    """
    Attempt to play whatever song comes next!
    """

    try:
        player = await nextsong()

        # instantiate player, hack in volume controls
        player.buff = FancyVolumeBuff(player.buff)  # so awkward
        player.buff.volume = J._volume / 100.0  # not to be confused with the command

        J.player = player
        player.start()

        # update our status
        await J.client.change_status(discord.Game(name=player.title[:128]))

    except InvalidState:
        # eep, we got disconnected mid song
        await stop()


def on_end():
    if J.keep_playing:
        tornado.ioloop.IOLoop.instance().add_callback(lambda: playsong())


class WebPlayer(tornado.web.RequestHandler):
    """
    super awkward naming now, basically a util to auth with twitch
    and spit the oauth token out to stdout
    """

    def get(self):
        self.render('jukebox.html')

    def post(self):

        token = self.get_argument('token')
        username = self.get_argument('name')

        info('got token %s for user %s' % (token, username))
