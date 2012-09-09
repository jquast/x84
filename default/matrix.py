"""
 Matrix login screen for X/84 (Formerly, 'The Progressive') BBS, http://1984.ws

 This script is the session entry point. In Legacy era, a matrix script might
 be something to full folk not in the know, require a passcode, or even
 swapping the modem into a strange stop/bit/parity configuration, or
 auto-answering to strange strings, or simply, "login" program. thats what we
 do here.
"""
__url__ = 'https://github.com/jquast/x84/'

TIMEOUT = 45
CH_MASK_PASSWD = 'x'
ALLOW_ANONYMOUS = True
ALLOW_APPLY = True
def main ():
  session = getsession()
  term = getterminal()
  handle=''
  byecmds = ini.cfg.get('matrix', 'byecmds').split()
  newcmds = ini.cfg.get('matrix', 'newcmds').split()
  APPLY_DENIED = '\r\n\r\nfiRSt, YOU MUSt AbANdON YOUR libERtIES.'
  apply_msg = '\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5
  encrypt_msg = term.cyan_reverse + '  encrypting ...'

  def denied(msg):
    echo (msg)
    echo (term.normal + '\r\n\r\n')
    getch (0.7)

  def refresh():
    echo (term.move (0,0) + term.clear)
    echo ('\r\n%s\r\n' % (ini.cfg.get('system','bbsname'),))
    echo ('see %s for source\r\n' % (__url__,))
    echo ('\r\n\r\n')
    showfile('art/1984.asc')
    echo ('\r\n\r\n')
    if ALLOW_ANONYMOUS:
      echo ("'anonymous' login enabled.\r\n")
    echo (term.normal_cursor)

  refresh ()
  while True:
    session.activity = 'logging in'
    echo ('\r\n  user: ')
    max_user = int(ini.cfg.get('nua', 'max_user'))

    handle, event, data = readlineevent \
        (width=max_user, value=handle,
            events=(('refresh','input',)), timeout=TIMEOUT)

    if (None, None) == (event, data):
      logger.info ('login timeout exceeded')
      goto ('logoff')

    if event == 'refresh':
      refresh ()
      flushevent ('refresh')

    if handle == '':
      continue # re-prompt

    if handle.lower() in newcmds:
      if ALLOW_APPLY:
        # 'new' in your language ..
        gosub ('nua', '')
        refresh()
        continue
      else:
        # applications are denied
        denied (term.bright_red + APPLY_DENIED)

    elif handle in byecmds:
      # 'so long,' in whatever your localization ...
      goto ('logoff')

    # this account name used to be about warez, not sql injections
    if handle.lower() == 'anonymous':
      if ALLOW_ANONYMOUS:
        goto (ini.cfg.get('matrix', 'topscript'), 'anonymous')
      else:
        denied ("\r\n\r\n%s'%s' login denied." % (term.bright_red, handle,))

    # match handle, request to create new account
    match = finduser(handle)
    if match is None:
      if not ALLOW_APPLY:
        # applications are denied
        denied (term.bright_red + APPLY_DENIED)
        getch (0.8)
        continue
      echo (apply_msg)
      ynq = getch()
      if str(ynq).lower() == 'y':
        goto ('nua', handle)
      elif str(ynq).lower() == 'q' \
      or ynq == term.KEY_EXIT:
        goto ('logoff')
      else: # 'n' is default
        continue
    handle = match

    # request & authenticate password
    echo ('\r\n\r\n  pass: ')
    password, event, data = readlineevent \
        (width=int(ini.cfg.get('nua', 'max_pass')),
            hidden=CH_MASK_PASSWD, timeout=TIMEOUT*2)
    if (None, None) == (event, data):
      goto ('logoff')
    echo (term.move_x(1) + term.clear_eol)
    (x, y) = getpos(0.15)
    echo (encrypt_msg)
    if authuser(handle, password):
      goto (ini.cfg.get('matrix', 'topscript'), handle)
    if (None,None) != (x, y):
      echo (term.move (x, y))
    denied (term.red_reverse + "'%s' login failed." % (handle,))
