""" Module provides ``Script`` definition for x/84. """
# std imports
import collections

#: Defines a target script name, positional, and keyword arguments.
Script = collections.namedtuple('Script', ['name', 'args', 'kwargs'])
