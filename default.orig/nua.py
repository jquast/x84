"""
 New user account module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: nua.py,v 1.6 2009/02/24 07:25:24 jojo Exp $

 This modulde demonstrates simple information retrieval for creating a new
 user account, and string and record validation.

 Simply create a new User() instance and set the most minimum values,
 handle and password, then call the .add() method to commit this record.
"""

__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

deps = ['bbs','userbase']

def init():
  pass # nothing to initialize

def warning(string, xy, clean=True):
  " Display warning to user with a dynamic pause "
  # Color theme for warning prompts
  color_left_warn = attr(NORMAL) + color(RED)
  color_right_warn = color()
  color_punc_warn = color(BLACK, BRIGHT)
  split_loc = 3   # characters from right to split for two-tone shading
  cpsec =  13.0   # characters per second to pause for, sleep(len(string)/cps)

  x, y = xy[0], xy[1]
  warning_msg = \
    color_left_warn + string[:-split_loc] \
    + color_right_warn + string[-split_loc:] \
    + color_punc_warn + '! '
  # display
  echo \
    (pos (x, y) \
     + warning_msg )
  # pause
  inkey = readkeyto ( float( len( string)) /cpsec)
  # clear
  echo \
    (pos (x, y) \
     + ' '*ansilen(warning_msg) )
  return inkey

def main (user):
  # input area (x, y)
  loc_user   = (20, 16)
  loc_origin = (20, 18)
  loc_pass   = (20, 20)
  loc_email  = (20, 20)
  loc_state  = (30, 20)
  loc_prompt = (35, 22)

  session.activity = 'New User Application'
  if user.lower() == 'new': user == ''

  echo ( color() + cls() )
  showfile ('ans/nua.ans')

  echo ( pos(40 -(ansilen(session.activity)/2), 14) + session.activity)

  location, hint = '', ''
  while True:
    user_ok, origin_ok, pass_ok, email_ok = False, False, False, 0

    while not (user_ok):
      echo (pos(*loc_user) + cl() + color() + 'username: ')
      user = readline (cfg.max_user, user)
      if not user:
        if warning ('Enter an alias, Press Ctrl+X to cancel', loc_origin) == chr(24):
          return
      elif userexist (user):
        warning ('User exists', loc_origin)
      elif user == '' or len(user) < cfg.min_user:
        warning ('Too short! (%i)' % cfg.min_user, loc_origin)
      elif user.lower() in ['bye', 'new', 'logoff', 'quit', 'sysop', 'all', 'none']:
        warning ('Illegal username', loc_origin)
      else:
        user_ok = True

    while not (origin_ok):
      echo (pos(*loc_origin) + color() + 'origin: ')
      location = readline (cfg.max_origin, location)
      if location == '':
        if warning ('Enter a location, Press Ctrl+X to cancel', loc_pass) == chr(24):
          return
        echo (cl())
      else:
        origin_ok = True

    password, verify, = '', ''
    while not (pass_ok):
      echo (pos(*loc_pass) + cl() + color() + 'password: ')
      password = readline (cfg.max_pass, hidden='x')
      if len(password) < 4:
        # fail if password too short
        if warning ('too short, Press Ctrl+X to cancel', loc_email) == chr(24):
          return
        echo (cl())
      else:
        # verify
        echo (pos(*loc_pass) + cl() + color() + '   again: ')
        verify = readline (cfg.max_pass, hidden='z')
        if password != verify:
          if warning ('verify must match, Press Ctrl+X to cancel', loc_email) == chr(24):
            return
          echo (cl())
        else: pass_ok = True

    while (email_ok < 2):
      email_ok = 0
      # email loop
      echo (pos(*loc_email) + cl() + color() + 'email address: ')
      for ch in hint:
        # must have @, level 1
        if ch == '@':
          email_ok = 1
        # must have '.' following @, level 2
        if email_ok == 1 and ch == '.':
          email_ok = 2
      if email_ok != 2:
        # allow user to opt-out of e-mail
        if warning ('valid email please, Ctrl+O to Opt out', loc_state) == chr(15):
          echo (pos(*loc_state) + cl() + color() + 'make your statement, then: ')
          statement = readline (45)
          if not statement:
            disconnect( )

    echo (pos(35, 23) + cl() + color() + 'Everything cool?')
    lr = leftrightclass([62,23])
    lr.left ()
    lr.run()
    if lr.isleft():
      u = User ()
      u.handle = user
      u.password = password
      u.location = location
      u.hint = hint
      u.add ()
      goto ('top', user)
