# begin XXX cut/transform XXX
#from userbase import finduser, getuser, setuser

import userbase
import msgbase
from ansi import pos
# end XXX cut/transform XXX
import ini
from dbproxy import DBProxy
from userbase import User, getuser, finduser, userexist, authuser, listusers
from session import getsession
from fileutils import abspath, fopen, ropen
from output import echo, oflush, delay
from input import getch, readline, readlineevent
from ansiwin import AnsiWindow
from editor import HorizEditor
from leftright import LeftRightClass, YesNoClass, PrevNextClass
from lightwin import LightClass
from pager import ParaClass
from sauce import SAUCE

__all__ = [
    'DBProxy',
    'User',
    'finduser',
    'userexist',
    'authuser',
    'getuser',
    'listusers',
    'ini',
    'AnsiWindow',
    'HorizEditor',
    'LeftRightClass',
    'YesNoClass',
    'PrevNextClass',
    'LightClass',
    'ParaClass',
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
    'delay',
    'oflush',
    'echo',
    'abspath',
    'fopen',
    'ropen',
    'showfile',
    'readline',
    'readlineevent',
    'msgbase',
    'SAUCE',
]

def getterminal():
    return getsession().getterminal()

def gethandle():
    return getsession().handle


def getterminal():
    return getsession().getterminal()


def disconnect():
    import exception as exception
    raise exception.Disconnect('disconnect')


def goto(*arg):
    import exception
    raise exception.Goto(arg)


def gosub(*arg):
    return getsession().runscript(*(arg[0],) + arg[1:])


def sendevent(pid, event, data):
    return getsession().send_event('event', (pid, event, data))


def broadcastevent(event, data):
    return getsession().send_event('global', (getsession().pid, event, data))


def readevent(events = ['input'], timeout = None):
    return getsession().read_event(events, timeout)


def flushevent(event = 'input', timeout = -1):
    return getsession().flush_event(event, timeout)


def flushevents(events = ['input'], timeout = -1):
    return [flushevent(e, timeout) for e in events]


def loginuser(handle):
    import time as time
    u = userbase.getuser(handle)
    u.calls += 1
    u.lastcall = time.time()


def showfile(filename, bps=0, pause=0.1, cleansauce=True):
    import strutils as strutils
    if '*' in filename or '?' in filename:
        fobj = ropen(filename, 'rb')
    else:
        fobj = fopen(filename, 'rb')
    if cleansauce:
        data = str(SAUCE(fobj))
    else:
        data = strutils.chompn(fobj.read())
    if not bps:
        echo(strutils.chompn(data))
    else:
        cps = bps / 8
        cpp = cps * pause
        n = 0
        for ch in data:
            n += 1
            if n == int(cpp):
                getsession().read_event(events=['input'], timeout=pause)
                n = 0
            echo(ch)
