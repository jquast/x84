"""
Key mapping utilities for 'The Progressive' BBS.
Copyright (C) 2008 Jeffrey Quast.

Default instance of KeyClass imported by bbs.py. To use:

C{key = readkey()
if key == KEY.SPACE: next()}

keymappings::
 - ALTDEL: meta+backspace
 - INSERT, DELETE, HOME, END, PGUP, PGDOWN: a 1-byte character code


"""

keymap_default = { \
  'F1'       : chr(230),
  'F2'       : chr(231),
  'F3'       : chr(232),
  'F4'       : chr(233),
  'F5'       : chr(234),
  'F6'       : chr(235),
  'F7'       : chr(236),
  'F8'       : chr(237),
  'F9'       : chr(238),
  'F10'      : chr(239),
  'F11'      : chr(240),
  'F12'      : chr(241),
  'ALTDEL'   : chr(242),
  'SELECT'   : chr(243),
  'EXECUTE'  : chr(244),
  'FIND'     : chr(245),
  'INSERT'   : chr(246),
  'BREAK'    : chr(247),
  'PGDOWN'   : chr(248),
  'PGUP'     : chr(249),
  'UP'       : chr(250),
  'DOWN'     : chr(251),
  'LEFT'     : chr(252),
  'RIGHT'    : chr(253),
  'END'      : chr(254),
  'HOME'     : chr(255),
  'ENTER'    : chr(10),
  'SPACE'    : chr(32),
  'DELETE'   : chr(127),
  'ESC'      : chr(27),
  'ESCAPE'   : chr(27),
  'BACKSPACE': chr(8),
  'EXIT'     : chr(24), \
}

class KeyClass(dict):
  def __init__(self, keymap=None):
    if not keymap:
      keymap = keymap_default
    dict.__init__(self, keymap)
  def __setattr__ (self, key, value):
    self[key] = value
  def __getattr__ (self, key):
    try:
      return self[key]
    except KeyError:
      if keymap_default.has_key(key):
        return keymap_default[key]

# check if user has stored keyclass and return
KEY = KeyClass()
