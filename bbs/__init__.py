"""
bbs module for X/84 BBS https://github.com/jquast/x84
everything in the bbs package is exported as a global to all bbs session
scripts. It is as if the statement:

    from bbs import *

Is implied for all session scripts.
"""
import msgbase
import bbs.ini
ini = bbs.ini
from bbs.exception import Disconnect, Goto, ConnectionTimeout
from bbs.cp437 import from_cp437
from bbs.door import Door
from bbs.dbproxy import DBProxy
from bbs.userbase import User, getuser, finduser
from bbs.userbase import userexist, authuser, listusers
from bbs.session import getsession, logger
from bbs.fileutils import abspath, fopen, ropen
from bbs.leftright import Selector
from bbs.lightwin import Lightbar
from bbs.pager import Pager
from bbs.ansiwin import AnsiWindow
from bbs.output import echo, timeago, Ansi, chompn
from bbs.input import getch, getpos, readline, readlineevent
from bbs.input import LineEditor, ScrollingEditor
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
    'finduser',
    'userexist',
    'authuser',
    'getuser',
    'listusers',
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
    'flushevent',
    'flushevents',
    'getsession',
    'getterminal',
    'gethandle',
    'getch',
    'getpos',
    'sleep',
    'echo',
    'abspath',
    'fopen',
    'ropen',
    'showfile',
    'readline',
    'readlineevent',
    'msgbase',
    'SAUCE',]

def getterminal():
    """
    Return blessings terminal instace of this session.
    """
    return getsession().terminal


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
    return getsession().read_event(events, timeout)

def readevent(event='input', timeout=None):
    """
    Poll for Session event.
    """
    return getsession().read_event((event,), timeout)[1]

def sleep (seconds):
    """
    Block session for seconds, meanwhile, buffers events
    """
    getsession().read_event ((), seconds)

def flushevent(event = 'input', timeout = -1):
    """
    Remove any data for specified event buffered from the main bbs engine.
    """
    return getsession().flush_event(event, timeout)


def flushevents(events = ['input'], timeout = -1):
    """
    Remove any data for specified events buffered from the main bbs engine.
    """
    return [flushevent(e, timeout) for e in events]


def showfile (filename, cleansauce=True, file_encoding='cp437'):
    """
    Display a file to the user. This is different from a echo(open().read()) in
    several ways:
        1. by default, it presumes the file is in CP437 encoding, and
        translates to requivalent unicode bytes. CP437 encoding is used for
        "ansi art".
        2. it is possible to simulate a bits-per-second speed
    """
    # this is for ansi art, really. if you're not doing that, use .read() and
    # such. this is overkill u kno?
    # when unspecified, session interprets charset of file
    # open a random file if '*' or '?' is used in filename (glob matching)
    fobj = ropen(filename, 'rb') \
      if '*' in filename or '?' in filename \
        else fopen(filename, 'rb')

    data = SAUCE(fobj).__str__() if cleansauce else fobj.read()
    if file_encoding == 'cp437':
        data = from_cp437(data)
    else:
        data = data.decode(file_encoding)
    if 0 == bps:
        return chompn(data) + getterminal().normal
