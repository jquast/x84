"""
Terminal interface module for X/84 BBS, http://1984.ws
$Id: terminal.py,v 1.32 2010/01/02 02:09:40 dingo Exp $
"""
__license__ = 'ISC'
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast <dingo@1984.ws>',
                 'Copyright (c) 2005 Johannes Lundberg <johannes.lundberg@gmail.com>']

import time, logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from twisted.internet.protocol import Protocol
from twisted.internet import reactor

from ascii import esc
import session
import ansi
import keys
import db

# a simple list of allocated TTY's
TID = []

from re import compile as REGEX
# Keymap for CSI Sequences for popular terminal emulators.
# the 'ansi' keymap tries to please many types of terminals
CSI_KEYMAP= { \
  'linux': { \
    'INSERT': REGEX(esc + r"\[2~"),      'ALTDEL': REGEX(esc + r"\[3~"),
    'PGUP':   REGEX(esc + r"\[5~"),      'PGDOWN': REGEX(esc + r"\[6~"),
    'HOME':   REGEX(esc + r"\[1~"),      'END':    REGEX(esc + r"\[4~"),
    'UP':     REGEX(esc + r"\[A~?"),      'DOWN':   REGEX(esc + r"\[B~?"),
    'RIGHT':  REGEX(esc + r"\[C~?"),      'LEFT':   REGEX(esc + r"\[D~?"),
  }, \
  'vt100': { \
    'FIND':   REGEX(esc + r"\[1~"),      'INSERT': REGEX(esc + r"\[2~"),
    'ALTDEL': REGEX(esc + r"\[3~"),      'SELECT': REGEX(esc + r"\[4~"),
    'PGUP':   REGEX(esc + r"\[5~"),      'PGDOWN': REGEX(esc + r"\[6~"),
    'HOME':   REGEX(esc + r"\[7~"),      'END':    REGEX(esc + r"\[8~"),
    'UP':     REGEX(esc + r"\[A"),       'DOWN':   REGEX(esc + r"\[B"),
    'RIGHT':  REGEX(esc + r"\[C"),       'LEFT':   REGEX(esc + r"\[D") \
}, \
 'ansi': { \
  'F1':    REGEX(esc + r"(OP|\[11~)"),'F2':     REGEX(esc + r"(OQ|\[12~)"),
  'F3':    REGEX(esc + r"(OR|\[13~)"),'F4':     REGEX(esc + r"(OS|\[14~)"),
  'F5':    REGEX(esc + r"(Ot|\[15~)"),'F6':     REGEX(esc + r"\[17~"),
  'F7':    REGEX(esc + r"\[18~"),     'F8':     REGEX(esc + r"\[19~"),
  'F9':    REGEX(esc + r"\[20~"),     'F10':    REGEX(esc + r"\[21~"),
  'F11':   REGEX(esc + r"\[23~"),     'F12':    REGEX(esc + r"\[24~"),
  'FIND':  REGEX(esc + r"\[1~"),      'INSERT': REGEX(esc + r"\[(2~|@)"),
  'ALTDEL':REGEX(esc + r"\[3~"),      'SELECT': REGEX(esc + r"\[4~"),
  'PGUP':  REGEX(esc + r"\[(5~|V)"),  'PGDOWN': REGEX(esc + r"\[(6~|U)"),
  'HOME':  REGEX(esc + r"\[(7~|H)"),  'END':    REGEX(esc + r"\[(8~|[FK])"),
  'UP':    REGEX(esc + r"\[O?A"),     'DOWN':   REGEX(esc + r"\[O?B"),
  'RIGHT': REGEX(esc + r"\[O?C"),     'LEFT':   REGEX(esc + r"\[O?D")
 }
}

# newline, backspace/delete issue (127->^H), # and international
# assistant: windows codepage 1252 -> dos codepage 850
from string import maketrans
transtable = maketrans ( \
  '\r' '\x7F' '\xE5' '\xE4' '\xF6' '\xC5' '\xC4' '\xD6',
  '\n' '\x08' '\x86' '\x84' '\x94' '\x8F' '\x8E' '\x99')

class Terminal(object):
  xSession = None
  tty = '?' # [p-zP-T][0-9a-zA-Z]
  spy = None # set to username if someone is spying
  readOnly = False
  def __init__(self):
    self.attachtime = time.time()
    self.KEY = keys.KeyClass()
    self.resume_sessions = []

  def addsession(self, user=None, scriptname=None):
    " create new session for this terminal and begin "
    def find_tty():
      def ch_range(a='a',b='z'):
        return ''.join([chr(z) for z in range(ord(a),ord(b)+1)])
      for a in ch_range('p','z')+ch_range('P','T'):
        for b in ch_range('0','9')+ch_range('a','z')+ch_range('A','Z'):
          self.tty='%s%s' % (a,b,)
          if not self.tty in TID:
            TID.insert (0,self.tty)
            return

    # for now, we fake a tty device from an internal list of fictional ones.
    # this system not use real pseudo terminals, it implements its own.
    # It is helpful to have meaningful names for terminals.
    find_tty()

    # XXX we need to track terminal<->session more closely,
    # but a thread spawned inside session.start() prevents us
    # from farming this information without introducing
    # thread race conditions
    self.xSession = session.Session(self)
    self.xSession.start (handle=user, script=scriptname)

  def handleinput(self, data):
    """
    receive keyboard input, translate into keycodes, and place
    result into the sessions 'input' event queue. The complexity
    of buffering and timing input is not done here, so if a
    multi-byte sequence causes this method to be called more
    than once to complete a pattern, we will not be able to parse it.
    """
    # translate keycodes through input filter
    out = ''

    # use user-defined keymap if we have an input
    # filter that matches it. otherwise, use the
    # system-wide default
    if self.xSession.TERM in CSI_KEYMAP:
      keymap = self.xSession.TERM
    else:
      keymap = db.cfg.default_keymap

    skip = 0 # used to skip beyond sequences
    for n, ch in enumerate(data):
      if skip and skip > n:
        continue

      if ch == '\014':
        # send refresh screen event because (^L) was pressed,
        # however, continue sending on to user script, some
        # scripts may chose to process this keystroke instead
        # of reading the 'refresh' event
        self.xSession.event_push ('refresh', '^L')

      if db.cfg.detach_keystroke and ch == db.cfg.detach_keystroke:
        # the special detach keystroke has been pressed (^D)
        # if we have no resume sessions, tell the user what
        # why they are about to be disconnected.
        if not len(self.resume_sessions):
          logger.warn ('[tty%s] ^D keypress detected, but no resume sessions exist.', self.tty)
        else:
          logger.info ('[tty%s] ^D keypress detected, destroying terminal', self.tty)
          self.destroy()
          return # shouldnt be necessary

      # try to match the regular expression patterns for the
      # input terminal we use here and translate them to helpful
      # keycodes that can be used as KEY.PGUP etc.
      for kname, pattern in CSI_KEYMAP[keymap].items():
        match = pattern.match(data[n:])
        if match:
          out += self.KEY[kname]
          skip = n+match.end()
          break

      if not match and data[n:].startswith(esc):
        logger.warn('[tty%s] unrecognized keyseq %r', self.tty, repr(data))

      if not match:
        # copy it as-is to userland
        out += ch

    if out:
      out = out.translate(transtable)
      if self.readOnly:
        logger.warn('[tty%s] ro session denied keystroke: %r', self.tty, out)
        return
      self.xSession.putevent('input', out)

  def destroy(self):
    """
      destroy a terminal, re-attaching to stored resume session if
      available- This occurs when a hijacked terminal is destroyed,
      we need to provide hijacker with a session to reattach to, this
      is done using .attachterminal (self)
    """

    # remove terminal from current session
    self.xSession.detachterminal (self)

    if self.resume_sessions:
      callback = session.getsession(self.resume_sessions.pop())
      if callback:
        logger.info('[tty%s] resuming %s terminal %s to session %i',
          self.tty, self.type, self.info, callback.sid)
        # and re-attach to prior session (hijacking occured)
        callback.attachterminal (self)
        return
    logger.info ('[tty%s] destroying %s terminal %s from session %i',
      self.tty, self.type, self.info, self.xSession.sid)
    self.close ()

  def close(self):
    try:
      TID.remove(self.tty)
    except ValueError:
      pass

class RemoteTerminal (Protocol, Terminal):
  def connectionLost (self, reason):
    logger.warn ('[tty%s] connection lost: %s', self.tty, reason.value)
    self.destroy ()
    Protocol.connectionLost (self, reason)

  def connectionMade (self):
    """
    Create new session. This method should be derived to tailor
    terminal initialization for the appropriately derived terminal
    type or network service. Make sure to call self.addsession()!
    """
    # BEGIN client session!
    self.addsession ()

  def dataReceived (self, data):
    " process data recieved from terminal"
    self.handleinput (data)

  def write (self, data):
    " write data to terminal "
    reactor.callFromThread (self.transport.write, data)

  def close (self):
    " close terminal "
    reactor.callFromThread (self.transport.loseConnection)
    Terminal.close (self)
