import StringIO
import time
import sys
import os
import logging
import traceback
import multiprocessing

import bbs.ini
import exception # yech
import scripting

logger = multiprocessing.get_logger()
logger.setLevel (logging.DEBUG)

mySession = None
scripts = dict ()

def getsession():
  if mySession is None:
    raise KeyError, 'session uninitialized'
  return mySession

class Session(object):
  def __init__ (self, terminal=None, pipe=None):
    """
    .pipe is a pipe for event data, which includes user input,
    program IPC, and broadcasted data.
    Data is retrieved from this queue in read_event().

    the flag .recording=True can be set to farm all screen
    output in a list of tuples of (time, characters) that can be played
    back

    .current_script is stored as a tuple, first value is the script path,
    and remaining are function arguments passed to main(*args) during the
    runscript() procedure.

    use .cwd to track the filesystem location of current script, so that
    directory helper functions in fileutils.py remain relative.

    when .persistent is True, sessions that are disconnect unexpectedly
    have their session instance reserved in memory, so that it may be
    resumed to later, or attached to by another party. typically,
    persistent stays False until a user has authenticated. this shouldn't
    be necessary for local lines, but is critical for network lines.
    """
    self.pipe = pipe
    self.terminal = terminal
    self.pid = os.getpid()
    self.user = None
    self.handle, self.activity = '', ''
    # previously executed script id
    self.lastscript = None
    # our current path directory for script lookup
    self.cwd = ''
    # wether or not our session dies when last terminal closes
    self.persistent = False
    # set recording=True to record session to self.buffer['record']
    self.recording = False
    self.buffer = {
      'input': list(),
      'output': StringIO.StringIO(),
      'resume': StringIO.StringIO(),
      'record': list(),
    }
    #self.logintime, self.lastkeypress = time.time(), time.time()
    self.current_script = [(bbs.ini.cfg.get('system','matrixscript'),)]

  def run(self):
    """
    The main script execution loop for a session handles the
    movement of the client users throughout userland via calls to
    runscript(). The client scripts, however, make use goto()
    which causes the ScriptChange exception to be raised and handled
    here, or by bypassing us through a gosub() function which too
    calls runscript(), via engine.getsession().runscript()
    """
    global mySession
    assert mySession is None, \
        'sessionmain cannot be called twice'
    mySession = self
    logger.debug ('%d: script stack: %r', self.pid, self.current_script,)
    fallback_script = self.current_script
    while len(self.current_script) > 0:
      try:
        self.lastscript = self.current_script[-1]
        self.runscript (*self.current_script.pop())

        logger.warn ('crashloop: recovery <Session.runscript(%r)>' \
            % (self.lastscript,))
        if not self.current_script:
          logger.error ('current_script = <fallback_script: %r>', \
              fallback_script)
          self.current_script = fallback_script
      except exception.ScriptChange, e:
        logger.info ('ScriptChange: %s' % (e,))
        self.current_script = [e[0] + tuple(e[1:])]
      except exception.Disconnect, e:
        logger.info ('User disconnected: %s' % (e,))
        break
      except exception.ConnectionClosed, e:
        logger.info ('Connection Closed: %s' % (e,))
        break
      except exception.SilentTermination, e:
        logger.debug ('Silent Termination: %s' % (e,))
        break
      # Cannot find or execute script.
      except exception.ScriptError, e:
        logger.error ("ScriptError rasied: %s", e)
        if 0 == len(self.current_script):
          break
        throw_out = self.current_script.pop()
        logger.info ('continue after current_script.pop(): %s', throw_out)
      # Pokemon exception
      except Exception, e:
        t, v, tb= sys.exc_info()
        map (logger.error, (l.rstrip() for l in traceback.format_tb(tb)))
        map (logger.error, (l.rstrip() for l in traceback.format_exception_only(t, v)))
        if 0 == len(self.current_script):
          break
        throw_out = self.current_script.pop()
        logger.info ('continue after current_script.pop(): %s', throw_out)
    if len(self.current_script) == 0:
      logger.error ('no scripts remain')
    logger.info ('disconnected.')
    self.getterminal().destroy()

  #def setuser(self, user, recordLogin=True):
  #  " set session's user object "
  #  self.user = user
  #  self.handle = user.handle
  #  if recordLogin:
  #    self.logintime = time.time()

  #def getuser(self):
  #  return self.user

  def getcwd(self):
    return self.cwd

  def setcwd(self, path):
    if self.cwd != path:
      logger.debug ('userland path change %s/->%s/', self.cwd, path)
      self.cwd = path

  def getterminal(self):
    " return leading terminal of this session "
    return self.terminal

  def write (self, data):
    """
    write data to output and resume buffer. When a cls sequence occurs,
    flush the resume buffer. The output buffer is flushed on oflush()
    """
    if self.recording and data is not None:
      self.buffer['record'].append ((time.time(), data))
    self.buffer['output'].write(data.decode('iso8859-1'))
    self.buffer['resume'].write(data)

    last_cls = data.rfind(self.getterminal().clear.encode('iso8859-1'))
    if last_cls != -1:
      # cls in output, reset resume buffer to cls sequence onwards
      self.reset_resumebuffer (data[last_cls:])

  def reset_resumebuffer(self, data=''):
    " Clear resume buffer. and set contents to value of data "
    self.buffer['resume'].close()
    self.buffer['resume'] = StringIO.StringIO()
    self.buffer['resume'].write (data)

  def oflush (self):
    " write buffered output to socket. "
    self.getterminal().stream.write \
        (self.buffer['output'].getvalue())
    self.buffer['output'].close()
    self.buffer['output'] = StringIO.StringIO()

  def flush_event (self, event='input', timeout=-1):
    " for 'event', throw away all data waiting in event buffer "
    data = 1
    while event is not None and data is not None:
      event, data = self.read_event([event], timeout=timeout)

  def iflush(self):
    " throw away input "
    self.flush_event (event='input')

  def event_pop(self, event='input'):
    """
    retrieve first event item from front of specified event buffer.
    then, delete the foremost column of data.
    finally, return the stored value.
    """
    store = self.buffer[event][0]
    self.buffer[event] = self.buffer[event][1:]
    return store

  def buffer_event (self, event, data):
    " push event data into event buffer "
    if not self.buffer.has_key(event):
      self.buffer[event] = list()
    if event == 'input':
      # process multi-byte sequences into keycodes / keystrokes
      map(self.buffer[event].append, self.getterminal().trans_input(data))
    else:
      self.buffer[event].append (data)

  def send_event (self, event, data):
    self.pipe.send ((event, data))

  def read_event (self, events, timeout=None):
    """
    handle retrieving events from self.pipe.  Return value is in the form
    of a tuple as (event, data).  Always available is the 'input' event for
    keyboard input. A timeout of None waits indefintely, otherwise when defined,
    (None, None) may be returned when all events iterated in order of priority
    have been exausted within the time specified. fe.,
    event, data = read_event(events=['input','newmail'])
    if event == 'input':
    process_keystroke (data)
    elif event == 'newmail':
    status (bel + 'new mail has arrived!')
    """

    self.oflush ()

    # no matter the timeout, if data is available in
    # the buffer, immediately pop data
    for event in events:
      if event in self.buffer and 0 != len(self.buffer[event]):
        return (event, self.event_pop(event))

    t = time.time()
    event, data = None, None
    timeleft = lambda t: \
        float('inf') if timeout is None \
        else timeout -time.time() -t
    waitfor = timeleft(t)
    while waitfor > 0:
      if self.pipe.poll (None if waitfor == float('inf') else waitfor):
        event, data = self.pipe.recv()

        if event == 'connectionclosed':
          raise exception.ConnectionClosed(data)

        # buffer data received. data can be any size, such as a multibyte
        # input sequence, or a chunk of output data
        self.buffer_event (event, data)

        # when an event has just been buffered that is of an event specified
        # in the events=[] list, immediately pop the first column of data stored
        # in the buffer and return. For instance, a single keystroke
        if event in events:
          return (event, self.event_pop(event))

      # when the event recieved is not buffered and the event specified in
      # the events=[] list has not returned, then return (None, None) to
      # indicate that all buffers specified are flushed.
      if timeout == -1:
        return (None, None)
      waitfor = timeleft(t)
    return (None, None)

  def runscript(self, script, *args):
    """
      execute module's .main() function with optional *args as arguments.
    """
    import bbs
    global scripts
    cs = (script,) + args
    logger.info ('runscript(%r)', cs)

    self.current_script.append (cs)
    try:
      self.script_name, self.script_filepath \
          = scripting.chkmodpath (script, self.cwd)
    except LookupError, e:
      raise exception.ScriptError, e

    if not os.path.dirname(self.script_filepath) in sys.path:
      sys.path.append (os.path.dirname(self.script_filepath))

    scripts[self.script_name] = scripting.load(self.cwd, self.script_name)
    for idx in bbs.__all__:
      setattr(scripts[self.script_name], idx, getattr(bbs, idx))

    assert hasattr(scripts[self.script_name], 'main'), \
        "%s: main() not found." % (self.script_name,)
    assert callable(scripts[self.script_name].main), \
        "%s: 'main' not callable" % (self.script_name,)

    # function pointer to main()
    f = scripts[self.script_name].main

    # which script 'path' should we revert to after script execution?
    # answer: our current one, or this scripts' path if we haven't
    # got a current one.
    current_path = os.path.dirname(self.script_filepath)
    prev_path = self.getcwd() if self.getcwd() else current_path
    self.setcwd (current_path)

    value = f(*args)

    # we were gosub()'d here and have returned value. .pop() the current
    # script off the stack and return with the script's return value.
    lastscript = self.current_script.pop()
    logger.debug ('%s popped from current_script, value=%s', lastscript, value)
    self.setcwd (prev_path) # return to previous path
    return value
