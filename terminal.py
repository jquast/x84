# -*- coding: iso-8859-1 -*-
import multiprocessing
import threading
import time
import re
import blessings

# global list of (TelnetClient, multiprocessing.Pipe,)
CHANNELS = []
# global list of multiprocessing.Process
PROCS = []

logger = multiprocessing.get_logger()

def start_process(child_conn, termtype, rows, columns):
  import bbs.session
  stream = IPCStream(child_conn)
  term = BlessedIPCTerminal (stream, termtype, rows, columns)
  new_session = bbs.session.Session (terminal=term, pipe=child_conn)
  return new_session.run ()

class IPCStream(object):
  """
  connect blessings 'stream' to 'child' multiprocessing.Pipe
  only write(), fileno(), and close() are called by blessings.
  """
  def __init__(self, channel):
    self.channel = channel
  def write(self, data):
    self.channel.send (('output', data))
  def fileno(self):
    return self.channel.fileno()
  def close(self):
    return self.channel.close ()

class BlessedIPCTerminal(blessings.Terminal):
  """
    Extend the blessings interface to manage keycode input.

    trans_input() is a generator that, given a sequence of terminal input as
    a character buffer, yields each keystroke as-is or as a keycode, which
    is an integer value above 255, and can be compared to KEY_* attributes
    of the class, such as KEY_ENTER -- or can be named to a string using the
    class keyname() method.

    Furthermore, .rows and .columns no longer queries using termios routines.
    They must be managed by another procedure. Instances of this class
    are stored in the global CHANNELS
  """
  def __init__(self, stream, terminal_type, rows, columns):
    # patch in a .rows and .columns static property.
    # this property updated by engine.py poll routine (?)
    self.rows, self.columns = rows, columns
    self.kind = terminal_type
    blessings.Terminal.__init__ (self,
        kind=terminal_type, stream=stream, force_styling=True)

    # after setupterm(), use the curses.has_key._capability_names
    # dictionary to find the terminal descriptions for keycodes.
    # if any value is returned, store in self._keymap with (sequence,
    # keycode) as (key, value). curses keycodes are numeric values
    # above 256, and can be matched, fe. as curses.KEY_ENTER
    import curses
    import curses.has_key
    self._keymap = dict()
    for (keycode, cap) in curses.has_key._capability_names.iteritems():
      v = curses.tigetstr(cap)
      if v is not None:
        self._keymap[v] = keycode

    # copy curses KEY_* attributes
    for attr in (a for a in dir(curses) if a.startswith('KEY_')):
      setattr(self, attr , getattr(curses, attr))

  def trans_input(self, data):
    """Yield single keystroke for each character or multibyte input sequence."""
    while len(data):
      match=False
      for keyseq, keycode in self._keymap.iteritems():
        if data.startswith(keyseq):
          # slice keyseq from *data
          yield keycode
          data = data[len(keyseq):]
          match=True
          break
      if match == False:
        if data[0] == '\x00':
          print 'skip nul'
          pass # telnet negotiation
        elif data[0] == '\r':
          yield self.KEY_ENTER # ?
        else:
          yield data[0].decode('utf-8') if type(data[0]) is str else data[0]
        # slice character from *data
        print 'slice!'
        data = data[1:]

  def keyname(self, keycode):
    """Return any matching keycode name for a given keycode."""
    for attr in (k for k in dir(self) if k.startswith('KEY_')):
      if keycode == getattr(self, attr):
        return attr

  def has_key(self, ch):
    import curses.has_key
    return curses.has_key.has_key (ch)

  @property
  def terminal_type(self):
    return self.kind

  def _height_and_width(self):
    """Return a tuple of (terminal height, terminal width)."""
    return self.rows, self.columns

def on_disconnect(client):
  import copy
  logger.info ('Disconnected from telnet client %s:%s',
      client.address, client.port)
  for tgt_client, pipe in copy.copy(CHANNELS):
    if client == tgt_client:
      CHANNELS.remove ((client, pipe,))

def on_connect(client):
  """Spawn a ConnectTelnetTerminal() thread for each new connection."""
  logger.info ('Connection from telnet client %s:%s',
      client.address, client.port)
  t = ConnectTelnetTerminal(client)
  t.start ()

class ConnectTelnetTerminal (threading.Thread):
  """
  This thread spawns long enough to
    1. set socket and telnet options
    2. ask about terminal type and size
    3. start a new session (as a sub-process)
  """
  TIME_WAIT = 1.0
  TIME_PAUSE = 0.5
  TIME_POLL  = 0.05
  TTYPE_UNDETECTED = 'unknown client'
  WINSIZE_TRICK= (
        ('vt100', ('\x1b[6n'), re.compile('\033' + r"\[(\d+);(\d+)R")),
        ('sun', ('\x1b[18t'), re.compile('\033' + r"\[8;(\d+);(\d+)t"))
  ) # see: xresize.c from X11.org

  def __init__(self, client):
    self.client = client
    threading.Thread.__init__(self)

  def _spawn_session(self):
    """ Our last action as enacting thread is to create a sub-process.
        In previous incarnations, this software was multi-threaded.
        The mixing in of curses.setupterm() now requires a unique process space.

        Its just as well. This avoids the GIL and forces all IPC data to be
        communicated via IPC instead of shared variables or memory regions.
    """
    global CHANNELS
    global PROCS
    parent_conn, child_conn = multiprocessing.Pipe()
    p = multiprocessing.Process \
        (target=start_process,
           args=(child_conn, self.client.terminal_type,
        self.client.rows, self.client.columns))
    p.start ()
    CHANNELS.append ((self.client, parent_conn,))
    PROCS.append (p)

  def run(self):
    """Negotiate and inquire about terminal type, telnet options,
    window size, and tcp socket options before spawning a new session."""
    self._set_socket_opts ()
    self._no_linemode ()
    self._try_sga ()
    self._try_echo ()
    self._try_naws ()
    self._try_ttype ()
    self._spawn_session ()

  def _set_socket_opts(self):
    """Set socket non-blocking and enable TCP KeepAlive"""
    import socket
    self.client.sock.setblocking (0)
    self.client.sock.setsockopt (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

  def _no_linemode (self):
    """Negotiate line mode (LINEMO) telnet option (off)."""
    from telnet import LINEMO
    self.client._iac_dont(LINEMO)
    self.client._iac_wont(LINEMO)
    self.client._note_reply_pending(LINEMO, True)

  def _try_sga(self):
    """Negotiate supress go-ahead (SGA) telnet option (on)."""
    from telnet import SGA
    enabledRemote = self.client._check_remote_option
    enabledLocal = self.client._check_local_option
    if not (enabledRemote(SGA) is True and enabledLocal(SGA) is True):
      self.client.send('request-do-sga\r\n')
      self.client.request_do_sga ()
      self.client.socket_send() # push
      t = time.time()
      while not (enabledRemote(SGA) is True and enabledLocal(SGA) is True):
          time.sleep (self.TIME_POLL)
          if not self._timeleft(t):
            break
      if (enabledRemote(SGA) is True and enabledLocal(SGA) is True):
        self.client.send ('sga enabled (negotiated)\r\n')
      else:
        self.client.send ('failed: supress go-ahead\r\n')
    else:
      self.client.send('sga enabled\r\n')

  def _try_echo(self):
    """Negotiate echo (ECHO) telnet option (on)."""
    if self.client.telnet_echo is False:
      self.client.send('request-will-echo\r\n')
      self.client.request_will_echo ()
      self.client.socket_send() # push
      t = time.time()
      while self.client.telnet_echo is False:
        time.sleep (self.TIME_POLL)
        if not self._timeleft(t):
          break
      if self.client.telnet_echo:
        self.client.send ('echo enabled (negotiated)\r\n')
    else:
      self.client.send ('echo enabled\r\n')
    self.client.socket_send() # push

  def _try_naws(self):
    """Negotiate about window size (NAWS) telnet option (on)."""
    if None in (self.client.columns, self.client.rows,):
      self.client.send('request-naws\r\n')
      self.client.request_naws ()
      self.client.socket_send() # push
      t = time.time()
      while None in (self.client.columns, self.client.rows,):
        time.sleep (self.TIME_POLL)
        if not self._timeleft(t):
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
        self.client.socket_send() # push
        inp=''
        t = time.time()
        while self.client.idle() < self.TIME_PAUSE:
          time.sleep (self.TIME_POLL)
          if not self._timeleft(t):
            break
        inp = self.client.get_input()
        match = response_pattern.search (inp)
        if match:
          self.client.rows, self.client.columns = match.groups()
          break
        self.client.send ('\x1b[r')
        self.client.send ('cursor restored --')

    # set to 80x24 if not detected
    self.client.columns, self.client.rows = \
        80 if self.client.columns is None   \
          else self.client.columns,         \
        24 if self.client.rows is None      \
          else self.client.rows
    self.client.send ('window size: %dx%d\r\n' \
        % (self.client.columns, self.client.rows,))
    self.client.socket_send() # push

  def _try_ttype(self):
    """Negotiate terminal type (TTYPE) telnet option (on)."""
    if self.client.terminal_type == self.TTYPE_UNDETECTED:
      self.client.send ('request-terminal-type\r\n')
      self.client.request_terminal_type ()
      self.client.socket_send() # push
      t = time.time()
      while self.client.terminal_type == self.TTYPE_UNDETECTED:
        if not self._timeleft(t):
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
        if not self._timeleft(t):
          break
      inp=''
      if self.client.input_ready:
        t = time.time()
        while self.client.idle() < self.TIME_PAUSE:
          time.sleep (self.TIME_POLL)
          if not self._timeleft(t):
            break
        inp = self.client.get_input()
        self.client.terminal_type = inp.strip()
        self.client.send ('answerback reply receieved\r\n')
      else:
        self.client.send ('failed: answerback reply not receieved\r\n')
      self.client.request_will_echo ()

    # set to vt220 if undetected
    self.client.terminal_type = 'vt220' \
        if self.client.terminal_type == self.TTYPE_UNDETECTED \
        else self.client.terminal_type
    self.client.send ('terminal type: %s\r\n' % (self.client.terminal_type,))
    self.client.socket_send () # push

  def _timeleft(self, t):
    return bool(time.time() -t < self.TIME_WAIT)
