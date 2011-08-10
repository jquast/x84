"""
 Matrix post-login screen for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 Copyright (c) 2005 Johannes Lundberg
 $Id: top.py,v 1.4 2008/05/26 07:26:28 dingo Exp $

 This script is called after sucessfull login.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast'
                 'Copyright (c) 2005 Johannes Lundberg']
__license__ = 'ISC'
deps = ['bbs','ui.leftright']

def main(login_handle):
  session.activity = 'Intro screen'

  # setuid
  loginuser (login_handle)

  echo (cls() + color())
  showfile ('ans/top.ans')

  def disp_num_msgs(msgs, txt=' new message'):
    return str(len(msgs)) + color() + txt

  echo (pos(60, 9) + color(*LIGHTRED) + '* ' + color() \
    + 'new msg scan' + color(*DARKGREY) + '...')
  oflush ()
  privmsgs = listprivatemsgs(handle())
  echo (pos(55, 10) + color(*LIGHTGREY))
  txt = ' private msg'
  if len(privmsgs) != 1: txt += 's'
  echo (disp_num_msgs(privmsgs, txt))

  oflush ()
  newprivmsgs = msgfilter(privmsgs, type='read', data=False)
  if len(newprivmsgs):
    echo (', ' + color(*LIGHTGREEN))
    echo (disp_num_msgs(newprivmsgs, ' new') + bel)

  oflush ()
  pubmsgs = listpublicmsgs(tags=None)
  echo (pos(55, 11) + color(*LIGHTGREY))
  echo (disp_num_msgs(pubmsgs, ' public msgs'))

  oflush ()
  # exclude messages already read
  newpubmsgs = msgfilter(pubmsgs, inclusive=False, type='read', data=handle())
  if len(newpubmsgs):
    echo (', ' + color(*LIGHTGREEN))
    echo (disp_num_msgs(newpubmsgs, ' new') + bel)

  oflush ()
  echo (pos(60, 13) + color(*LIGHTRED) + '* ' + color() \
    + 'logging call' + color(*DARKGREY) + '...')
  gosub('lc', True)

  echo (pos(5,25) + '(- This is a 25 line bbs! -)')
  echo (pos(5,1) + '(- This is a 25 line bbs! -)')

  # Prompt to read new private messages
  if newprivmsgs:
    echo (pos(37, 24) + color() + 'Read new private mail?')
    lr = leftrightclass([60,24], LEFT)
    if (lr.run() == LEFT):
      gosub ('msgreader', newprivmsgs)
    echo (color())

  # Prompt to read new public messages
  if newpubmsgs:
    echo (pos(37, 24) + color() + 'Read new public mail?')
    lr = leftrightclass([60,24], LEFT)
    if (lr.run() == LEFT):
      gosub ('msgreader', newpubmsgs)
    echo (color())

  # Prompt for quick login
  echo (pos(47, 24) + color() + cl() + 'Quick Login?')
  lr = leftrightclass([60,24], RIGHT)
  if (lr.run() == LEFT):
    goto ('main')

  # last callers
  gosub('lc')

  # news
  gosub('news')

  # one liners
  gosub('ol')

  # weather
  if user.has_key('zipcode'):
    gosub('weather', user.zipcode)

  # jump to main
  goto('main')
