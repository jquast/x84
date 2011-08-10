"""
 Matrix login screen for X/84 BBS, http://1984.ws
 $Id: matrix.py,v 1.9 2010/01/02 07:35:43 dingo Exp $

 This script is the session entry point called by the engine as cfg.matrixscript.

 If 'handle' is passed to main, then authentication is skipped.
 This is the case when a user arrives by ssh login.
"""

__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast',
                 'Copyright (c) 2005 Johannes Lundberg']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

import re
deps = ['bbs']

def main ():
  session = getsession()

  # enable high-bit art for PC-DOS vga fonts,
  # enable line wrapping at right margin,
  # display cursor,
  # enable scrolling,
  echo (charset() + linewrap() + cursor_show() + scroll())

  def refresh():
    # display software version, copyright, and banner
    echo (cls() + color())

  refresh()
  echo ('Sit fACiNG thE SCREEN, lOGAN-5\r\n')

  if not (session.height and session.width) \
    or (session.TERM== 'unknown'):
    # Delay for 1 second, telnet NAWS and TERMTYPE communications occur
    # after the session is created, so that the results are communicated
    # up through the session layer. However, this means the matrix script
    # is running simultaneously. Lets give it a second to ensure those
    # communicates have had enough time to occur.
    x = getstr(period=0.3)
    if x:
      log.write ('u:'+handle(), 'throwing on-connect chatter: %s' %(x,))


  echo ('Terminal size: ')
  if not (session.height and session.width):
    # we can try to detect the window size using ansi sequences. This is done
    # by moving the cursor to 999,999 and querying the client for their
    # position. We do this in the standard vt100 way first, then try for sun
    # clients.

    termdetections = ( \
      ('vt100', (CSI + '6n'), '\033' + r"\[(\d+);(\d+)R"),
      ('sun', (CSI + '18t'), '\033' + r"\[8;(\d+);(\d+)t"))

    for TERM, query_seq, response_pattern in termdetections:
      # save cursor position, enable scrolling
      echo (cursor_save() + pos(999,999) + query_seq)
      response = getstr(period=0.2)
      echo (cursor_restore())
      if response:
        pattern = re.compile(response_pattern)
        match = pattern.search(response)
        if match:
          session.setTermType(TERM)
          h, w = match.groups()
          try:
            session.setWindowSize(int(w),int(h))
          except ValueError: pass
          break

  echo ('%sx%s\r\n' % (session.width, session.height))

  #echo ('IDENTIFY ')
  echo ("SYStEM MAitENANCE!\r\niii\r\n")
  y = readkey ()
  print y
  if y == 'x':
    gosub('naked_lunch')
  disconnect()

