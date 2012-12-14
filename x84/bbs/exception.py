"""
Custom exception classes for x/84, https://github.com/jquast/x84
"""


class Disconnected(Exception):
    """Thrown when a client is disconnected."""
    pass


class Goto (Exception):
    """Thrown to change script without returning."""
    pass


class ScriptError (Exception):
    """Thrown for internal scripting errors."""
    pass
