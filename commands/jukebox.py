from commands import command
from random import shuffle
from array import array
from logging import info, debug, error
import discord
import tornado

from youtube_dl.utils import DownloadError
from websockets.exceptions import InvalidState

class VolumeBuff(object):
    """
        Kind of a volume aware buffer mixin.
    """

    def __init__(self, player, buff):
        self.player = player
        self.buff = buff
        self.frame_count = 0

    def read(self, frame_size):
        self.frame_count += 1
        frame = self.buff.read(frame_size)

        volume = self.player.volume
        # Only make volume go down. Never up.
        if volume < 1.0:
            # Ffmpeg returns s16le pcm frames.
            frame_array = array('h', frame)

            for i in range(len(frame_array)):
                frame_array[i] = int(frame_array[i] * volume)

            frame = frame_array.tobytes()

        return frame


class Jukebox:
    """ music playing commands """

    voice = None
    voicechan = None
    player = None

    keep_playing = True

    _volume = 69  # store this as 1-100
    playlist = []  # seeded with __init__
    requests = []

    client = None  # used to set playing status

    def __init__(self):
        with open('playlist.txt') as f:
            self.playlist = f.readlines()
            shuffle(self.playlist)

J = Jukebox()  # completely unenforced singleton


async def say(client, channel, message, destroy=0):
    """ kind of silly helper method"""
    msg = await client.send_message(channel, message)

    if destroy:
        await asyncio.sleep(destroy)
        await client.delete_message(msg)


@command('summon')
async def summon(client, message):
    ''' Try to join the author's voice channel '''
    authorchan = message.author.voice_channel

    if not authorchan:
        return await say(client, message.channel, 'You must join a voice channel first, {}'.format(message.author.name))

    # check if this is new or we're moving
    if client.is_voice_connected(message.server):

        # already connected somewhere - here?
        if authorchan == J.voicechan:
            return await say(client, message.channel, 'I am already in your channel, {}'.format(message.author.name))

        # or leave so we can join the new channel
        else:
            await J.voice.disconnect()

    # join the author's voice channel
    J.voicechan = authorchan
    J.voice = await client.join_voice_channel(authorchan)


@command('banish')
async def banish(client, message):
    ''' Clear out any pre-existing voice connections '''
    if client.is_voice_connected(message.server):
        await J.voice.disconnect()

    J.voicechan = J.voice = None


@command('request')
async def request(client, message):
    req = message.content.split('|request ')[1]

    # they didn't manage to request a song
    if not req:
        await say(client, message.channel, "What would you like to request, {}?".format(message.author.name))
        return

    if not J.voice:
        await say(client, message.channel, "I am not in a voice channel, {}".format(message.author.name))
        return

    # let's see if it works
    try:
        player = await J.voice.create_ytdl_player(req, options='-bufsize 520k', after=on_end)
        player._url = req
    except DownloadError as exc:
        await say(client, message.channel, "I could not find that, {}".format(message.author.name))

    await say(client, message.channel, '{} has been added to the queue.'.format(player.title))

    J.requests.append(player)


@command('play')
async def play(client, message):

    if not (J.voice and J.voicechan):
        await say(client, message.channel, 'I am not in a voice channel, {}'.format(message.author.name))
        return

    # check if we are already playing something
    if J.player and J.player.is_playing():
        await say(client, message.channel, 'I am already playing, {}'.format(message.author.name))
        return

    J.keep_playing = True

    J.playchan = message.channel  # reset the channel we want to talk in
    J.client = client
    await playsong()


@command('song')
async def song(client, message):
    if not (J.player and J.player.is_playing()):
        return await say(client, message.channel, 'I am not playing right now.')

    await say(client, message.channel, 'Now playing **{}**'.format(J.player.title))


@command('stop')
async def stop(client=None, message=None):  # defaults, sometimes we call this directly

    # set this before calling .stop(), the end callback will check for it
    J.keep_playing = False

    if J.player:
        J.player.stop()
        J.player = None

    await J.client.change_status(None)  # set our "playing" status to nothing
    J.client = None

    if message:
        await say(client, message.channel, ':hammer: time')


@command('skip')
async def skip(client, message):
    """ Skip whatever is playing right now - TODO, votes? """

    if J.player:
        J.player.stop()


@command('volume')
async def volume(client, message):
    """ Set the volume """

    txt = message.content.strip('|volume')

    if txt:
        try:
            vol = int(txt)
        except ValueError:
            return await say(client, message.channel, 'Please try a number between 1 and 100, {}'.format(message.author.name))

        J._volume = vol

    if J.player:
        J.player.volume = J._volume / 100.0

    return await say(client, message.channel, 'The volume is set at {}'.format(J._volume))


@command('queue')
async def queue(client, message):

    if not J.requests:
        await say(client, message.channel, 'There are no requests right now, {}'.format(message.author.name))

    else:
        await say(client, message.channel, 'There are {} requests, next up is {}'.format(len(J.requests), J.requests[0].title))


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
        player = await J.voice.create_ytdl_player(player._url, options='-bufsize 520k', after=on_end)

    return player


async def playsong():
    """
    Attempt to play whatever song comes next!
    """

    try:
        player = await nextsong()

        # instantiate player, hack in volume controls
        player.buff = VolumeBuff(player, player.buff)  # so awkward
        player.volume = J._volume / 100.0  # not to be confused with the command

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
