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
__url__ = 'https://github.com/jquast/x84'

import re
deps = ['bbs']
CH_MASK_PASSWD='x'
wait_negotiation=1.0
def main ():
  terminal = getsession().getterminal()

  def refresh():
    # display software version, copyright, and banner
    with terminal.location():
      #echo (terminal.move (0,0) + terminal.clear_eos)
      echo ('X/84, PRSV branch: %s license, see %s for source' \
          % (__license__, __url__))
      for c in __copyright__:
        echo ('\r\n  %s' % (c))
      echo ('\r\n\r\n')
      showfile('art/1984.asc')
      echo ('\r\n\r\n')
      echo (terminal.normal_cursor)
      # DEBUG
      echo ('keyseq, keycode\r\n')
      for keyseq, keycode in terminal.keymap.iteritems():
        echo ('%14r %s\r\n' % (keyseq, terminal.keyname(keycode)))
      # END DEBUG

  refresh ()
  i_handle=''
  while True:
    getsession().activity = 'logging in'
    echo ('\r\n  user: ')
    max_user = int(ini.cfg.get('nua', 'max_user'))

    i_handle, event, data = readlineevent(width=max_user, value=i_handle)
    if not i_handle:
      continue
    if i_handle.lower() == 'new':
      goto ('nua', '')
    elif i_handle in ['exit', 'logoff', 'bye', 'quit']:
      gosub ('logoff')
      refresh()
    match = userbase.finduser(i_handle)
    if not match:
      echo ('\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5)
      ynq = getch()
      if ynq.lower() == 'y':
        goto ('nua', i_handle)
      elif ynq.lower() == 'q':
        goto ('logoff')
      else: # 'n' is default
        continue
    i_handle = match
    echo ('\r\n\r\n  pass: ')
    password, event, data = readlineevent \
        (**dict([('width',    int(ini.cfg.get('nua', 'max_pass'))),
                 ('hidden', CH_MASK_PASSWD)]))
    if userbase.authuser(i_handle, password):
      goto (ini.cfg.get('system', 'topscript'), i_handle)
    else:
      echo (cl() + color(*LIGHTRED) + 'Login incorrect' + color() + '\r\n')
      getch (1)
      continue
