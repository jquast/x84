"""
Custom exception classes for x/84, https://github.com/jquast/x84
"""


class Disconnected(Exception):
    """Thrown when socket was disconnected"""
    pass


class Disconnect(Exception):
    """Throw to cause the socket to be disconnected."""
    pass


class ConnectionClosed (Exception):
    """Thrown when client closes connection."""
    pass


class ConnectionTimeout (Exception):
    """Thrown to indicate idle time exceeded."""
    pass


class Goto (Exception):
    """Thrown when a script wants exec() another script"""
    pass


class ScriptError (Exception):
    """Thrown when runscript fails to locate script."""
    pass
