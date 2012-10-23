"""
bbs module for X/84 BBS https://github.com/jquast/x84
everything in the bbs package is exported as a global to all bbs session
scripts. It is as if the statement:

    from bbs import *

Is implied for all session scripts.
"""
import bbs.ini as ini
from bbs.selector import Selector
from bbs.lightbar import Lightbar
from bbs.editor import LineEditor, ScrollingEditor
from bbs.input import getch

from bbs.exception import Disconnect, Goto, ConnectionTimeout
from bbs.cp437 import from_cp437
from bbs.door import Door
from bbs.dbproxy import DBProxy
from bbs.userbase import list_users, get_user, find_user, User, Group
from bbs.session import getsession, getterminal, logger
from bbs.scripting import abspath, fopen, ropen
from bbs.pager import Pager
from bbs.ansiwin import AnsiWindow
from bbs.output import echo, timeago, Ansi, chompn
# from bbs.input import getpos
import sauce
SAUCE = sauce.SAUCE

__all__ = [
    'Ansi',
    'LineEditor',
    'ScrollingEditor',
    'ConnectionTimeout',
    'Door',
    'from_cp437',
    'logger',
    'timeago',
    'DBProxy',
    'User',
    'Group',
    'list_users',
    'find_user',
    'get_user',
    'ini',
    'AnsiWindow',
    'Selector',
    'Lightbar',
    'Pager',
    'disconnect',
    'goto',
    'gosub',
    'sendevent',
    'broadcastevent',
    'readevent',
    'pollevent',
    'readevents',
    'flushevent',
    'flushevents',
    'getsession',
    'getterminal',
    'gethandle',
    'getch',
    'sleep',
    'echo',
    'abspath',
    'fopen',
    'ropen',
    'showcp437',
    'SAUCE',]


def gethandle():
    """
    Return user handle of this session.
    """
    return getsession().handle


def disconnect():
    """
    Disconnect the session
    """
    raise Disconnect('disconnect')


def goto(*args):
    """
    Switch to another bbs script, with arguments. Do not return.
    """
    raise Goto(args)


def gosub(*arg):
    """
    Switch to another bbs script, with arguments. Returns script return value.
    """
    #pylint: disable=W0142
    #        Used * or ** magic
    return getsession().runscript(*(arg[0],) + arg[1:])

def sendevent(pid, event, data):
    """
    Send an event to the main bbs engine.
    """
    return getsession().send_event('event', (pid, event, data))


def broadcastevent(event, data):
    """
    Broadcast an event to all other sessions.
    """
    return getsession().send_event('global', (getsession().pid, event, data))


def readevents(events=('input',), timeout=None):
    """
    Poll for first available Session event.
    """
    return getsession().read_events(events, timeout)

def readevent(event='input', timeout=None):
    """
    Poll for Session event. (blocking)
    """
    return getsession().read_event(event, timeout)

def pollevent(event='input'):
    """
    Poll for session event (non-blocking)
    """
    return getsession().read_event(event, -1)

def sleep (seconds):
    """
    Block session for seconds, meanwhile, buffers events
    """
    getsession().read_events ((), seconds)

def flushevent(event = 'input', timeout = -1):
    """
    Remove any data for specified event buffered from the main bbs engine.
    """
    return getsession().flush_event(event, timeout)


def flushevents(events = ('input',), timeout = -1):
    """
    Remove any data for specified events buffered from the main bbs engine.
    """
    return [flushevent(evt, timeout) for evt in events]

def showcp437 (filepattern):
    """
    Display a cp437 artfile relative to current script path, trimming SAUCE
    data and translating cp437 to utf8. A glob pattern can be used, such as
    'art/login*.ans'
    """
    fobj = ropen(filepattern, 'rb') \
      if '*' in filepattern or '?' in filepattern \
        else fopen(filepattern, 'rb')
    term = getterminal()
    return chompn(from_cp437(SAUCE(fobj).__str__())) + term.normal

