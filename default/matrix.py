"""
 Matrix login screen for X/84 BBS, http://1984.ws
 $Id: matrix.py,v 1.9 2010/01/02 07:35:43 dingo Exp $

 This script is the session entry point called by the engine as cfg.matrixscript.

 If 'handle' is passed to main, then authentication is skipped. This is the
 case when a user arrives by ssh login.
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
    echo ('X/84, PRSV branch: %s license, see %s for source' % (__license__, __url__))
    for c in __copyright__:
      echo ('\r\n  %s' % (c))
    echo ('\r\n\r\n')
    showfile('art/1984.asc')
    echo ('\r\n\r\n')

  refresh()
  if not (session.height and session.width) \
  or (session.TERM== 'unknown'):
    # Delay for 1 second, telnet NAWS and TERMTYPE communications occur
    # after the session is created, so that the results are communicated
    # up through the session layer. However, this means the matrix script
    # is running simultaneously. Lets give it a second to ensure those
    # communicates have had enough time to occur.
    x = getstr(period=1.0)
    if x:
      log.write ('u:'+handle(), 'throwing on-connect chatter: %s' %(x,))

  # for the most part, terminal size is asked for and negotiated using
  # the telnet protocol. However, if this neogitation fails, or doesn't
  # happen because we're via ssh or another protocol, we try it here

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
      response = getstr(period=1.6)
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
  echo ("SYStEM MAitENANCE!\r\n\r\n")

  echo ('Terminal type: ')
  if session.TERM and session.TERM != 'unknown':
    echo (session.TERM+ '\r\n')
  else:
    log.write ('u:'+handle(), 'requesting answerback sequence')
    echo ('(Answerback?\005')
    idstr = getstr(period=1.6)
    if idstr:
      # check for compatible terminal??
      echo (') %s\r\n' % (idstr,))
      session.setTermType(idstr)
    else:
      echo (') using default: %s\r\n' % (db.cfg.default_keymap,))
      session.setTermType(db.cfg.default_keymap)

  i_handle=''
  while True:
    session.activity = 'logging in'
    echo ('\r\n  user: ')
    i_handle, event, data = readlineevent(max=cfg.max_user, value=i_handle)
    if not i_handle:
      continue
    if i_handle.lower() == 'new':
      goto ('nua', '')
    elif i_handle in ['exit', 'logoff', 'bye', 'quit']:
      gosub ('logoff')
      refresh()
    match = finduser(i_handle)
    if not match:
      echo ('\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5)
      ynq = readkey()
      if ynq.lower() == 'y':
        goto ('nua', i_handle)
      elif ynq.lower() == 'q':
        gosub ('logoff')
        refresh ()
      else: # 'n' is default
        continue
    i_handle = match
    echo ('\r\n\r\n  pass: ')
    password, event, data = readlineevent(max=cfg.max_pass, hidden='x')
    if authuser(i_handle, password):
      goto (cfg.topscript, i_handle)
    else:
      echo (cl() + color(*LIGHTRED) + 'Login incorrect' + color() + '\r\n')
      readkey (1)
      continue
