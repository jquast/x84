import multiprocessing
import traceback
import itertools
import logging
import time
import sys
import os

import ini
import exception
import scripting

logger = multiprocessing.get_logger()
mySession = None
TAP = False # if True, keystrokes logged at debug level

def getsession():
  """Return session, after a .run() method has been called on any 1 instance.
  """
  assert mySession is not None, \
      'a Session() instance must be initialized with .run() method'
  return mySession

class Session(object):
  """
  _script_stack is a list of script modules for tracking active script location
  during consecutive gosub() calls. When this script is exausted, the session
  ends. On instantiation, the value is set to the 'script' option of subsection
  'matrix' in the settings ini file. When run() is called, _script_stack begins
  execution.

  _buffer is a dict keyed by event names, containing lists of data buffered
  from the IPC pipe of the parrent process during calls to read_event() that
  were not immediately yielded. _buffer['input'] contains keypresses. a call to
  flush_event() discards all data waiting for an event. a call to read_event()
  returns a any any data waiting on the event queue within the specified
  timeout. if data is recieved on the IPC pipe that is not requested, it is
  buffered to _buffer.

  _source is a tuple that indicates the origin of the terminal in some form,
  such as (client.addr, client.port) for telnet connections.
  """
  _user = None
  _handle = None
  _activity = None
  _cwd = None
  last_input_time = 0.0
  connect_time = 0.0

  def __init__ (self, terminal=None, pipe=None, encoding=None,
  source=('undef', None)):
    self.pipe = pipe
    self.terminal = terminal
    self._script_stack = list(((ini.cfg.get('matrix','script'),),))
    self._encoding = encoding if encoding is not None \
        else ini.cfg.get('session', 'default_encoding')
    self._buffer = dict()
    self._source = source
    self.last_input_time = \
        self.connect_time = time.time()

  def idle(self):
    return time.time() -self.last_input_time

  def duration(self):
    return time.time() -self.connect_time

  @property
  def activity(self):
    """Current activity (arbitrarily set)."""
    return self._activity

  @activity.setter
  def activity(self, value):
    if self._activity != value:
      logger.info ('%s setactivity %s', self.handle, value)
      self._activity = value


  @property
  def handle(self):
    """User handle."""
    return self._handle

  @handle.setter
  def handle(self, value):
    # _handle only set by @user.setter
    raise TypeError, 'handle property read-only'


  @property
  def user(self):
    """User record object."""
    return self._user

  @user.setter
  def user(self, value):
    import userbase
    assert type(value) is userbase.User
    logger.info ('setuser %s', value.handle)
    self._user = value
    self._handle = value.handle

  @property
  def origin(self):
    """A string describing the source of this connection."""
    return '%r' % (self.souce,)

  @property
  def source(self):
    """A tuple describing the session source, usually in
       the form of (sock.addr, sock.port,). """
    return self._source

  @source.setter
  def source(self, value):
    assert type(value) is tuple
    self._source = value

  @property
  def cwd(self):
    """Current working directory."""
    return self._cwd if self._cwd is not None else '.'

  @cwd.setter
  def cwd(self, value):
    if self._cwd != value:
      logger.debug ('%s setcwd %s', self.handle, value)
      self._cwd = value


  @property
  def encoding(self):
    """Input and Output encoding."""
    return self._encoding

  @encoding.setter
  def encoding(self, value):
    logger.info ('%s setencoding %s', self.handle, value)
    self._encoding = value


  @property
  def pid(self):
    """Process ID."""
    return os.getpid()


  def run(self):
    """
      The main script execution loop for a session handles the
      movement of the client users throughout userland via calls to
      runscript(). The client scripts, however, make use goto()
      which causes the ScriptChange exception to be raised and handled
      here, or by bypassing us through a gosub() function which too
      calls runscript(), via engine.getsession().runscript()
    """
    import copy
    global mySession
    assert mySession is None, 'run() cannot be called twice'
    mySession = self
    fallback_stack = copy.copy(self._script_stack)
    while len(self._script_stack) > 0:
      logger.debug ('%s: script_stack is %s',
          self.handle, self._script_stack)
      try:
        lastscript = self._script_stack[-1]
        value = self.runscript (*self._script_stack.pop())
        if not self._script_stack:
          logger.error ('_script_stack = <fallback_stack: %r>', \
              fallback_stack)
          self._script_stack = fallback_stack
          continue
      except exception.Goto, e:
        logger.debug ('Goto: %s' % (e,))
        self._script_stack = [e[0] + tuple(e[1:])]
        continue
      except exception.Disconnect, e:
        logger.info ('User disconnected: %s' % (e,))
        return
      except exception.ConnectionClosed, e:
        logger.info ('Connection Closed: %s' % (e,))
        return
      except exception.SilentTermination, e:
        logger.info ('Silent Termination: %s' % (e,))
        return
      except exception.ScriptError, e:
        logger.error ("ScriptError rasied: %s", e)
      except Exception, e:
        # Pokemon exception. question: can this python code
        # be made to look like an ascii poke-ball?
        t, v, tb= sys.exc_info()
        map (logger.error, (l.rstrip() \
            for l in itertools.chain \
              (traceback.format_tb(tb), \
               (fe for fe in traceback.format_exception_only(t, v)))))
      if 0 != len(self._script_stack):
        # recover from a general exception or script error
        toss = self._script_stack.pop()
        logger.info ('%s after %s popped from script stack.',
          'continue' if 0 != len(self._script_stack) else 'stop',
          toss)


  def write (self, data, encoding=None):
    """Write data to terminal stream as unicode."""
    if type(data) is not unicode:
      enc = self.encoding if encoding is None \
          else encoding
      data = data.decode (enc)
    self.terminal.stream.write (data)


  def flush_event (self, event, timeout=-1):
    """Flush all data buffered for 'event'."""
    data = 1
    while (None, None) != (event, data):
      event, data = self.read_event([event], timeout=timeout)


  def _event_pop(self, event):
    """Return first-most item buffered for event (FIFO)."""
    store = self._buffer[event].pop ()
    return store


  def _buffer_event (self, event, data):
    """
       Push data into FIFO buffer keyed by event.  If event is a string named
       'input', translate data as bytestrings into items yielded from generator
       self.terminal.trans_input().
    """
    if event == 'ConnectionClosed':
      raise exception.ConnectionClosed (data)
    if event == 'refresh-naws':
      # transliterate to 'refresh' event, but record new terminal dimensions
      (self.terminal.columns, self.terminal.rows) = data
      (event, data) = 'refresh', ('resize', data)
    if not self._buffer.has_key(event) or event == 'refresh':
      # create new buffer; only accept 1 most recent 'refresh' event
      self._buffer[event] = list()
    if event == 'input':
      for keystroke in self.terminal.trans_input(data, self.encoding):
        if keystroke == chr(12):
          # again; buffer only 1 most recent 'refresh' eventm
          # this time, if <ctrl+L> is pressed; there exists a KEY_REFRESH ...
          self._buffer['refresh'] = list((0, ('input', keystroke,),))
        self._buffer['input'].insert (0, keystroke)
      self._last_input_time = time.time()
      logger.debug ('%s event buffered, %s.', self.handle,
          (event, data if TAP else 'x' * len(data),))
    else:
      self._buffer[event].insert (0, data)
      logger.info ('%s event buffered, (%s,%s).', self.handle, event, data,)

  def send_event (self, event, data):
    """
       Send data to IPC pipe in form of (event, data).
       engine.py of the main process translates the following events into
       actions: 'output', send data to socket; 'global', duplicate data to all
       other IPC processes; and 'db-<schema>', a IPC database communication
       pipe used by dbproxy.py
    """
    self.pipe.send ((event, data))


  def read_event (self, events, timeout=None):
    """
       Poll for and return any buffered IPC data for events that have arrived
       in the form of (event, data). Always available is the 'input' event for
       keyboard input. A timeout of None waits indefinitely, otherwise
       (None, None) is returned when timeout has exceeded. when timeout of -1
       is used, this call is non-blocking.
    """
    (event, data) = (None, None)

    # return immediately any events that are already buffered
    for (event, data) in ((e, self._event_pop(e)) for e in events \
        if e in self._buffer and 0 != len(self._buffer[e])):
          return (event, data)

    t = time.time()
    timeleft = lambda t: \
        float('inf') if timeout is None \
        else timeout - (time.time() -t)
    waitfor = timeleft(t)
    while waitfor > 0:
      if self.pipe.poll (None if waitfor == float('inf') else waitfor):
        event, data = self.pipe.recv()
        if event == 'exception':
          (t, v, tb) = data
          map (logger.error, (l.rstrip() for l in tb))
          logger.error ('local traceback follows')
          raise t, v
        self._buffer_event (event, data)
        if event in events:
          return (event, self._event_pop(event))
        else:
          logger.debug ('not seeking event %s; pass.', (event,))
      # poll()
      if timeout == -1:
        return (None, None)
      waitfor = timeleft(t)
    return (None, None)


  def runscript(self, script, *args):
    """Execute script's .main() callable with optional *args."""
    import bbs
    logger.info ('%s runscript %r.', self.handle, (script, args,))

    self._script_stack.append ((script,) + args)
    try:
      self.script_name, self.script_filepath \
          = scripting.chkmodpath (script, self.cwd)
    except LookupError, e:
      raise exception.ScriptError, e

    current_path = os.path.dirname(self.script_filepath)
    if not current_path in sys.path:
      sys.path.append (current_path)
      logger.debug ('%s append to sys.path: %s', self.handle, current_path)

    script = scripting.load(self.cwd, self.script_name)
    for idx in bbs.__all__:
      setattr(script, idx, getattr(bbs, idx))
    assert hasattr(script, 'main'), \
        "%s: main() not found." % (self.script_name,)
    assert callable(script.main), \
        "%s: main not callable." % (self.script_name,)
    prev_path = self.cwd \
        if self.cwd is not None else current_path
    self.cwd = current_path
    value = script.main(*args)
    self.cwd = prev_path

    # we were gosub()'d here and have returned value.
    toss = self._script_stack.pop()
    logger.debug ('%s popped from script_stack, return value=%s', toss, value)
    return value
