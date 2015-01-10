""" Custom exceptions for x/84. """
# local imports
from x84.bbs.session import Script


class Disconnected(Exception):

    """ Thrown when a client is disconnected. """

    pass


class Goto(Exception):

    """ Thrown to change script without returning. """

    def __init__(self, script, *args, **kwargs):
        # re-define the same Script namedtuple from x84.bbs.session.
        # just a simple hack to avoid any kind of circular imports.
        self.value = Script(name=script, args=args, kwargs=kwargs)


class ScriptError(Exception):

    """ Thrown for internal scripting errors. """

    pass
