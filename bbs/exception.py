"""
Custom exception classes for x/84 BBS https://github.com/jquast/x84
"""

class Disconnect(Exception):
    """Raise this error to cause the socket to be disconnected."""
    pass


class ConnectionClosed (Exception):
    """This exception thrown when client closes connection."""
    pass


class ConnectionTimeout (Exception):
    """Raised this error to indicate idle time exceeded."""
    pass


class Goto (Exception):
    """Raised whenever a script wants to travel&exchange itself to another."""
    pass


class ScriptError (Exception):
    """This exception thrown when runscript fails to locate script."""
    pass
