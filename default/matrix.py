"""
 Matrix login screen for X/84 (Formerly, 'The Progressive') BBS, http://1984.ws

 This script is the session entry point
"""
__license__ = 'ISC'
__url__ = 'https://github.com/jquast/x84/'

CH_MASK_PASSWD = 'x'

def main ():
  terminal = getterminal()

  def refresh():
    # display software version, copyright, and banner
    echo (terminal.move (0,0) + terminal.clear)
    echo ('X/84, PRSV branch: %s license, see %s for source' \
        % (__license__, __url__))
    echo ('\r\n\r\n')
    showfile('art/1984.asc')
    echo ('\r\n\r\n')
    echo (terminal.normal_cursor)
    # DEBUG
    echo ('keyseq, keycode: ')
    for keyseq, keycode in terminal._keymap.iteritems():
      echo ('%r %s; ' % (keyseq, terminal.keyname(keycode)))
    echo ('\r\n')
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
    elif i_handle in ini.cfg.get('matrix', 'byecmds').split():
      gosub ('logoff')
      refresh()
    elif i_handle.lower() == 'anonymous':
      goto (ini.cfg.get('matrix', 'topscript'), 'anonymous')
    match = finduser(i_handle)
    if not match:
      echo ('\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5)
      ynq = getch()
      if str(ynq).lower() == 'y':
        goto ('nua', i_handle)
      elif str(ynq).lower() == 'q' \
      or ynq == terminal.KEY_EXIT:
        goto ('logoff')
      else: # 'n' is default
        print 'x', repr(ynq)
        continue
    i_handle = match
    echo ('\r\n\r\n  pass: ')
    password, event, data = readlineevent \
        (width=int(ini.cfg.get('nua', 'max_pass')), hidden=CH_MASK_PASSWD)
    if authuser(i_handle, password):
      goto (ini.cfg.get('matrix', 'topscript'), i_handle)
    else:
      echo (terminal.clear_bol + terminal.bright_red)
      echo ('Login incorrect')
      echo (terminal.normal + '\r\n')
      getch (1)
      continue
