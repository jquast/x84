import msgbase # FIX, work on msging...
import ini
from exception import Disconnect, Goto, ConnectionTimeout
from strutils import chompn, asctime, ansilen, chkseq, seqp, seqc, maxanswidth
from cp437 import fromCP437
from door import Door
from dbproxy import DBSessionProxy
from userbase import User, getuser, finduser, userexist, authuser, listusers
from session import getsession, logger
from fileutils import abspath, fopen, ropen
from output import echo, oflush, delay
from input import getch, getpos, readline, readlineevent
from ansiwin import AnsiWindow
from editor import HorizEditor
from leftright import LeftRightClass, YesNoClass, PrevNextClass
from lightwin import LightClass
from pager import ParaClass
from sauce import SAUCE

__all__ = [
    'ConnectionTimeout',
    'Door',
    'fromCP437',
    'logger',
    'maxanswidth',
    'chompn',
    'asctime',
    'ansilen',
    'chkseq',
    'seqp',
    'seqc',
    'DBSessionProxy',
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
    'getpos',
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
    'SAUCE',]

def getterminal():
  return getsession().terminal


def gethandle():
  return getsession().handle


def disconnect():
  raise exception.Disconnect('disconnect')


def goto(*arg):
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


def showfile(filename, bps=0, pause=0.1, cleansauce=True, file_encoding='cp437'):
  # when unspecified, session interprets charset of file
  # open a random file if '*' or '?' is used in filename (glob matching)
  fobj = ropen(filename, 'rb') \
    if '*' in filename or '?' in filename \
      else fopen(filename, 'rb')
  session_encoding = getsession().encoding
  data = chompn(SAUCE(fobj).__str__() if cleansauce else fobj.read())
  if ('cp437', 'utf8') == (file_encoding, session_encoding):
    # convert from cp437 to unicode when the output terminal
    # is utf-8 encoded.
    data = fromCP437(data)
  elif ('cp437','cp437') == (file_encoding, session_encoding):
    # our client is cp437 too, decode as iso8859-1 so that
    # no data is transliterated from iso8859-1
    data = data.decode('iso8859-1')
  else:
    logger.warn ('unknown file_encoding to session_encoding')
    logger.warn ('file=%s, session=%s', encoding, session_encoding)
    data = data.decode(file_encoding)

  if 0 == bps:
    echo (data)
    echo (getterminal().normal)
    return

  # display at a timed speed; re-expereince the pace of 9600bps ...
  cpp = int((float(bps)/8) *pause)
  for n, ch in enumerate(data):
    if 0 == (n % cpp):
      getsession().read_event(events=['input'], timeout=pause)
    echo (ch)
