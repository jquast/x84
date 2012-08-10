"""
 Matrix post-login screen for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 Copyright (c) 2005 Johannes Lundberg
 $Id: top.py,v 1.4 2009/05/18 18:34:49 dingo Exp $

 This script is called after sucessfull login.

 An interesting feature here is the ability to resume sessions.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast'
                 'Copyright (c) 2005 Johannes Lundberg']
__license__ = 'ISC'

deps = ['bbs']
import time
lastupdate = 0

def main(login_handle):
  # resume previous session?
  while True:
    rs = dict([(str(n), (s)) \
      for n, s in enumerate(sessionlist()) \
      if s.handle == login_handle and not len(s.terminals)])
    if not rs:
      # no sessions to resume;
      break
    echo ('\r\n\r\n' + color(*LIGHTGREEN))
    echo ('Resume a previously abandoned session?')
    echo ('\r\n' + color())
    # layered joke-cake
    for num, s in sorted(rs.items()):
      echo ('\r\n  %s. %s, %s idle' % (num, s.activity, asctime(s.idle())))
    if len(rs) < cfg.get('system','max_sessions'):
      echo ('\r\n  X. Start new session')
      orX=', or X'
    else:
      orX=''
    echo ('\r\n\r\n [' + ', '.join(rs.keys()) + orX + ']: ')
    choice = readline (max=maxwidth(rs.keys()))
    echo ('\r\n$\r\n')

    if choice.lower() == 'x' or not len(choice):
      if len(rs) < cfg.get('system','max_sessions'):
        echo ('\r\nspawning new session...\r\n')
        break # go ahead and start a new session
      echo ('\r\ntoo many sessions ...\r\n')

    elif choice in rs.keys():
      resume = rs[choice]
      echo ('\r\nresuming session: %s\r\n' % (resume,))
      # get this session's terminal, there should be only 1 (us)
      terminal = getsession().terminals[0]
      echo ('\r\ndetaching terminal: %s\r\n' % (terminal,))
      # detatch terminal from this session
      getsession().detachterminal (terminal)
      # and resume another session
      resume.attachterminal (terminal)
      # kill this session
      terminate () # ! endpoint
    echo ('\r\ninvalid choice,\r\n')

  # setuid
  loginuser (login_handle)

  getsession().activity = 'Intro screen'
  getsession().persistent = True

  # retrieve user record (for settings)
  user = getuser(handle())

  echo (cls() + color())
  showfile ('art/msgs.asc')

  # rebuild 'last callers' log after each login
  if not lastupdate or time.time() -lastupdate > 20:
    gosub('lc', True)

  getsession().activity = 'Intro screen'
  gosub('chkmsgs')

  getsession().activity = 'Intro screen'
  echo ('\r\n\r\nQuick login? [yn] ')
  while True:
    k = readkey()
    if k.lower() == 'y':
      goto ('main')
    elif k.lower() =='n':
      break

  # last callers
  gosub('lc')

  # news
  gosub('news')

  # one liners
  gosub('ol')

  # jump to main
  goto('main')
