""" Custom exceptions for x/84. """

# local imports
from x84.bbs.script_def import Script


class Disconnected(Exception):

    """ Thrown when a client is disconnected. """

    pass


class Goto(Exception):

    """ Thrown to change script without returning. """

    def __init__(self, script, *args, **kwargs):
        self.value = Script(name=script, args=args, kwargs=kwargs)
