"""
Scripting and session engine for 'The Progressive' BBS.
"""
__author__ = 'Johannes Lundberg <johannes.lundberg@gmail.com>'
__copyright__ = 'Copyright (C) 2005, 2008 Johannes Lundberg'
__license__ = 'Public Domain'
__version__ = '$Id: engine.py,v 1.50 2010/01/06 19:54:04 jojo Exp $'

# 3rd party modules (dependencies)
from twisted.internet import reactor
from twisted.python import threadable

# python modules
import threading as threading
import traceback as traceback
from StringIO import StringIO
import exceptions
import os.path
import thread
import string
import Queue
import time
import imp
import sys
import os

# prsv modules
import db
import log
import ansi
import keys
import session
import strutils
import fileutils
import exception

import terminal
import telnet
import ssh
import local
import finger

def SID():
  " @returns: calling thread's active session id "
  global threadslist
  return threadslist[thread.get_ident()]

def registersession(session):
  """
  Register a new session in the global lists sessionlist[] and threadlist[].
  @param session: An instance of the L{Session} class.
  """
  global slock, threadslist, sessionlist, caller
  slock.acquire()
  caller += 1
  threadslist[thread.get_ident()] = caller
  sessionlist[caller] = session
  sessionlist[caller].sid = caller
  slock.release()

def deletesid(sid):
  """
  Unregister a session, removing from the global lists sessionlist[] and threadlist[].
  @param sid: session key as used in sessionlist[] or returned from L{SID}.
  """
  log.write('engine','deleting sid %i' % (sid,))
  slock.acquire()
  del threadslist[thread.get_ident()]
  del sessionlist[sid]
  slock.release()

def getsession(sid=None):
  """
  @param sid: a session id key in sessionlist[]. If no key is passed, the key
  for the current session is identified using L{SID}.
  @returns: a handle to a Session instance, stored in the global sessionlist[]
  by key sid
  """
  if not sid:
    sid = SID()
  try:
    return sessionlist[sid]
  except exceptions.KeyError:
    log.write ('!!', 'No such session %s in sessionlist' % (sid,))
    return None

def main():
  """
  PRSV main entry point. The system begins and ends here.

  The following global variables are exported:
  - scriptlist: A dictionary of bbs-local scripts loaded into memory, keyed
    by their bbs-relative path
  - threadslist: A reverse-lookup of sessionlist, threadslist is keyed by
    the thread id of the thread that initialized the session.
  - sessionlist: A dictionary of session instances, keyed by caller
  - caller: a unique autonumber key that begins here as 0, incremented on each
    new session created, essentially becoming a call # since bbs executed.
  - slock: A safe lock object for manipulating sessionlist and threadlist

  @todo: main thread/engine becomes session that can send and recieve events,
  becoming a fully scriptable WFC screen.
  """
  global sessionlist, threadslist, slock, caller

  # initialize the database subsystem
  db.openDB ()

  # Thread -> SessionID dictionary
  threadslist = {}

  # Sessions by SessionID
  sessionlist = {}

  # Initialize script cache, preload with bbs.py
  scriptinit ()

  # increments on each call, doubles as sessionid
  caller = 0

  # aquire session<->thread lock
  slock = threading.Lock()

  for ttyname in db.cfg.local_ttys:
    term = local.LocalTerminal(ttyname)
    reactor.addReader (term)
    log.write ('tty%s' % (term.tty,), '%s terminal on %s' \
      % (term.type, term.info,))

  if db.cfg.local_wfc:
    term = local.LocalTerminal(db.cfg.local_wfc, db.cfg.wfcscript)
    reactor.addReader (term)
    log.write ('tty%s' % (term.tty,), '%s terminal on %s for %s' % \
      (term.type, term.info, db.cfg.local_wfc,))

  # TODO: if /dev/tty isn't attached to any lines, fork as a daemon and exit

  telnetFactory = telnet.TelnetFactory()
  for port in db.cfg.telnet_ports:
    reactor.listenTCP (port, telnetFactory)
    log.write ('telnet', 'listening on tcp port %s' % (port,))

  # XXX: We need to inject the sessionlist into the finger factory
  fingerFactory = finger.FingerFactory(sessionlist)
  if db.cfg.finger_port:
    reactor.listenTCP (db.cfg.finger_port, fingerFactory)
    log.write ('finger', 'listening on tcp port %s' % (db.cfg.finger_port,))

  if len(db.cfg.ssh_ports):
    try:
      db.cfg.ssh_hostkey_public
      db.cfg.ssh_hostkey_private
    except KeyError:
      log.write ('ssh', 'Generating new host keys. This may take a while.')
      if db.cfg.ssh_keytype == 'RSA':
        key = ssh.RSA.generate(db.cfg.ssh_keybits, ssh.secureRandom)
      elif db.cfg.ssh_keytype == 'DSA':
        key = ssh.DSA.generate(db.cfg.ssh_keybits, ssh.secureRandom)
      else:
        raise ValueError, 'Unknown key type: %r in db.cfg.ssh_keytype' % (db.cfg.ssh_keytype)
      db.cfg.ssh_hostkey_public = ssh.makePublicKeyString(key, comment='X/84 BBS')
      db.cfg.ssh_hostkey_private = ssh.makePrivateKeyString(key, comment='')

    sshFactory = ssh.SSHFactory()
    for port in db.cfg.ssh_ports:
      reactor.listenTCP (port, sshFactory)
      log.write ('ssh', 'listening on tcp port %s' % (port))

  reactor.run ()
  # the bbs ends here
  db.close ()

def scriptinit():
  """
  Initialize the global scriptlist[], a cache store for run-time imports,
  reloading, dependencies, and sharing. By sharing scripts in this way,
  users may communicate across global variables, and share memory regions.
  It is recommended, however, to use the database subsystem to share large
  data segments, and the event subsystem to communicate across threads.
  """
  global scriptlist
  # Scripts and modules cache
  scriptlist = {}

  # load global bbs.py into scriptlist
  scriptimport ('bbs', False, *imp.find_module('bbs'))
  loadscript ('bbs')
  populatescript ('bbs')

def scriptimport(name, asDependancy, file, filename, desc=('.py','U',imp.PY_SOURCE)):
  """
  This function is a wrapper for imp.load_module. Arguments C{name}, C{file},
  C{filename}, and C{desc} is given information returned by find_module(), just
  as imp.load_module. See L{scriptinit} for an example.

  @param asDependancy: This argument, when True, signifies that this script
  import is a refresh of an existing script, that may be a dependancy (as specified
  by the C{deps[]} list of said script) to other scripts that may require their
  imported namespace of said script to be refreshed.

  @todo: need to cache deps[] variable if script is refreshed, before refresh,
  and if this list changes after refresh, re-populate script.
  """
  log.write ('engine', 'importing %s' % (name,))
  script = imp.load_module(name, file, filename, desc)
  script._name     = name
  script._filename = filename
  script._filedate = os.path.getmtime (filename)
  script._loadtime = time.time()
  scriptlist[name] = script

  if not asDependancy:
    return

  # if this script was previously loaded in memory, all other scripts
  # that refer to this as a dependency in deps[] needs to have this
  # script repopulated into its namespace

  # fresh up in-memory copy
  scriptlist[name] = script

  for tgtscript in [key for key in scriptlist.keys() if key != name]:
    # iterate each target script except for ourselves
    if isDependancyOf(tgtscript, name):
      log.write (name, 'needs import of %s' % (tgtscript))
      populatescript(tgtscript, loadonly_dep=name)

def isDependancyOf(script, dep):
  """
  @param script: Script to check for dependencies.
  @param dep: Dependency to check for in Script.
  @returns: True if script lists dep as a dependency.
  """
  try:
    scriptdeps = getattr(scriptlist[script], 'deps')
  except AttributeError:
    # no dependencies
    return False

  for chkdep in scriptdeps:
    # retrieve normalized path of dependency
    _deppath = chkdep.replace('.', os.path.sep)
    chkdepname, _filepath = chkmodpath(chkdep, parent=os.path.dirname(_deppath))
    if dep == chkdepname:
      return True
  return False

def populatescript(name, loadonly_dep=None):
  """
  Ensure all globals are populated into the target script's global namespace.

  Load only the namespace of module defined as 'loadonly_dep' into target
  script 'name', when defined.

  Populate target script with all values and functions from bbs.py, except
  those that begin with C{'_'}.

  Then, retrieve script attribute C{deps}, of type list or tuple, and return
  immediately if not available. Otherwise, insert all globals from each
  dependency from the matching module defined by target scripts 'deps'
  variable.
  """
  global scriptlist

  if loadonly_dep:
    deps = [loadonly_dep]
  else:
    try:
      # retrieve from memory
      deps = getattr(scriptlist[name], 'deps')
    except AttributeError:
      # script is without dependencies
      return

  for depname in deps:
    try:
      depname, filepath = chkmodpath(depname, parent=os.path.dirname(name))
    except LookupError:
      log.write ('!!', 'Failed to locate %s for %s' % depname, name)
      continue

    if depname == name:
      log.write ('!!', '%s depends on itself!' (name))
      # avoid circular dependencies
      continue
    status = checkscript(depname)
    if status == -1:
      log.write ('!!', 'Failed to load dependency %s for %s' % (depname, name))
      continue
    source = scriptlist[depname]
    # copy all attributes into another's
    # global space 'deps' and 'init'
    keys=[k for k in dir(scriptlist[depname]) \
          if not k.startswith('_') \
          and not k in ['deps','init']]
    target = scriptlist[name]
    for key in keys:
      setattr (target, key, getattr(source, key))

def chkmodpath(name, parent):
  """
  return tuple (modpath, filepath), for module named by 'name'.
  """

  cur = os.path.curdir
  if parent.startswith (cur):
    parent = parent[len(cur):]

  name = name.replace('.', os.path.sep)

  # absolute path
  if parent.startswith (os.path.sep):
    name_a = os.path.join(parent, name)
    path_a = name_a + '.py'
    if os.path.exists (path_a):
      return (name_a, path_a)

  # as-is (path/X.py)
  name_r = os.path.join(parent, name)
  path_r = name_r + '.py'

  if not os.path.exists(path_r):
    # script-path relative
    name_l = os.path.join(db.cfg.scriptpath, name)
    path_l = name_l + '.py'

    if not os.path.exists(path_l):
      # kernel-path relative (./path/name.py)
      name_g = os.path.join(os.path.join(os.path.curdir, parent), name)
      path_g = name + '.py'
      if not os.path.exists(path_g):
          log.write ('!!', ' chkmodpath(name=%s, parent=%s): filepath not found:' % (name, parent))
          log.write ('!!', ' script relative: %s' % path_r)
          log.write ('!!', '      scriptpath: %s' % path_l)
          log.write ('!!', '      kernelpath: %s' % path_g)
          raise LookupError, 'filepath not found: "%s"' % name
      else:
        return name, path_g
    else:
      return name_l, path_l
  else:
    return name_r, path_r

def loadscript(name, asDependancy=False):
  """
  load script specified by module relative to script path, and populate
  its' global namespace with contents of modules defined in list 'deps'.
  If script contains init() function, also execute that.
  """
  global scriptlist

  sessionpath = fileutils.abspath ()
  name, path = chkmodpath(name, sessionpath)

  if not os.path.abspath(os.path.dirname(path)) in sys.path:
    #log.write ('engine', 'Prepend to environment path: %s' \
    #  % os.path.abspath(os.path.dirname(path)))
    # push target module's directory into front of environment path
    sys.path.insert (0, os.path.abspath(os.path.dirname(path)))

  try:
    scriptimport (name, asDependancy, *imp.find_module(name.split(os.path.sep)[-1]))
  except ImportError:
    log.tb (*sys.exc_info())
    log.write ('!!', 'Failed to import script at:')
    log.write ('!!', '     Python path: %s' % name)
    log.write ('!!', '       File path: %s' % path)
    log.write ('!!', '    Session path: %s' % sessionpath)
    log.write ('!!', '  Engine curpath: %s' % os.path.abspath(os.path.curdir))
    return False

  # load in script dependencies, specified by global deps=['module.name']
  populatescript (name)

  init = None
  try:
    init = getattr(scriptlist[name],'init')
  except AttributeError:
    pass

  if init:
    # Run init() function of script on import, if available
    log.write ('engine', '%s:init()' % (name,))
    init()
  return True

def scriptlastmodified(name):
  path = name.replace('.', os.path.sep) + '.py'
  if not os.path.exists(path):
    path = os.path.join(db.cfg.scriptpath, path)
  if not os.path.exists(path):
    log.write ('!!', 'exausted path search for module %s.' % name)
    return 0
  try:
    return os.path.getmtime (path)
  except OSError:
    log.write ('!!', 'failed to retrieve mtime for path %s.' % path)
    return 0

def chkglobals():
  """
  ensure globals and engine pieces are loaded, failing over to swapped
  copies on failure with a stern warning. (thats the idea, anyway)
  """

  if not 'bbs' in scriptlist:
    scriptinit ()

  bbs_swap = scriptlist['bbs']

  lastmodified = scriptlastmodified('bbs')
  if lastmodified > scriptlist['bbs']._loadtime:
    log.write ('u:'+getsession().handle, 'reload bbs.py, modified %s ago.' \
      % (strutils.asctime(time.time() -lastmodified),))
    try:
      scriptinit ()
    except:
      # exception raised because a failure occured loading the new bbs script
      log.write ('!!', 'bbs.py reload failed')
      log.tb (*sys.exc_info())
      log.write ('>>', 'File: "./bbs.py"')
      log.write ('!!', 'bbs.py reload failed, reverting to swap')
      scriptlist['bbs'] = bbs_swap
      return False
  return True

def checkscript(name, forcereload=False):
  """
  Firstly, check if bbs.py requires reload, and do so.
  Then, reload specified script into memory under any of the following
  conditions:
    - bbs.py has been reloaded.
    - file has been modified since last run.
    - any of its' dependencies require reload.
  Then, return a value signifying the status of the script checked:
    - return >0 if the above conditions applied and caused a reload,
      returning the number of modules and scripts reloaded.
    - return 0 when script did not require reloading.
    - return -1 when not sucessfully loaded.

  This function is recursive.
  """
  global scriptlist

  # number of scripts and dependencies reloaded (return value)
  loaded = 0

  if not chkglobals ():
    log.write ('!!', "chckglobals failed, we're on fire!")
    return -1

  try:
    name, path = chkmodpath (name, fileutils.abspath())
  except LookupError:
    return -1

  if not forcereload and scriptlist.has_key(name) \
  and hasattr(scriptlist[name],'deps'):
    for depname in getattr(scriptlist[name], 'deps'):
      if depname == name:
        # avoid circular recursion
        continue
      # force reload of this script if any dependencies required refresh
      if checkscript(depname) > 0:
        #log.write ('engine', "[%s]: checkscript(): script '%s' dependency calls for refresh" % (session.handle, depname))
        forcereload = True
        loaded += 1

  if not forcereload and not scriptlist.has_key(name):
    #log.write ('engine', "[%s]: checkscript(): script '%s' first load." % (session.handle, name))
    forcereload = True

  asDependancy = False
  if not forcereload and scriptlastmodified(name) > scriptlist[name]._filedate:
    log.write ('engine', "checkscript(): script '%s' modified %s ago. refresh." \
      % (name, strutils.asctime(time.time()-scriptlastmodified(name))))
    forcereload = True
    asDependancy = True

  if forcereload:
    if not loadscript (name, asDependancy):
      return -1
    loaded += 1

  return loaded

#
## Session handling
#

def destroysessions():
  " destroy all sessions "
  for key in sessionlist.keys():
    sessionlist[key].event_push ('connectionclosed', 'destroysessions()')

def sendevent(sid, event, data):
  " send an event do a session "
  sessionlist[sid].event_push (event, data)

def broadcastevent (event, data):
  " send event to all other sessions "

  sendto = []
  for sid in sessionlist.keys():
    if sid != SID():
      sendto.append (sid)

  log.write ('u:'+getsession().handle,
    'event %s broadcast to %s sessions: %s' \
      % (event, len(sendto), data,))

  for sid in sendto:
    sessionlist[sid].event_push (event, data)

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

    if the first value of .current_script is None, then db.cfg.matrixscript
    will be used.

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
      'output': StringIO(),
      'resume': StringIO(),
      'record': []
    }
    self.logintime, self.lastkeypress = time.time(), time.time()
    self.current_script = [(db.cfg.matrixscript,)]
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
    registersession (self)
    log.write('session', 'begin session %i, script stack: %s' \
      % (self.sid, self.current_script,))
    tryagain = True
    fallback_script = self.current_script
    while len(self.current_script):
      try:
        self.lastscript = self.current_script[-1]
        self.runscript (*self.current_script.pop())

        log.write ('u:'+self.handle, 'crashloop: recovery')
        if not self.current_script:
          log.write ('u:'+self.handle, 'falling back to %s' % (fallback_script,))
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
      except:
        # General exception, an error in script run-time
        log.write ('u:'+self.handle, 'raised general exception in %s' % (self.lastscript,))
        log.tb (*sys.exc_info())
        if len(self.current_script):
          log.write ('u:'+self.handle, 'pop %s' % (self.current_script.pop(),))
          continue
        else:
          log.write ('u:'+self.handle, 'No scripts remain in stack')
          break
    broadcastevent ('global', '%s disconnected' % (self.handle,))
    terminals = [t for t in self.terminals]
    for t in terminals:
      t.destroy ()
    deletesid (SID())

  def start (self, handle=None, script=None):
    """
    Called from Terminal::addsession(), this begins the script execution
    loop for the session via a call to the global sessionmain() function.

    When handle is passed, the default matrix script is bypassed, jumping
    directly to topscript (passing handle as first argument). This occurs
    when the terminal has already handled authentication, such as ssh.
    """
    if not script:
      script=db.cfg.matrixscript

    if not handle:
      # set script path
      self.current_script = [(script, )]
    else:
      # set script stack to include handle as argument
      self.current_script = [(script, handle)]

    reactor.callInThread (self.sessionmain)

  def setWindowSize(self, w, h):
    log.write ('u:'+self.handle,'Set window size: %sx%s' % (w, h,))
    self.width, self.height = (w, h)
    self.event_push ('refresh', ((w, h)))

  def setTermType(self, TERM):
    log.write ('u:'+self.handle,'Set terminal type: %s' % (TERM,))
    self.TERM = TERM

  def setuser(self, user, recordLogin=True):
    " set session's user object "
    self.user = user
    self.handle = user.handle
    if recordLogin:
      self.logintime = time.time()

  def setpath(self, path):
    if self.path != path:
      log.write ('u:'+self.handle, 'userland path change %s/->%s/' % (self.path, path))
      self.path = path

  def detachterminal (self, term):
    " dissasociate terminal from this session "
    log.write ('tty%s' % (term.tty,), \
      'dissasociate terminal from session %i' % (self.sid))
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
      log.write ('tty%s' % (term.tty,),
        'start new session on %s terminal %s' \
          % (term.type, term.info))
    else:
      log.write ('tty%s' % (term.tty,),
        'attaching %s terminal %s to session %i' \
        % (term.type, term.info, self.sid))

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
    self.buffer['resume'] = StringIO()
    self.buffer['resume'].write (newdata)

  def oflush (self):
    " write buffered output to socket and return number of characters written. "
    output = self.buffer['output'].getvalue()
    if output:
      [term.write (output) for term in self.terminals]
    self.buffer['output'].close()
    self.buffer['output'] = StringIO()
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
    self.buffer[event] = strutils.remove(self.buffer[event], column=0, n=1)
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
        log.write ('!!', 'eventqueue %s full' % event)
        log.write ('>>', 'flushing for %ss before retry.' % period)
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

  def runscript(self, script, *args):
    """
      execute module's .main() function with optional *args as arguments.
      if script is None, then the matrixscript is used more or less as a
      reset or init switch
    """
    global scriptlist

    if not script:
      script = db.cfg.matrixscript

    log.write ('u:'+self.handle, 'exec %s, args: %s' % (script, args))

    # break script into an informal and formal path, add
    # to our script stack .current_script, then check the
    # import status of the script and re-load if necessary
    self.script_name, self.script_filepath = chkmodpath (script, self.path)
    self.current_script.append ((script,) + args)
    # XXX check return status?
    checkscript (self.script_name)

    # the script, after being loaded, should contain a 'main'
    # function, seen here as an attribute of the imported script
    try:
      deps = getattr(scriptlist[self.script_name], 'main')
    except AttributeError:
      log.write (self.script_name, 'main definition not found in %s (%s)' \
        % (self.script_filepath))

      raise
    try:
      f = scriptlist[self.script_name].main
    except:
      log.write (self.script_name, 'Error on import of main(), filepath:' \
        % (self.script_filepath,))
      log.tb (*sys.exc_info())
      raise

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
      log.write ('u:'+self.handle, "pop %s: %s" % (lastscript, value))
      self.setpath (path_swap) # return to previous path
      return value

    except exception.ScriptChange, e:
      # bbs.goto() exception
      #
      # raise exception up to self.sessionmain() with new target
      # script as value of exception, effectively acting as a GOTO
      # statement.
      log.write ('u:'+self.handle, "%s goto %s" % (self.script_name, e))
      raise

    except exception.ConnectionClosed:
      # client connection closed, raise up
      type, value, tb = sys.exc_info ()
      log.write ('u:'+self.handle, "Connection closed: %s" % (value,))
      self.setpath (path_swap) # return to previous path
      raise

    except exception.MyException:
      # Custom exception
      type, value, tb = sys.exc_info ()
      self.setpath (path_swap) # return to previous path
      raise
