"""
 Matrix login screen for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 Copyright (c) 2005 Johannes Lundberg
 $Id: matrix.py,v 1.6 2009/05/02 04:38:24 dingo Exp $ #

 This is an otherwise generic login matrix for bulletin board systems,
 with the exception of a unique feature: the checkresume() function looks
 for sessions without an attached terminal, and prompts the user to
 resume one of these sessions or create a new one.

 finduser() discovers users with the same handle but different mixed case
 userexist() returns true if the user specified exists on the system
 authuser() returns true if the password for the specified user is correct
 top() is then called via goto, from which this script never resumes control
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast'
                 'Copyright (c) 2005 Johannes Lundberg']
__license__ = 'ISC'

import re
deps = ['bbs']

# fields, [x, y]
loc_user = [26, 9]
loc_pass = [28, 11]
loc_prompt = [35, 22]
#
def checkresume (handle):
  """ Check for and resume sessions. A listing is made from global
      sessionlist() of users who match our handle and are without an attached
      terminal. Resuming a session is similar to daemon forking, our current
      terminal is disconnected from our current session, and attached to the
      resumed session. Then, this session is terminated. """
  # Check for existing sessions, and let the user choose.
  sesctl = LightClass (4, 60, 24-4, 40-(60/2))
  sesctl.partial = True
  sesctl.interactive = True
  sesctl.byindex = True
  refresh = True
  while 1:
    vprint = ['New session']
    vdata  = ['new']
    for s in sessionlist():
      if handle == s.handle and not len(s.terminals):
        vprint.append (s.activity + ', ' + asctime(s.idle()) + ' idle')
        vdata.append (s)
    if len(vprint) == 1:
      return # no sessions to resume
    if refresh:
      echo (color() + color(GREEN))
      sesctl.border ()
      sesctl.title ('< Resume a previously abandoned session? >')
      refresh = False
    elif len(vprint) > cfg.max_sessions:
      # too many sesions
      vprint.remove ('New session')
      vdata.remove ('new')
    sesctl.update (vprint)
    idx = sesctl.run(timeout=3)
    if idx is not None:
      resume = vdata[idx]
      if resume == 'new':
        return # create new session
      break

  # get session's terminal
  terminal = session.terminals[0]
  # detatch terminal from this session
  session.detachterminal (terminal)
  # and resume another session
  resume.attachterminal (terminal)
  # kill this session
  terminate ()

def main ():
  # some clients send an identifier (syncterm), throw away for now.
  # we don't care about baud rate, and we're ansi only!
  echo ('X/84, PRSV branch\r\n')
  echo ('Authors:\r\n')
  echo ('  Jeff Quast <dingo@1984.ws>\r\n')
  echo ('  Johannes Lundberg <johannes.lundberg@gmail.com>\r\n\r\n')
  echo ('\r\nIdentifying terminal: ')
  idstr = getstr(period=.3)
  if not idstr:
    echo ('Answerback? \005')
    idstr = getstr(period=.3)

  if idstr:
    echo (idstr + '\r\n')
    log.write('1984/matrix', 'client identified as %r' % idstr)
  else:
    echo ('none \r\n')
    log.write('1984/matrix', 'client did not identify %r' % idstr)

  echo ('Terminal size: ')
  row, col, termtype = None, None, None

  # the following sequence is derived from X11-0.40.2/xc/programs/xterm/resize.c
  echo (cursor_attr_save() + scroll()) # save attribute and enable scrolling
  echo (pos(999,999)) # move to presumably out-of-bounds lower-right corner

  echo ('vt100? ')
  response = getstr(period=0.3)

  termdetections = ( \
    ('sun', (CSI + '18t'), '\033' + r"\[8;(\d+);(\d+)t"),
    ('vt100', (CSI + '6n'), '\033' + r"\[(\d+);(\d+)R"))

  for termtype, query_seq, regexp in termdetections:
    echo (termtype + '? ')
    echo (query_seq)
    response = getstr(period=0.30)
    if response:
      pattern = re.compile(regexp)
      match = pattern.search(response)
      if match:
        session.termtype = termtype
        row, col = match.groups()
        session.row, session.col = str(row), str(col)
        echo (str(col) + 'x' + str(row))
        break
      else:
        echo ('failed ')
        log.write('1984/matrix', 'client response illegal for %s: %r' % (termtype, response))

  echo (cursor_attr_restore())

  if row and col and termtype:
    log.write ('1984/matrix', 'client screen size: %sx%s (%s)' % (row, col, termtype))
    echo (col + 'x' + row + ' (' + termtype + ')\r\n')

  # intro screen
  session.activity = 'login matrix'

  echo ( cls() + cursor_show())
  showfile ('ans/matrix.ans')

  # auth loop
  handle = ''
  while True:
    echo (pos(*loc_user))
    handle, event, data = readlineevent(max=cfg.max_user, value=handle)
    if handle.lower() == 'new':
      goto ('nua', '')
    elif handle in ['logoff', 'bye', 'quit']:
      goto ('logoff')
    match = finduser(handle)
    if match:
      handle = match
      echo (pos(*loc_pass))
      password, event, data = readlineevent(max=cfg.max_pass, hidden='x')
      if authuser(handle, password):
        # check for abandoned sessions
        checkresume (handle)
        session.persistent = True
        goto ('top', handle)
      echo (pos(30, 23) + cl() + color(*LIGHTRED) + 'Login incorrect')
      readkey (1)
      echo (color() + cl())
      # clear password input field
      echo (pos(*loc_pass) + ' ' + ' '*cfg.max_pass)
    else:
      echo (pos(40,23) + color() + 'CREAtE NEW ACCOUNt?')
      # prompt to create new account
      lr = LeftRightClass([62,23])
      lr.left ()
      lr.run()
      if lr.isleft():
        # goto new user account script
        goto ('nua', handle)
      echo (cl())
