Discord_commands = {}


def discord_command(name):
    """
    Decorator for registering commands
    """

    def __decorator(func):
        Discord_commands[name] = func
        return func

    return __decorator


Twitch_commands = {}

def twitch_command(name):
    def __decorator(func):
        Twitch_commands[name] = func
        return func

    return __decorator

