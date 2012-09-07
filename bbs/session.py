import multiprocessing
import traceback
import itertools
import StringIO
import logging
import time
import sys
import os

import ini
import exception
import scripting

logger = multiprocessing.get_logger()

mySession = None

def getsession():
  assert mySession is not None, \
      'a Session() instance must be initialized with .run() method'
  return mySession


class Session(object):
  """
  _script_stack is a list of script modules for tracking active script location
  during consecutive gosub() calls. When this script is exausted, the session
  ends. On instantiation, the value is set to the 'matrixscript'.ini option.
  When run() is called, _script_stack begins execution.

  _buffer is a dict keyed by event names, containing lists of data buffered
  from the IPC pipe of the parrent process during calls to read_event() that
  were not immediately yielded. _buffer['input'] contains keypresses. a call to
  flush_event() discards all data waiting for an event. a call to read_event()
  returns a any any data waiting on the event queue within the specified
  timeout. if data is recieved on the IPC pipe that is not requested, it is
  buffered to _buffer.
  """
  _user = None
  _handle = None
  _activity = None
  _encoding = None
  _cwd = None
  _script_stack = None
  _buffer = None


  def __init__ (self, terminal=None, pipe=None):
    self.pipe = pipe
    self.terminal = terminal
    self._script_stack = list(((ini.cfg.get('system','matrixscript'),),))
    self._encoding = ini.cfg.get('system', 'encoding')
    self._buffer = dict()


  @property
  def activity(self):
    """Current activity (arbitrarily set)."""
    return self._activity

  @activity.setter
  def activity(self, value):
    if self._activity != value:
      logger.info ('%s/%s setactivity %s', self.pid, self.user, value)
      self._activity = value


  @property
  def handle(self):
    """User handle."""
    return self._handle


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
  def cwd(self):
    """Current working directory."""
    return self._cwd if self._cwd is not None else '.'

  @cwd.setter
  def cwd(self, value):
    if self._cwd != value:
      logger.info ('%s/%s setcwd %s',
          self.pid, self.user, value)
      self._cwd = value


  @property
  def encoding(self):
    """Input and Output encoding."""
    return self._encoding

  @encoding.setter
  def encoding(self, value):
    logger.info ('%s/%s setencoding %s',
        self.pid, self.user, value)
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
    logger.setLevel (getattr(logging, ini.cfg.get('session','log_level').upper()))
    while len(self._script_stack) > 0:
      logger.debug ('%s/%s script_stack: %s',
          self.pid, self.handle, self._script_stack)
      try:
        lastscript = self._script_stack[-1]
        self.runscript (*self._script_stack.pop())

        logger.warn ('crashloop: recovery <Session.runscript(%r)>' \
            % (lastscript,))
        if not self._script_stack:
          logger.error ('_script_stack = <fallback_stack: %r>', \
              fallback_stack)
          self._script_stack = fallback_stack
      except exception.Goto, e:
        logger.info ('Goto: %s' % (e,))
        self._script_stack = [e[0] + tuple(e[1:])]
        continue
      except exception.Disconnect, e:
        logger.info ('User disconnected: %s' % (e,))
        break
      except exception.ConnectionClosed, e:
        logger.info ('Connection Closed: %s' % (e,))
        break
      except exception.SilentTermination, e:
        logger.info ('Silent Termination: %s' % (e,))
        break
      except exception.ScriptError, e:
        logger.error ("ScriptError rasied: %s", e)
      except Exception, e:
        # Pokemon exception
        t, v, tb= sys.exc_info()
        map (logger.error, (l.rstrip() for l in itertools.chain \
            (traceback.format_tb(tb), \
             traceback.format_exception_only(t, v))))
      if 0 != len(self._script_stack):
        # recover from a general exception or script error
        toss = self._script_stack.pop()
        logger.info ('%s after %s popped from script stack.',
          'continue' if 0 != len(self._script_stack) else 'stop',
          toss)
    logger.info ('%s/%s end of session.', self.pid, self.handle)


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
      Push data into FIFO buffer keyed by event.
      If event is a string named 'input', translate data as bytestrings
      into items yielded from generator self.terminal.trans_input()
    """
    if not self._buffer.has_key(event):
      self._buffer[event] = list()
      logger.info ('%s %s new event buffer, %s.',
          self.pid, self.handle, event,)
    if event != 'input':
      self._buffer[event].insert (0, data)
      logger.debug ('%s %s event buffered, (%s,%s).',
          self.pid, self.handle, event, data,)
      return
    elif event == 'input':
      for keystroke in self.terminal.trans_input(data, self.encoding):
        self._buffer[event].insert (0, keystroke)


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
      (None, None) is returned when timeout has exceeded.
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

        if event == 'connectionclosed':
          raise exception.ConnectionClosed (data)

        # buffer data received. data can be any size, such as a multibyte
        # input sequence, or a chunk of output data. It must be pickable
        self._buffer_event (event, data)

        # when an event has just been buffered that is of an event specified
        # in the events=[] list, immediately pop the first column of data stored
        # in the buffer and return. For instance, a single keystroke
        if event in events:
          return (event, self._event_pop(event))

      # when the event recieved is not buffered and the event specified in
      # the events=[] list has not returned, then return (None, None) to
      # indicate that all buffers specified are flushed.
      if timeout == -1:
        return (None, None)

      waitfor = timeleft(t)
    return (None, None)


  def runscript(self, script, *args):
    """Execute script module's .main() function with optional *args as arguments."""
    import bbs
    logger.info ('%s/%s runscript %r, args=%r.',
        self.pid, self.handle, script, args)

    self._script_stack.append ((script,) + args)
    try:
      self.script_name, self.script_filepath \
          = scripting.chkmodpath (script, self.cwd)
    except LookupError, e:
      raise exception.ScriptError, e

    current_path = os.path.dirname(self.script_filepath)
    if not current_path in sys.path:
      logger.debug ('%s/%s append to sys.path: %s', self.pid, self.handle, current_path)
      sys.path.append (current_path)

    script = scripting.load(self.cwd, self.script_name)
    for idx in bbs.__all__:
      setattr(script, idx, getattr(bbs, idx))
    assert hasattr(script, 'main'), "%s: main() not found." % (self.script_name,)
    assert callable(script.main), "%s: main not callable." % (self.script_name,)
    prev_path = self.cwd \
        if self.cwd is not None else current_path
    self.cwd = current_path
    value = script.main(*args)
    self.cwd = prev_path

    # we were gosub()'d here and have returned value.
    toss = self._script_stack.pop()
    logger.debug ('%s popped from script_stack, return value=%s', toss, value)
    return value

  # XXX kill
  def oflush (self):
    import warnings
    warnings.warn ('unncessary', DeprecationWarning)
  # XXX kill
  def getterminal(self):
    import warnings
    warnings.warn ('use terminal attribute instead', DeprecationWarning)
    return self.terminal


