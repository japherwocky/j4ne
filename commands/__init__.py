Commands = {}


def command(name):
    """
    Decorator for registering commands
    """

    def __decorator(func):
        Commands[name] = func
        return func

    return __decorator
