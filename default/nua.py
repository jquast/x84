"""
 New user account script for X/84, http://1984.ws

 Simply create a new User() instance and set the most minimum values,
 handle and password, then call the .add() method to commit this record.
"""

# input area (y, x)
loc_user   = (12, 20)
loc_origin = (14, 20)
loc_pass   = (16, 20)
loc_email  = (18, 20)
loc_state  = (20, 10)
loc_prompt = (23, 35)
# grr, (x, y) ?
loc_yesno  = (62, 23) #23, 62)

def main (handle):
  if handle.lower() in ('new',):
    handle = ''
  location, hint = '', ''
  password, verify, = '', ''
  session = getsession()
  terminal = getterminal()

  def warning(msg):
    " Display warning to user with a dynamic pause "
    cpsec =  13.0
    min_sec = 3
    split_loc = 3
    warning_msg = ''.join((
        terminal.clear_eol,
        terminal.normal, terminal.red, msg[:-split_loc],
        terminal.normal, msg[-split_loc:],
        terminal.bright_black, '!'))
    echo (warning_msg)
    inkey = getch(max(min_sec,float(len(msg))/cpsec))
    echo (terminal.clear_bol)
    return inkey

  session.activity = 'New User Application'
  echo (terminal.clear + terminal.normal)
  showfile ('art/newuser.asc')
  echo ( 'New User Application'.center (terminal.width-1) + '\r\n')

  while True:
    user_ok = origin_ok = pass_ok = level = 0
    while not (user_ok):
      echo (terminal.move (*loc_user))
      echo (terminal.clear_eol + terminal.normal)
      echo ('username: ')
      handle = readline (int(ini.cfg.get('nua', 'max_user')), handle)
      echo (terminal.move (*loc_user))
      if not handle:
        inkey = warning('Enter an alias, Press Ctrl+X to cancel')
        if inkey == chr(24):
          return
      elif userbase.userexist (handle):
        warning ('User exists')
      elif handle == '' or len(handle) < int(ini.cfg.get('nua', 'min_user')):
        warning ('Too short! (%s)' % ini.cfg.get('nua', 'min_user'))
      elif handle.lower() in ini.cfg.get('nua', 'invalid_handles').split():
        warning ('Illegal username')
      else:
        user_ok = True

    while not (origin_ok):
      echo (terminal.move (*loc_origin))
      echo (terminal.clear_eol + terminal.normal)
      echo ('origin: ')
      location = readline (int(ini.cfg.get('nua', 'max_origin')), location)
      echo (terminal.move (*loc_origin))
      if location == '':
        inkey = warning('Enter a location, Press Ctrl+X to cancel')
        if inkey == chr(24):
          return
        echo (terminal.clear_eol)
      else:
        origin_ok = True

    while not (pass_ok):
      echo (terminal.move(*loc_pass))
      echo (terminal.clear_eol + terminal.normal)
      echo ('password: ')
      password = readline (int(ini.cfg.get('nua', 'max_pass')), hidden='x')
      echo (terminal.move(*loc_pass))
      if len(password) < 4:
        # fail if password too short
        echo (terminal.move (*loc_email))
        inkey = warning('too short, Press Ctrl+X to cancel')
        if inkey == chr(24):
          return
        echo (terminal.clear_eol)
      else:
        # verify
        echo (terminal.clear_eol + terminal.normal)
        echo ('   again: ')
        verify = readline (int(ini.cfg.get('nua', 'max_pass')), hidden='z')
        echo (terminal.move(*loc_pass))
        if password != verify:
          inkey = warning ('verify must match, Press Ctrl+X to cancel')
          if inkey  == chr(24):
            return
          echo (terminal.clear_eol)
        else:
          break

    # this is a joke?
    while (level < 2):
      echo (terminal.move(*loc_email))
      # email loop
      echo (terminal.clear_eol + terminal.normal)
      echo ('e-mail (optional): ')
      hint= readline (int(ini.cfg.get('nua', 'max_email')))
      echo (terminal.move(*loc_email))
      # TODO regexp
      if not len(hint):
        level = 2
        break # no e-mail
      for ch in hint:
        # must have @, level 1
        if ch == '@':
          level = 1
        # must have '.' following @, level 2
        if level == 1 and ch == '.':
          level = 2
          break
      if level == 2:
        # email is valid, break out
        break

      # allow user to opt-out of e-mail
      echo (terminal.location (*loc_state))
      inkey = warning('invalid, Ctrl+O to Opt out')
      echo (terminal.location (*loc_state))
      if inkey == chr(15):
        echo (terminal.clear_eol + terminal.normal)
        echo ('make your statement, then: ')
        hint = readline (int(ini.cfg.get('nua', 'max_email')))
        if not hint:
          return
        break

    echo (terminal.move (*loc_prompt))
    echo (terminal.clear_eol + terminal.normal)
    echo ('Everything cool?')

    lr = YesNoClass(loc_yesno)
    lr.left ()
    lr.run()
    if lr.isleft():
      # we've gained the following variables:
      # handle, password, location, hint
      u = userbase.User \
          (handle=handle, password=password, location=location, hint=hint)
      u.add ()
      goto ('top', u.handle)
