"""
 Matrix login screen for X/84 (Formerly, 'The Progressive') BBS, http://1984.ws

 This script is the session entry point. In Legacy era, a matrix script might
 be something to full folk not in the know, require a passcode, or even
 swapping the modem into a strange stop/bit/parity configuration, or
 auto-answering to strange strings, or simply, "login" program. thats what we
 do here.
"""
__url__ = u'https://github.com/jquast/x84/'

import sys

TIMEOUT = 45
CH_MASK_PASSWD = u'x'
ALLOW_ANONYMOUS = True
def main ():
  echo (u'\033(U') # switches to CP437 on some systems.
  # you may or may not want this; the art on this bbs does!
  session = getsession()
  term = getterminal()
  handle=''
  timeout = int(ini.cfg.get('session',  'timeout'))
  byecmds = ini.cfg.get('matrix', 'byecmds').split()
  newcmds = ini.cfg.get('matrix', 'newcmds').split()
  APPLY_DENIED = u'\r\n\r\nfiRSt, YOU MUSt AbANdON YOUR libERtIES.'
  apply_msg = u'\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5
  prompt_user = u'\r\n  user: '
  badpass_msg = u"\r\n  " + term.red_reverse + u"'%s' login failed."
  badanon_msg = u"\r\n  " + term.bright_red + u"'%s' login denied."
  max_user = int(ini.cfg.get('nua', 'max_user'))
  allow_apply = ini.cfg.get('nua', 'allow_apply') in ('yes',)
  topscript = ini.cfg.get('matrix', 'topscript')
  bbsname = ini.cfg.get('system','bbsname')
  status_auth = ''.join((
    term.move (0,0) + term.clear + term.bright_cyan + u'\033#8',
    term.move (max(0,(term.height /2) -1), max(0,(term.width /2) -10),),' '*20,
    term.move (max(0,(term.height /2)   ), max(0,(term.width /2) -10),),
      'encrypting ...'.center (20),
    term.move (max(0,(term.height /2) +1), max(0,(term.width /2) -10),),' '*20,
    term.normal,))
  status_dirties_screen = True

  def denied(msg):
    echo (msg)
    echo (term.normal + u'\r\n\r\n')
    getch (0.7)

  def refresh():
    flushevent ('refresh')
    echo ('\r\n' + term.normal)
    echo (u'\r\nConnected to %s, see %s for source\r\n' % (bbsname, __url__))
    uname = '/usr/bin/uname' if sys.platform in ['darwin'] else '/bin/uname'
    Door (uname, args=('-a',)).run()
    echo (u'\r\n\r\n')
    showfile('art/1984.asc')
    echo (u'\r\n\r\n')
    if ALLOW_ANONYMOUS:
      echo (u"'anonymous' login enabled.\r\n")
    echo (term.normal_cursor)

  refresh ()
  while True:
    session.activity = u'logging in'
    echo (prompt_user)
    handle, event, data = readlineevent \
        (width=max_user, value=handle,
            events=(('refresh','input',)), timeout=timeout)

    if (None, None) == (event, data):
      raise ConnectionTimeout, 'timeout at login prompt'

    if event == 'refresh':
      refresh ()
      continue

    if 0 == len(handle):
      continue # re-prompt

    if handle.lower() in newcmds:
      if allow_apply:
        # 'new' in your language ..
        gosub ('nua', '')
        refresh()
        continue
      else:
        # applications are denied
        denied (term.bright_red + APPLY_DENIED)
        handle = ''
        continue

    elif handle in byecmds:
      goto ('logoff')

    # this account name used to be about warez, not sql injections
    if handle.lower() == 'anonymous':
      if ALLOW_ANONYMOUS:
        goto (topscript, 'anonymous')
      denied (badanon_msg % (handle,))
      getch (0.8)
      handle = ''
      continue
    handle = handle.decode(session.encoding)

    if not DBSessionProxy('userbase').has_key(handle):
      #remain exactly where you are
      #make no move, until you are ordered
      #now we can see you. -i#
      if allow_apply is False:
        # applications are denied
        denied (term.bright_red + APPLY_DENIED)
        getch (0.8)
        handle = ''
        continue

      # the photos of you and the girl will be recycled for prolitarian use
      echo (apply_msg)
      ynq = getch(timeout)
      if ynq is None:
        raise ConnectionTimeout, 'timeout at nua? prompt'
      if str(ynq).lower() == 'q' or ynq == term.KEY_EXIT:
        goto ('logoff')
      if str(ynq).lower() == 'y':
        goto (ini.cfg.get('nua', 'script'), handle)
      continue

    # request & authenticate password
    echo (u'\r\n\r\n  pass: ')

    # even when running a keyboard debug tap (default = off)
    # disable tap during password input.

    chk = session._tap_input # save
    session._tap_input = False
    # get keyboard input
    password, event, data = readlineevent \
        (width=int(ini.cfg.get('nua', 'max_pass')),
            hidden=CH_MASK_PASSWD, timeout=timeout)
    session._tap_input = chk # restore

    if (None, None) == (event, data):
      raise ConnectionTimeout, 'timeout at password prompt'

    if password == '':
      continue

    echo (status_auth)
    if authuser(handle.decode(session.encoding),
        password.decode(session.encoding)):
      goto (ini.cfg.get('matrix', 'topscript'), handle)
    if status_dirties_screen:
      refresh()

    denied (badpass_msg % (handle,))
