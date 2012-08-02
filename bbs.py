"""
Global functions for 'The Progressive' BBS.

This is the primary include point for script dependencies, use the line::

  deps = ['bbs']

In all client scripts to access the bbs engine.

@note: To make use of @db.locker, import db directly in client engine as well ...
"""
__copyright__ = 'Copyright (c) 2005 Johannes Lundberg.'
__author__ = 'Johannes Lundberg'
__license__ = 'Public Domain'
__version__ = '$Id: bbs.py,v 1.50 2010/01/02 00:54:26 dingo Exp $'

import time, logging, random
from time import time as timenow # legacy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

deps = [ \
  'db', 'session', 'exception', 'userbase', 'msgbase',
  'ascii', 'ansi', 'sauce', 'fileutils', 'strutils', 'keys',
  'ui.ansiwin', 'ui.pager', 'ui.leftright', 'ui.lightwin',
  'ui.editor']

#import engine
import log

def init():
  # No initialization routine on re-import
  None

##                             ##
# Script change and termination #
##                             ##

def disconnect():
  " disconnect calling session from bbs "
  raise Disconnect('disconnect')

def goto(*arg):
  """
  Jump to script without return.

  First argument is python script path, all arguments following
  script path become positional parameters to the main() function
  of target script.

  @note: If target script fails, there is no return and the session
    is terminated. This function should be used for only this very
    purpose, such as after a sucessfull login.
  """
  raise ScriptChange((arg[0],)+arg[1:])

def gosub(*arg):
  """
  Jump to script and return value.

  First argument is python script path, all arguments following
  script path become positional parameters to the main() function
  of target script.

  This function returns the return value from target script's
  main() when complete. Exceptions are also raised upwards, and
  can be trapped.
  """
  return getsession().runscript(*(arg[0],)+arg[1:])

##      ##
# Events #
##      ##

def sendevent(sid, event, data):
  """
  Place an event into target session's event queue.

  @param sid: session id of reciever
  @param event: tag of event, such as 'input'
  @param data: content of event, such as 'hijacked input'
  """
  return session.sendevent(sid, event, data)

def broadcastevent(event, data):
  """
  Place an event into all other session's eventqueue.

  @param event: tag of event, such as 'post'
  @param data: content event, such as ('new post by dingo', msg.number)
  """
  return session.broadcastevent(event, data)

def globalevent (data):
  """
  Place a public event into all other session's, tagged as 'global'.

  @param data: content event, such as "dingo posted message, 'Re: linux sucks'"
  """
  # TODO: also store into db
  broadcastevent (event='global', data=data)

def readevent(events=['input'], timeout=None):
  """
  Read for any waiting events tagged by paramater L{events}. Returns
  a tuple in the form of (event_tag, event_data). If the L{timeout}
  paramater is specified, and no events of tag L{events} are in the eventqueue,
  (None, None) is returned.
  """
  return getsession().readevent(events, timeout)

def globalevents (timeout=-1):
  """
  Read for any waiting global events. If no events tagged as 'global' are
  in the eventqueue, None is returned immediately. Otherwise, only the the
  data of the event is returned.
  """
  event, data = readevent(events=['global'], timeout=-1)
  if event: return data
  return None

def flushevent(event='input', timeout=-1):
  """
  Remove all events tagged as L{event} from session eventqueue.
  """
  return getsession().flushevent(event, timeout)

def flushevents(events=['input'], timeout=-1):
  """
  Remove all events tagged as L{event} from session eventqueue.
  """
  return [getsession().flushevent(event, timeout) for event in events]

##        ##
# Sessions #
##        ##

def getsession(sid=None):
  """
  return caller's Session instance. If L{sid} is specified, return session
  instance keyed by id L{sid}.
  """
  return session.sessions.getsession(sid)

def terminate():
  """
  Silently terminates caller's session, without killing terminals.

  This is used to disconnect the session from the engine, but
  does not kill any attached terminals, should they be re-used.

  This can be used to 'jump to' another session, that is, attaching
  to another session, while removing the current one.

  This is used in login.py in the 'resume session?' prompt, so
  that after login, a past session may resumed, while the session
  doing the attaching can silently disapear.
  """
  raise SilentTermination(None)

def sessionlist():
  " List all session instances "
  return sessions.values()

def attachsession(sid, spy=None, killCurrent=False):
  """
  All terminals attached to Caller's session are set detached, and reattached
  to the target session specified by L{sid}. If no session exists by that
  key, False is returned. Otherwise, True is returned.

  The variable spy is a string to identify the source of the attachment. It
  has only informational significance.

  When the variable L{killCurrent} is set, the calling session is completely
  removed. Otherwise, when the target session is removed (such as disconnect),
  the caller is returned to the session prior to attachment.
  """
  if sid in session.sessions:
    remote_session = session.getsession(sid)

    session = getsession()
    for number, term in enumerate(getsession().terminals):
      msg = '%s attaches to session %s owned by %s' \
        % (session.handle, remote_session.sid,
           remote_session.handle and remote_session.handle or '[ unauthenticated ]')
      globalevent (msg)

      if not killCurrent:
        # save session to resume to, when this terminal is destroyed
        term.resume_sessions.append (session.sid)

      # detach current terminal from local session
      session.detachterminal (term)

      # attach terminal to remote session
      remote_session.attachterminal (term, spy)

    if killCurrent:
      terminate ()
  else:
    return False
  return True

def handle():
  " return handle used by caller's session "
  return session.sessions.getsession().handle

##              ##
# Terminal Input #
##              ##

def getch(timeout=None):
  """
  Return data waiting in the 'input' event of the eventqueue.
  When timeout is defined, None is returned if timeout period has passed.
  Otherwise, block until a keyevent occurs.
  """
  event, data = readevent(['input'], timeout=timeout)
  return data

# XXX DEPRICATION
readkeyto = readkey = inkey = getch

def getstr(period=.25):
  """
  getstr is similar to getch, but retrieves strings. It works similarly using
  {period} as opposed to timeout in seconds, and a sequence of characters are
  expected to be recieved, with no more than L{period} seconds between each
  character.

  The only viable use for getstr() thus far is throwing away data sent by a
  terminal, often on connect. For instance, the SynchroTerm program sends
  'ANSI/152000', often confusing the user to find it in their 'login' field.
  """
  s = ''
  while True:
    k = getch(period)
    if not k:
      return s # timeout period reached without keystroke
    else:
      s += k # keystroke within period, append to sequence

##                ##
#  Terminal Output #
##                ##

def delay(seconds):
  """
  This function acts as a timer, flushing all screen output, and will not
  return until the number of seconds specified by L{seconds} has passed,
  often used for animations.
  """
  getsession().oflush ()
  session.readevent([], seconds)
sleep = delay

def oflush():
  " flush all data waiting in session output buffer "
  return getsession().oflush ()

def write(data):
  " write data to session output buffer "
  return getsession().write (data)

def echo(string, parse=True):
  """
  echo string to session output. If parameter L{string} is not of type
  string, it is converted to one via the str() function.
  """
  if type(string) != type(''):
    logger.debug ('%s: non-string value in echo: %r', handle(), string)
    string = str(string)
  write (string)

def showfile(filename, bps=0, pause=0.15, cleansauce=True):
  """
  Display a file to output.
  @param bps: Baud rate simulation speed, such as 9600.
  @param pause: when simulating baud rate, pause between each delayed sequence.
  @param cleansauce: When set, examile file for sauce data, and remove before output.
  """
  if '*' in filename or '?' in filename:
    fobj = ropen(filename, 'rb')
  else:
    fobj = fopen(filename, 'rb')
  if cleansauce:
    data = str(SAUCE(fobj))
  else:
    data = chompn(fobj.read())
  if not bps:
    echo (chompn(data))
  else:
    cps = bps /8      # charaters per second
    cpp = cps * pause # characters per pause
    n = 0
    for ch in data:
      n +=1
      if n == int(cpp):
        getch(pause)
        n = 0
      echo (ch)

def readline (max, value='', hidden='', paddchar=' ', events=['input'], timeout=None, interactive=False, silent=False):
  value, event, data = readlineevent(max, value, hidden, paddchar, events, timeout, interactive, silent)
  return value
  # XXX re-definition of built-in 'max' here...

def readlineevent (max,
              value='',
              hidden='',
              paddchar=' ',
              events=['input'],
              timeout=None,
              interactive=False,
              silent=False):
  """
  Line editor and general purpose event reader.

  This is most commonly used when both input from the user into a field is
  expected, as well as other non-input events.

  Set interactive if the calling procedure returns None immediately after
  each call, unless either the L{KEY.ENTER} is recieved in the input event,
  or any other events are recieved.

  @return: A tuple is returned in the form of (field_input, event, data), where
  field_input is the current text in the input field, event is the event recieved,
  and data is either the last keypress on input event (KEY.ENTER by default), or
  the data recieved for an alternate event described in the L{events} paramater.

  @param value:
    pre-populate field with this data, as if it were inputted by user.
  @param hidden:
    mask output characters using this character, such as password fields.
  @param paddchar:
    character displayed to overwrite prior column on backspace.
  """

  mx = int(mx)
  # value checking
  if not isinstance(value, str):
    print 'bbs.py: non-string, \'' + repr(value) + '\' passed as value to readlineevent, tossing'
    value = ''
  if not hidden:
    write (value)
  else:
    write (hidden *len(value))

  # events checking
  if not isinstance(events, list):
    print 'bbs.py: non-list \'' + repr(events) + '\' passed as events to readlineevent, tossing'
    events = []

  # place input event channel at front of events list
  if (len(events) and events[0] != 'input'):
    events.remove('input')
  if not 'input' in events:
    events.insert(0,'input')

  while 1:
    event, char = readevent(events, timeout)

    # pass-through non-input data
    if event != 'input':
      data = char
      return (value, event, data)
    else:
      data = None

    # escape or carraige return, returns from readline(),
    # as well as when interactive=True for each keystroke,
    # but only after manipulation occurs
    if char == KEY.EXIT:
      # XXX out of band signals, for now,
      # always return none. Remember, return
      # value == None for exit, and
      return (None, 'input', data)
    elif char == KEY.ENTER:
      # value == "" for carriage return
      # on empty input
      return (value, 'input', KEY.ENTER)

    elif char == KEY.BACKSPACE:
      if len(value) > 0:
        value = value [:-1]
        write ('\b' + paddchar + '\b')
    elif len(value) < mx and isprint(ord(char)):
      value += char
      if hidden:
        write(hidden)
      else:
        write(char)
    elif not silent:
      write (bel)
    if interactive:
      return (value, 'input', None)

def loginuser(handle):
  """
  Register caller's session as user identified by handle.

  Parameter L{handle} must already have been sucessfully identified
  via the authuser() function, available in the L{userdb} module.
  """
  u = getuser(handle)
  u.set ('calls', u.calls +1)
  u.set ('lastcall', time.time())
  getsession().setuser (u)
  globalevent (handle + ' logged in, call #' + str(u.calls))

def uniq(seq):
  # Dave Kirby, http://www.peterbe.com/plog/uniqifiers-benchmark/uniqifiers_benchmark.py
  seen = set()
  return [x for x in seq if x not in seen and not seen.add(x)]
