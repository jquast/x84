import threading, thread, Queue, StringIO, time, sys, os, logging, traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from twisted.internet import reactor # wha!
import db,log,exception # yech
import scripting # runscript
import ansi # cls lol

class SessionRegistry(dict):
  caller = 0

  def __init__(self):
    self.lock = threading.Lock()
    dict.__init__(self)

  def register(self, session):
    """ Create new unique session id (call #), and store the Session
        instance, registered by the calling thread's id.
    """
    self.lock.acquire()
    self.caller += 1
    session.sid = self.caller
    session.thread_id = thread.get_ident()
    self[self.caller] = session
    self.lock.release ()
    return self.caller

  def getsession(self, sid=None):
    """
    @param sid: session id. The current session is returned when None (default).
    @returns: Session instance
    """
    return self[sid if sid != None else self.get_ident()]

  def get_ident(self, thread_id=None):
    """
    @param thread_id: a thread id as returned from thread.get_ident(),
      otherwise the current threads id is used (default).
    @returns: session id
    """
    thread_id = thread_id if thread_id is not None else thread.get_ident()
    for sid, session in self.iteritems():
      if thread_id == session.thread_id:
        return sid
    raise KeyError

  def unregister(self, sid=None):
    sid = sid if sid is not None else self.get_ident()
    self.lock.acquire()
    del self[sid]
    self.lock.release ()

class Session:
  def __init__ (self, terminal=None):
    """
    .eventqueue is a queue for event data, which includes user input,
    program IPC, and broadcasted data. Data is retrieved from the queue
    in readevent().

    .terminals is a list of Terminal instances

    i/o buffers are 'input', 'output', and 'resume'. output and resume
    buffers are memory files using StringIO(). 'output' buffers screen data
    sent to socket until an event is read or it is explicitly flush()'ed.
    'resume' however, stores its data idefinitely until a cls() sequences
    is inserted, then it is reset. This 'resume' buffer is used for
    playback when another terminal is attached to this session through the
    attachterminal() procedure.

    additionaly, the flag .recording=True can be set to farm all screen
    output in a list of tuples of (time, characters) that can be played
    back

    .handle is [unknown] until authenticated, activity is [unknown] until
    explicitly set in scripts. .logintime and .lastkeypress are for time
    measurements of the elapsed time since connection and keypress, for
    use in last callers, or in .idletime().

    .current_script is stored as a tuple, first value is the script path,
    and remaining are function arguments passed to main(*args) during the
    runscript() procedure.

    if the first value of .current_script is None, then
    db.cfg.get('system','matrixscript') will be used.

    use .path to track the filesystem location of current script, so that
    directory helper functions in fileutils.py remain relative.

    when .persistent is True, sessions that are disconnect unexpectedly
    have their session instance reserved in memory, so that it may be
    resumed to later, or attached to by another party. typically,
    persistent stays False until a user has authenticated. this shouldn't
    be necessary for local lines, but is critical for network lines.
    """
    self.sid = -1
    self.handle, self.activity = '', ''
    # last script called for error reporting
    self.last_script = None
    # our current path for script lookup
    self.path = ''
    # wether or not our session dies when last terminal closes
    self.persistent = False
    # for input keymap handling in Terminal::handleinput(),
    # change with .setTermType
    self.TERM = 'unknown'
    # terminal height and width, change with .setWindowSize
    self.width, self.height = (80, 24)
    # list of terminals attached to this session
    self.terminals = []
    # set recording=True to record session to self.buffer['record']
    self.recording = False
    self.eventqueue = Queue.Queue(0)
    self.buffer = {
      'input': '',
      'output': StringIO.StringIO(),
      'resume': StringIO.StringIO(),
      'record': []
    }
    self.logintime, self.lastkeypress = time.time(), time.time()
    self.current_script = [(db.cfg.get('system','matrixscript'),)]
    if terminal:
      self.attachterminal(terminal)

  def sessionmain(self):
    """
    The main script execution loop for a session handles the
    movement of the client users throughout userland via calls to
    runscript(). The client scripts, however, make use goto()
    which causes the ScriptChange exception to be raised and handled
    here, or by bypassing us through a gosub() function which too
    calls runscript(), via engine.getsession().runscript()
    """
    self.lastscript = None
    sessions.register (self)
    logger.info ('Call #%i, script stack: %r', self.sid, self.current_script,)
    tryagain = True
    fallback_script = self.current_script
    while len(self.current_script):
      try:
        self.lastscript = self.current_script[-1]
        self.runscript (*self.current_script.pop())

        logger.warn ('crashloop: recovery <Session.runscript(%r)>' \
            % (self.lastscript,))
        if not self.current_script:
          logger.error ('current_script = <fallback_script: %r>', \
              fallback_script)
          self.current_script = fallback_script
      except exception.ScriptChange, sc:
        # change script (goto), no prior script to return from!
        self.current_script = [sc.value]
        continue
      except exception.Disconnect, e:
        # disconnect
        break
      except exception.ConnectionClosed, e:
        # closed connection
        break
      except exception.SilentTermination, e:
        # request for silent termination
        break
      except LookupError, e:
        # a scriptpath or module was not found in lookup,
        # error already emitted.
        continue
      except Exception, e:
        #        print self.lastscript + '<'*30
        script_name, script_filepath = scripting.chkmodpath \
            (self.lastscript[0], self.path)
        t, v, tb= sys.exc_info()
        for lc,l in enumerate(traceback.format_exception_only(t, v)):
          if lc == 0:
            logger.error ("Exception raised in '%s': %s",
              script_filepath,l.rstrip())
          else:
            logger.error (l.rstrip())
        map(logger.error, [l.rstrip() for l in traceback.format_tb(tb)])
        if len(self.current_script):
          logger.warn ('continue after current_script.pop(): %s',
              self.current_script.pop())
          continue
        else:
          logger.error ('no scripts remain in stack')
          break
    #broadcastevent ('global', '%s disconnected' % (self.handle,))
    terminals = [t for t in self.terminals]
    for t in terminals:
      t.destroy ()
    sessions.unregister()

  def start (self, handle=None, script=None):
    """
    Called from Terminal::addsession(), this begins the script execution
    loop for the session via a call to the global sessionmain() function.

    When handle is passed, the default matrix script is bypassed, jumping
    directly to topscript (passing handle as first argument). This occurs
    when the terminal has already handled authentication, such as ssh.
    """
    if not script:
      script=db.cfg.get('system','matrixscript')

    if not handle:
      # set script path
      self.current_script = [(script, )]
    else:
      # set script stack to include handle as argument
      self.current_script = [(script, handle)]

    reactor.callInThread (self.sessionmain)

  def setWindowSize(self, w, h):
    logger.debug ('window size: (w=%s,h=%s)', w, h)
    self.width, self.height = (w, h)
    self.event_push ('refresh', ((w, h)))

  def setTermType(self, TERM):
    logger.debug ('terminal type: (TERM=%s)', TERM)
    self.TERM = TERM

  def setuser(self, user, recordLogin=True):
    " set session's user object "
    self.user = user
    self.handle = user.handle
    if recordLogin:
      self.logintime = time.time()

  def setpath(self, path):
    if self.path != path:
      logger.info ('userland path change %s/->%s/', self.path, path)
      self.path = path

  def detachterminal (self, term):
    " dissasociate terminal from this session "
    logger.info ('[tty%s] dissasociate terminal from caller #%i', term.tty, self.sid)
    if term in self.terminals:
      self.terminals.remove (term)

  def attachterminal (self, term, spy=None):
    """
    associate terminal with this session, playing resume buffer as necessary,
    optional argument spy may be set to indicate which user handle has
    attached to this session
    """
    self.terminals.append (term)
    term.spy = spy
    if self.sid == -1:
      logger.info ('[tty%s] start new session term.(type=%s, info=%s)',
        term.tty, term.type, term.info)
    else:
      logger.info ('[tty%s] terminal joins session %i: term.(type=%s, info=%s)',
        term.tty, self.sid, term.type, term.info)

    # set parent session of new terminal
    term.xSession = self
    term.attachtime = time.time()

    # write resume buffer to hijacker's terminal output,
    # contents are screen playback since last cls()
    term.write (self.buffer['resume'].getvalue())

  def write (self, string):
    """
    write data to output and resume buffer. When a cls sequence occurs,
    flush the resume buffer. The output buffer is flushed on oflush()
    """
    if self.recording:
      self.buffer['record'].append ((time.time(), string))
    self.buffer['output'].write(string)
    self.buffer['resume'].write(string)
    last_cls = string.rfind(ansi.cls())
    if last_cls != -1:
      # cls in output, reset resume buffer to cls sequence onwards
      self.reset_resumebuffer (string[last_cls:])

  def reset_resumebuffer(self, newdata=''):
    " Clear resume buffer. and set contents to value of newdata "
    self.buffer['resume'].close()
    self.buffer['resume'] = StringIO.StringIO()
    self.buffer['resume'].write (newdata)

  def oflush (self):
    " write buffered output to socket and return number of characters written. "
    output = self.buffer['output'].getvalue()
    if output:
      [term.write (output) for term in self.terminals]
    self.buffer['output'].close()
    self.buffer['output'] = StringIO.StringIO()
    return output

  def flushevent (self, event='input', timeout=-1):
    " for 'event', throw away all data waiting in event buffer "
    data = 1
    while event and data:
      event, data = self.readevent([event], timeout=timeout)

  def iflush(self):
    " throw away input "
    self.flushevent ()

  def idle(self):
    " return number of seconds since last keypress "
    return time.time() - self.lastkeypress

  def event_pop(self, event='input'):
    """
    retrieve first event item from front of specified event buffer.
    then, delete the foremost column of data.
    finally, return the stored value.
    """
    store = self.buffer[event][0]
    self.buffer[event] = self.buffer[event][1:]
    return store

  def bufferevent (self, event, object):
    " push event data into event buffer "
    if event == 'input':
      self.buffer[event] += object
      self.lastkeypress = time.time()
    else:
      if not self.buffer.has_key(event):
        # dynamicly create new buffer as list
        self.buffer[event] = []
      self.buffer[event].append (object)

  def event_push (self, event, object, timeout=10, period=1):
    """
    store data specified as 'object' into top (front) of the event buffer
    specified by event=. for small queues, specify the timeout= in seconds
    until retries, intervaled by value of period=, have been exausted for a
    full queue.
    """
    start = time.time()
    while True:
      try:
        self.eventqueue.put_nowait ((event, object))
        return True
      except Queue.Full:
        logger.error ('eventqueue full!')
        logger.warn ('flushing %ss before retry.',  period)
        self.flushevent (event, timeout=period)
        continue
      if time.time() -start < timeout:
        return False
  putevent = event_push

  def readevent (self, events, timeout=None):
    """
    handle retrieving events from self.eventqueue.  Return value is in the form
    of a tuple as (event, data).  Always available is the 'input' event for
    keyboard input. A timeout of None waits indefintely, otherwise when defined,
    (None, None) may be returned when all events iterated in order of priority
    have been exausted within the time specified. fe.,
    event, data = readevent(events=['input','newmail'])
    if event == 'input':
    process_keystroke (data)
    elif event == 'newmail':
    status (bel + 'new mail has arrived!')
    """

    self.oflush ()

    # no matter the timeout, if data is available in
    # the buffer, immediately pop data
    for event in events:
      if self.buffer.has_key(event) \
      and len(self.buffer[event]):
        data = self.event_pop(event)
        return (event, data)

    start = time.time()
    waitfor = timeout
    event, data = None, None

    while 1:
      # pop event off queue
      if timeout == -1:
        # non-blocking. Queue.Empty raised when no data available.
        try:
          event, data = self.eventqueue.get (block=False)
        except Queue.Empty:
          event, data = None, None
      elif timeout != -1:
        # blocking. Queue.Empty raised when timeout is reached without input
        try:
          # XXX this may be blocking too hard, ^C wont respond
          # until a client types a key -jdq XXX
          event, data = self.eventqueue.get (block=True, timeout=waitfor)
        except Queue.Empty:
          return (None, None)

      if event == 'connectionclosed':
        raise exception.ConnectionClosed(data)

      if event and data:
        # buffer data received. data can be any size, such as a multibyte
        # input sequence, or a chunk of output data
        self.bufferevent (event, data)

      # when an event has just been buffered that is of an event specified
      # in the events=[] list, immediately pop the first column of data stored
      # in the buffer and return. For instance, a single keystroke for event 'input'
      if event in events:
        data = self.event_pop(event)
        return (event, data)

      # when the event recieved is not buffered and the event specified in
      # the events=[] list has not returned, then return (None, None) to
      # indicate that all buffers specified are flushed.
      if timeout == -1:
        return (None, None)

      if timeout != None:
        waitfor = timeout - (time.time() - start)
        if waitfor <= 0:
          return (None, None)
        continue

    return event, data

  def runscript(self, script=None, *args):
    """
      execute module's .main() function with optional *args as arguments.
      if script is None, then the matrixscript is used more or less as a
      reset or init switch
    """

    if not script:
      script = db.cfg.get('system', 'matrixscript')

    logger.info ('runscript(%r, **%r)', script, args)

    # break script into an informal and formal path, add
    # to our script stack .current_script, then check the
    # import status of the script and re-load if necessary
    self.script_name, self.script_filepath \
        = scripting.chkmodpath (script, self.path)

    self.current_script.append ((script,) + args)

    # XXX check return status?
    scripting.checkscript (self.script_name)

    # the script, after being loaded, should contain a 'main'
    # function, seen here as an attribute of the imported script
    try:
      deps = getattr(scripting.scriptlist[self.script_name], 'main')
    except AttributeError, e:
      logger.error ('script_name=%s, main definition not found: script_filepath=%s',
        self.script_name, self.script_path)
      raise AttributeError, e
    try:
      f = scripting.scriptlist[self.script_name].main
    except Exception, e:
      logger.error ('script_name=%s, main reference error: script_filepath=%s',
        self.script_name, self.script_path)
      logger.error ("make sure a 'def main():' statement exists in script for execution")
#      log.tb (*sys.exc_info())
      raise Exception, e

    if self.path:
      path_swap = self.path
    else:
      path_swap = (os.path.dirname(self.script_filepath))

    self.setpath (os.path.dirname(self.script_filepath))

    value = None
    try:
      value = f(*args)
      # we were gosub()'d here and have returned value. .pop() the current
      # script off the stack and return with the script's return value.
      lastscript = self.current_script.pop()
      logger.info ('%s popped from current_script, value=%s', lastscript, value)
      self.setpath (path_swap) # return to previous path
      return value

    except exception.ScriptChange, e:
      # bbs.goto() exception
      #
      # raise exception up to self.sessionmain() with new target
      # script as value of exception, effectively acting as a GOTO
      # statement.
      logger.info ('%s GOTO %s', self.script_name, e)
      raise exception.ScriptChange, e

    except exception.ConnectionClosed, e:
      # client connection closed, raise up
      type, value, tb = sys.exc_info ()
      logger.info ('Connection closed: %s', value)
      self.setpath (path_swap) # return to previous path
      raise exception.ConnectionClosed, e

    except exception.SilentTermination, e:
      # bbs.py:terminate()
      logger.info ('SilentTermination Exception raised')
      raise exception.SilentTermination, e

    except exception.MyException, e:
      # Custom exception
      type, value, tb = sys.exc_info ()
      logger.info ('MyException ? depricated XXX ? %s', value)
      self.setpath (path_swap) # return to previous path
      raise exception.MyException, e

# XXX WHAaaaa

sessions = SessionRegistry()

#class CurrentSession:
#  " Return caller's session"
#  def __call__ (self):
#    return sessions.getsession()
#  def __setattr__ (self, key, value):
#    setattr (sessions.getsession(), key, value)
#  def __getattr__ (self, key):
#    return getattr (sessions.getsession(), key)
#
#session = CurrentSession()
#
#class CurrentUser:
#  " Return caller's session.user"
#  def __call__ ():
#    return session.user
#  def __setattr__ (self, key, value):
#    setattr(session.user, key, value)
#  def __getattr__ (self, key):
#    return getattr (session.user, key)
#
#user = CurrentUser()

def destroysessions():
  " destroy all sessions "
  for sid, session in sessions.iteritems():
    session.event_push ('connectionclosed', 'destroysessions()')

def sendevent(sid, event, data):
  " send an event do a session "
  sessions.getsession(sid).event_push (event, data)

def broadcastevent (event, data):
  " send event to all other sessions "
  sid = sessions.get_ident()
  sendto = [id for id in sessions.iterkeys() if id != sid]
  logger.info ('[%s] broadcast event to %i sessions: %r',
    sessions.getsession().handle, len(sendto), data)
  for sid in sendto:
    sessions.getsession(sid).event_push (event, data)

