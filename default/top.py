"""
 Matrix post-login screen for X/84 (formerly 'The Progressive') BBS
 This script is called after sucessfull login.
"""

def main(login_handle='anonymous'):
  import time

  # XXX setuid routine, allow 'anonymous' user !
  user = getuser(login_handle) \
      if login_handle != 'anonymous' \
      else User()
  user.calls += 1
  user.lastcall = time.time()

  session = getsession()
  session.activity = 'Intro screen'
  session.user = user

  term = session.terminal

  # rebuild last caller db
  gosub('lc', True)
  session.activity = 'Intro screen'

  gosub('chkmsgs')
  session.activity = 'Intro screen'

  echo ('\r\n\r\nQuick login? [yn] ')
  while True:
    k = getch()
    if type(k) is not int:
      if k.lower() == 'y':
        goto ('main')
      elif k.lower() == 'n':
        break

  # last callers
  gosub('lc')
  session.activity = 'Intro screen'

  # news
  gosub('news')
  session.activity = 'Intro screen'

  # one liners
  gosub('ol')
  session.activity = 'Intro screen'

  # jump to main
  goto('main')
