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

def main(login_handle):

  # resume previous session?
  while True:
    rs = dict([(str(n), (s)) \
      for n, s in enumerate(sessionlist()) \
      if s.handle == login_handle and not len(s.terminals)])

    if not len(rs):
      break # no sessions to resume

    echo ('\r\n\r\n' + color(*LIGHTGREEN))
    echo ('Resume a previously abandoned session?')
    echo ('\r\n' + color())
    for num, s in sorted(rs.items()):
      echo ('\r\n  %s. %s, %s idle' % (num, s.activity, asctime(s.idle())))
    if len(rs) < cfg.max_sessions:
      echo ('\r\n  X. Start new session')
      orX=', or X'
    else:
      orX=''
    echo ('\r\n\r\n [' + ', '.join(rs.keys()) + orX + ']: ')
    choice = readline (max=maxwidth(rs.keys()))

    if choice.lower() == 'x' and len(rs) < cfg.max_sessions:
      break # go ahead and start a new session
    elif choice in rs.keys():
      resume = rs[choice]
      # get this session's terminal, there should be only 1 (us)
      terminal = getsession().terminals[0]
      # detatch terminal from this session
      getsession().detachterminal (terminal)
      # and resume another session
      resume.attachterminal (terminal)
      # kill this session
      terminate () # ! endpoint

  # setuid
  loginuser (login_handle)

  # setuid
  getsession().activity = 'Intro screen'
  getsession().persistent = True

  # retrieve user record (for settings)
  user = getuser(handle())

  echo (cls() + color())
  showfile ('art/msgs.asc')

  # rebuild 'last callers' log after each login
  gosub('lc', True)

  gosub('chkmsgs')
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
