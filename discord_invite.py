
# enabled permissions for discord bot
perms = [
    '0x0000400',  # READ_MESSAGES
    '0x0000800',  # SEND_MESSAGES
    '0x0002000',  # DELETE_MESSAGES
    '0x0008000',  # ATTACH_FILES
    '0x0004000',  # EMBED_LINKS ?
    '0x0100000',  # CONNECT (to voice)
    '0x0200000',  # SPEAK
    '0x2000000',  # DETECT VOICE
]


perm_int = sum([int(perm, 0) for perm in perms])

# Given the bot clientid, returns a link for authorizing the bot on your server
def invite_link(discord_clientid):
    link = 'https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions={}'.format(discord_clientid, perm_int)
    return link
