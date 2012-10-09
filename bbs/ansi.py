"""
ANSI escape sequence helper class for 'The Progressive' BBS.
(c) Copyright 2006, 2007 Jeffrey Quast.
$Id: ansi.py,v 1.13 2010/01/01 09:27:58 dingo Exp $

These functions return the apropriate ansi sequence for the macro or function
name, these are not to be called directly, but to be passed and stored as
output, ie: echo (cls())

"""
__author__ = "Jeffrey Quast"
__contributors__ = []
__copyright__ = "Copyright (c) 2006, 2007 Jeffrey Quast"
__license__ = "ISC"
#from bbs.ascii import esc
esc = '\033'
import warnings
warnings.warn ("deprecated", DeprecationWarning, 3)
# attributes
NORMAL = 0
BOLD = BRIGHT = 1    # bold or bright
DIM = 2       # faint
ITALIC = 3    # rare
UNDERLINE = 4 # colored on unix text terminals
BLINK = SBLINK = 5    # slow blink
RBLINK = 6    # rapid blink
REVERSE = INVERSE = 7   # swap foreground and background
CONCEAL = 8   # rare
STRIKETHROUGH = 9 # rare

# colors
BLACK = 30
RED = 31
GREEN = 32
BROWN = 33
BLUE = 34
PURPLE = 35
CYAN = 36
GRAY = GREY = 37

# color tuple aliases (bright colors)
# ensure that * is used for these only.
# color(*LIGHTRED) + 'T' + color(RED)
LIGHTBLACK = DARKGRAY = DARKGREY = BRIGHTBLACK = LIGHTBLACK = (BLACK, BRIGHT)
BRIGHTRED = LIGHTRED = (RED, BRIGHT)
BRIGHTGREEN = LIGHTGREEN = (GREEN, BRIGHT)
YELLOW = BRIGHTBROWN = LIGHTBROWN = (BROWN, BRIGHT)
BRIGHTBLUE = LIGHTBLUE = (BLUE, BRIGHT)
PINK = BRIGHTPURPLE = LIGHTPURPLE = (PURPLE, BRIGHT)
BRIGHTCYAN = LIGHTCYAN = (CYAN, BRIGHT)
WHITE = BRIGHTGREY = LIGHTGREY = (GREY, BRIGHT)

## ANSI sequences based on CSI (Control Sequence Introducer)

CSI = esc + '['

# Position definitions

def up(rows=1):
  " move cursor up 'rows' lines"
  if rows == 1: return CSI + 'A'
  return CSI + str(int(rows)) + 'A'

def down(rows=1):
  " move cursor down 'rows' lines"
  if rows == 1: return CSI + 'B'
  return CSI + str(int(rows)) + 'B'

def right(cols=1):
  " move cursor 'cols' columns right"
  if cols == 1: return CSI + 'C'
  return CSI + str(int(cols)) + 'C'

def left(cols=1):
  " move cursor 'cols' columns left"
  if cols == 1: return CSI + 'D'
  return CSI + str(int(cols)) + 'D'

def bnl(rows=1):
  " move cursor to beginning of line 'rows' below"
  if rows == 1: return CSI + 'E'
  return CSI + str(int(rows)) + 'E'

def bpl(rows=1):
  " move cursor to beginning of line 'rows' up"
  if rows == 1: return CSI + 'F'
  return CSI + str(int(rows)) + 'F'

def bpl(col):
  " move cursor to column 'col'"
  return CSI + str(int(col)) + 'G'

# erase definitions

def clear(code=2):
  """
  clear screen, Codes:
    0. clear from cursor to end of screen
    1. clear from cursor to beginning of screen
    2. clear entire screen, moves cursor to upper-left on MSDOS only,
       use cls() to call clear() and pos() in sequence
  """
  return CSI + str(int(code)) + 'J'

def cl(code=2):
  """
  clear line,
  code 0: clears from cursor to end of line
  code 1: clears from cursor to beginning of line
  code 2: clears entire line at cursor position
  """
  return '%s%sK' % (CSI, code)
clearline = cl
eraseline = cl

def pgup(rows=1):
  """ scroll window up 'rows' lines """
  if rows == 1: return CSI + 'S'
  return CSI + str(int(rows)) + 'S'

def pgdown(rows=1):
  """ scroll window down 'rows' lines """
  if rows == 1: return CSI + 'T'
  return CSI + str(int(rows)) + 'T'

def sgr(n=-1, k=-1):
  """ SGR (Select Graphic Rendition), pass no parameters to reset SGR to
      default (usually GREY on BLACK). Also used to set attributes or colors """
  # Nonetype is -1 because None is same as NORMAL attribute!
  if k != -1 and n != -1:
    return CSI + str(int(n)) + ';' + str(int(k)) + 'm'
  elif n != -1:
    return CSI + str(int(n)) + 'm'
  else:
    return CSI + 'm' # reset
attr  = sgr
color = sgr

def pos(x=-1, y=-1):
  """
  Set cursor position to x, y. If no x/y parameters are provided,
  cursor will move to home position
  """
  if y != -1 and x != -1:
    return CSI + str(y) + ';' + str(x) + 'H'
  elif y != -1:
    return CSI + str(y) + 'H'
  else:
    return CSI + 'H' # 'home' position (equivalent to 1,1)

def linewrap(enable=True):
  if enable: return CSI + '7h'
  else: return CSI + '7l'

def bcolor(colorcode, attr=-1):
  " returns sequence for changing background color "
  return color((colorcode +10), attr)

def cursor_show():
  " returns sequence to show cursor "
  return CSI + '?25h'

def cursor_hide():
  " returns sequence to hide cursor"
  return CSI + '?25l'

def cursor_save():
  " save cursor position"
  return CSI + 's'

def cursor_restore():
  " restore cursor position"
  return CSI + 'u'

def cursor_attr_save():
  " save cursor position & attributes"
  return esc + '7'

def cursor_attr_restore():
  " restore cursor position & attributes"
  return esc + '8'

def cls():
  """ returns sequence for clearing screen
      and returning cursor to home row & column """
  return clear() + pos()

def scroll(start=-1, end=-1):
  " enable scrolling, optional row {start} to row {end} "
  if start != -1 and end != -1:
    return CSI + start + ';' + end + 'r'
  elif start != -1:
    return CSI + start + ';' 'r'
  elif end != -1:
    return CSI + end + 'r'
  else:
    return CSI + 'r'

def scroll_down():
  " display down one line "
  return esc + 'D'

def scroll_up():
  " display up one line "
  return esc + 'M'

#
# DEC Terminal sequences
#

def charset(ch='U'):
  """ sets character set,
      use 'U' for IBM VGA font,
      'B' for Latin-1 font,
      '0' for DEC font. """
  return esc + '(' + ch

def fls():
  """ returns sequence for filling screen
      (DEC tube alignment sequence)"""
  return esc + '#8'

def reset():
  """ resets terminal device. This will reset charset, SGR's, keymappings,
      all sorts of things. use this carefully, as the default behavior of
      the remote terminal us unknown! You may just want color() """
  return esc + 'c'


