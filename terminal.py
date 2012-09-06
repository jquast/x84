# -*- coding: iso-8859-1 -*-
"""
Terminal interface module for X/84 BBS, http://1984.ws
$Id: terminal.py,v 1.32 2010/01/02 02:09:40 dingo Exp $
"""
__license__ = 'ISC'
__author__ = 'Jeffrey Quast <dingo@1984.ws>'

# channel is of format (client, pipe)
CHANNELS = []
PROCS = []

# threads are used for connect negotiation
import threading

# each new terminal and session is a forked process
import multiprocessing
import time
import logging
import os
import re
import blessings

logger = multiprocessing.get_logger()
logger.setLevel (logging.DEBUG)

def start_process(channel, termtype, rows, columns):
  import bbs.session
  global logger
  channel.send (('output', 'process %d started\r\n' % (os.getpid(),),))
  new_session = bbs.session.Session \
      (terminal=BlessedIPCTerminal (channel, termtype, rows, columns),
       pipe=channel)
  return new_session.run ()

# want: callback mechanism within telnet.py for NAWS
class BlessedIPCTerminal(blessings.Terminal):
  def __init__(self, ipc_channel, terminal_type, rows, columns):
    # patch in a .rows and .columns static property.
    # this property updated by engine.py poll routine (?)
    self.rows, self.columns = rows, columns
    self.kind = terminal_type
    class IPCStream(object):
      def __init__(self, channel):
        self.channel = channel
      def write(self, data):
        self.channel.send (('output', data))
      def fileno(self):
        return self.channel.fileno()
      def close(self):
        return self.channel.close ()

    blessings.Terminal.__init__ (self, kind=terminal_type,
        stream=IPCStream(ipc_channel), force_styling=True)
    import curses
    import curses.has_key

    # after setupterm(), use the curses.has_key._capability_names
    # dictionary to find the terminal descriptions for special keys.
    # if any value is returned, store in self.keymap with the value
    # of the curses keycode. curses keycodes are numeric values
    # above 256.
    self.keymap = dict()
    for keycode, cap in curses.has_key._capability_names.iteritems():
      v = curses.tigetstr(cap)
      if v is not None:
        self.keymap[v] = keycode

    # finally, make all curses keycodes available as attributes to
    # blessings terminal instances, for comparison.
    for attr in [a for a in dir(curses) if a.startswith('KEY_')]:
      setattr(self, attr , getattr(curses, attr))

  def trans_input(self, data):
    while len(data):
      match=False
      for keyseq, keycode in self.keymap.iteritems():
        if data.startswith(keyseq):
          data = data[len(keyseq):]
          yield keycode
          match=True
          break
      if match == False:
        if data[0] == '\000':
          pass
        if data[0] == '\r':
          yield self.KEY_ENTER
        else:
          yield data[0]
        data = data[1:]

  def keyname(self, keycode):
    for attr in sorted([k for k in dir(self) if k.startswith('KEY_')]):
      if keycode == getattr(self, attr):
        return attr

  def has_key(self, ch):
    import curses.has_key
    return curses.has_key.has_key (ch)

  @property
  def terminal_type(self):
    return self.kind

  def _height_and_width(self):
    # override termios window size unpacking
    """Return a tuple of (terminal height, terminal width)."""
    return self.rows, self.columns

def on_disconnect(client):
  logger.info ('Disconnected from telnet client %s:%s',
      client.address, client.port)
  return

def on_connect(client):
  logger.info ('Connection from telnet client %s:%s',
      client.address, client.port)
  t = ConnectTelnetTerminal(client)
  t.start ()

class ConnectTelnetTerminal (threading.Thread):
  """
  This thread spawns long enough to
    1. set socket and telnet options
    2. ask about terminal type and size
    3. spawn and register a sub-process
    4. create & register IPC pipes,
    5. initialize a curses-capable terminal (blessings)
    6. start and register a new session
  """
  TIME_WAIT = 1.0
  TIME_PAUSE = 0.5
  TIME_POLL  = 0.05
  TTYPE_UNDETECTED = 'unknown client'
  # see 'xresize' from X11
  WINSIZE_TRICK= ( \
        ('vt100', ('\x1b[6n'), re.compile('\033' + r"\[(\d+);(\d+)R")),
        ('sun', ('\x1b[18t'), re.compile('\033' + r"\[8;(\d+);(\d+)t")))

  def __init__(self, client):
    threading.Thread.__init__(self)
    self.client = client

  def spawn_session(self):
    """ Our last action as enacting thread is to create a sub-process.
        In previous incarnations, this software was multi-threaded.
        The mixing in of curses.setupterm() now requires a unique process space.

        Its just as well. This avoids the GIL and forces all IPC data to be
        communicated via IPC instead of shared variables or memory regions.
    """

    parent_conn, child_conn = multiprocessing.Pipe()
    p = multiprocessing.Process \
        (target=start_process,
           args=(child_conn, self.client.terminal_type,
        self.client.rows, self.client.columns))
    p.start ()
    CHANNELS.append ((self.client, parent_conn,))
    PROCS.append (p)

  def run(self):
    """ The purpose of this thread is to negotiate the environment with the
    remote client as best as possible before spawning the user session, which
    begins using terminal capabilities and sockets configured here. """
    import socket
    from telnet import SGA, ECHO, NAWS, TTYPE, SEND, LINEMO

    # set non-blocking input
    self.client.sock.setblocking (0)

    # use tcp keepalive
    self.client.sock.setsockopt (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    enabledRemote = self.client._check_remote_option
    enabledLocal = self.client._check_local_option
    timeleft = lambda t: time.time() -t < self.TIME_WAIT

    self.client._iac_dont(LINEMO)
    self.client._iac_wont(LINEMO)
    self.client._note_reply_pending(LINEMO, True)

    # supress go-ahead
    if not (enabledRemote(SGA) is True and enabledLocal(SGA) is True):
      self.client.send('request-do-sga\r\n')
      self.client.request_do_sga ()
      self.client.socket_send() # push
      t = time.time()
      while not (enabledRemote(SGA) is True and enabledLocal(SGA) is True):
          time.sleep (self.TIME_POLL)
          if not timeleft(t):
            break
      if (enabledRemote(SGA) is True and enabledLocal(SGA) is True):
        self.client.send ('sga enabled (negotiated)\r\n')
      else:
        self.client.send ('failed: supress go-ahead\r\n')
    else:
      self.client.send('sga enabled\r\n')

    # will echo
    if self.client.telnet_echo is False:
      self.client.send('request-will-echo\r\n')
      self.client.request_will_echo ()
      self.client.socket_send() # push
      t = time.time()
      while self.client.telnet_echo is False:
        time.sleep (self.TIME_POLL)
        if not timeleft(t):
          break
      if self.client.telnet_echo:
        self.client.send ('echo enabled (negotiated)\r\n')
    else:
      self.client.send ('echo enabled\r\n')
    self.client.socket_send() # push

    # negotiate about window size
    if None in (self.client.columns, self.client.rows,):
      self.client.send('request-naws\r\n')
      self.client.request_naws ()
      self.client.socket_send() # push
      t = time.time()
      while None in (self.client.columns, self.client.rows,):
        time.sleep (self.TIME_POLL)
        if not timeleft(t):
          break
      if None in (self.client.columns, self.client.rows,):
        self.client.send ('failed: negotiate about window size\r\n')
      else:
        self.client.send ('window size determined (negotiated)\r\n')
    else:
      self.client.send ('window size determined (unsolicited)\r\n')

    # send to client --> pos(999,999)
    # send to client --> report cursor position
    # read from client <-- window size
    if None in (self.client.columns, self.client.rows,):
      self.client.send ('store-cursor')
      self.client.send ('\x1b[s')
      for kind, query_seq, response_pattern in self.WINSIZE_TRICK:
        self.client.send ('\r\n                -- move-to corner' \
            '& query for %s' % (kind,))
        self.client.send ('\x1b[999;999H')
        self.client.send (query_seq)
        inp=''
        t = time.time()
        while self.client.idle() < self.TIME_PAUSE:
          time.sleep (self.TIME_POLL)
          if not timeleft(t):
            break
        inp = self.client.get_input()
        match = response_pattern.search (inp)
        if match:
          self.client.rows, self.client.columns = match.groups()
          break
        self.client.send ('\x1b[r')
        self.client.send ('cursor restored --')
    self.client.columns, self.client.rows = \
        80 if self.client.columns is None   \
          else self.client.columns,         \
        24 if self.client.rows is None      \
          else self.client.rows
    self.client.send ('window size: %dx%d\r\n' \
        % (self.client.columns, self.client.rows,))
    self.client.socket_send() # push

    # Try #1 -- we need this to work best
    if self.client.terminal_type == self.TTYPE_UNDETECTED:
      self.client.send ('request-terminal-type\r\n')
      self.client.request_terminal_type ()
      self.client.socket_send() # push
      t = time.time()
      while self.client.terminal_type == self.TTYPE_UNDETECTED:
        if not timeleft(t):
          break
        time.sleep (self.TIME_POLL)
      if self.client.terminal_type == self.TTYPE_UNDETECTED:
        self.client.send ('failed: terminal type not determined.\r\n')
      else:
        self.client.send ('terminal type determined (negotiated)\r\n')
    else:
      self.client.send ('terminal type determined (unsolicited)\r\n')
    self.client.socket_send() # push

    # Try #2 - ... this is bullshit
    if self.client.terminal_type == self.TTYPE_UNDETECTED:
      self.client.send('request answerback sequence\r\n')
      self.client.request_wont_echo ()
      self.client.socket_send () # push
      self.client.clear_input () # flush input
      self.client.send ('\005')  # send request termtype
      self.client.socket_send () # push
      t= time.time()
      while not self.client.input_ready:
        time.sleep (self.TIME_POLL)
        if not timeleft(t):
          break
      inp=''
      if self.client.input_ready:
        t = time.time()
        while self.client.idle() < self.TIME_PAUSE:
          time.sleep (self.TIME_POLL)
          if not timeleft(t):
            break
        inp = self.client.get_input()
        self.client.terminal_type = inp.strip()
        self.client.send ('answerback reply receieved\r\n')
      else:
        self.client.send ('failed: answerback reply not receieved\r\n')
      self.client.request_will_echo ()

    self.client.terminal_type = 'vt220' \
        if self.client.terminal_type == self.TTYPE_UNDETECTED \
        else self.client.terminal_type
    self.client.send ('terminal type: %s\r\n' % (self.client.terminal_type,))
    self.client.socket_send () # push
    self.spawn_session()

    logger.info ('thread complete')
    return # end of thread
