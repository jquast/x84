"""
 Matrix post-login screen for X/84 (formerly 'The Progressive') BBS
 This script is called after sucessfull login.
"""

deps = ['bbs']
lastupdate = 0

def main(login_handle):
  # setuid
  loginuser (login_handle)

  getsession().activity = 'Intro screen'
  getsession().persistent = True

  # retrieve user record (for settings)
  user = getsession().getuser()
  term = getsession().getterminal()

  # rebuild 'last callers' log after each login
  if not lastupdate or time.time() -lastupdate > 20:
    gosub('lc', True)

  getsession().activity = 'Intro screen'
  gosub('chkmsgs')

  getsession().activity = 'Intro screen'
  echo ('\r\n\r\nQuick login? [yn] ')
  while True:
    k = getch()
    if isinstance(k, str):
      if k.lower() == 'y':
        goto ('main')
      elif k.lower() == 'n':
        break

  # last callers
  gosub('lc')

  # news
  gosub('news')

  # one liners
  gosub('ol')

  # jump to main
  goto('main')
