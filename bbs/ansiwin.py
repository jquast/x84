"ANSI window class for 'The Progressive' BBS."
__author__ = "Jeffrey Quast <dingo@1984.ws>"
__copyright__ = "Copyright (c) 2006, 2007, 2008, 2009 Jeffrey Quast"
__license__ = "ISC"
__version__ = "$Id: ansiwin.py,v 1.2 2009/05/31 16:11:26 dingo Exp $ #"

from ascii import bel
import ansi
import types
from output import echo
from strutils import ansilen

class AnsiWindow():
  """
  AnsiWindow is a windowing class for mainting virtual positions within the
  client screen. This class should be subtyped for all user interface dialogs.

  The low-level function .pos() recieves a window-relative xy position,
  and returns an L{ansi.pos} sequence for the absolute screen position,
  to be used by sub-typed classes with L{bbs.echo}.

  """

  " @cvar: set True to display only horizontal row of border "
  partial = False

  # set to false for less screen draws, 9600bps is recommened cutoff for highdef
  highdef= True
  dirty= True

  def __init__(self, h, w, y, x, partial=False):
    """
    Construct window instance at geometry h, w, y, x.

    @todo: Use 'height' and 'width' instead of h and w?
    """
    self.h, self.w, self.y, self.x = h, w, y, x
    self.partial = partial

    self.glyphs= { \
      'top-left':  '\xDA',
      'bot-left':  '\xC0',
      'top-right': '\xBF',
      'bot-right': '\xD9',
      'left-vertical':  '\xB3',
      'right-vertical': '\xB3',
      'top-horizontal': '\xC4',
      'bot-horizontal': '\xC4',
      'fill':  ' ',
      'erase': ' ', }

    # a short note on backlighting. With terminals that do not support color,
    # using a background color and foreground color have no distinction, and will
    # not appear as highlighting. The most compatible form of highlighting is to
    # use ansi.color() + ansi.attr(ansi.INVERSE), which still highlights on
    # monochrome terminals.
    self.colors= { \
      'highlight':  ansi.color() + ansi.color(ansi.RED) + ansi.attr(ansi.INVERSE),
      'ghostlight': ansi.color() + ansi.color(ansi.BROWN) + ansi.attr(ansi.INVERSE),
      'lowlight':   ansi.color(),
      'active':     ansi.color() + ansi.color(*ansi.LIGHTBLUE),
      'inactive':   ansi.color() + ansi.color(ansi.GREY),
    }

    # glyphs for erasing borders
    self.emptyGlyph = { \
      'top-horizontal': ' ',
      'bot-horizontal': ' ',
      'right-vertical':  ' ',
      'left-vertical':  ' ',
      'bot-left':    ' ',
      'bot-right':   ' ',
      'top-left':       ' ',
      'top-right':      ' ', }

  def setTheme(self, theme):
    """
    Set a new theme.
    """
    if not type(theme) == types.DictionaryType:
      raise ValueError, "theme must be dictionary"
    if not theme.values() or not type(theme.values()[0]) == types.DictionaryType:
      raise ValueError, "theme dictionary values must also be dictionary"

    for key in theme.keys():
      if not hasattr(self, key):
        raise OverflowError, "setTheme denied new theme value: %s" % (key)

      if type(getattr(self,key)) != types.DictionaryType:
        raise OverflowError, "setTheme denied obliteration of " \
                             "non-theme type: %s by: %s" % (type(key), theme)

      # blend in new settings
      for subkey in theme[key].keys():
        getattr(self, key)[subkey] = theme[key][subkey]


  def border(self, glyphs=None, color=None):
    """
    @summary: Draw a rectangle on dimensions of window border at xy coords (0,0) to
    (width,height). A bordered window should refer to the first visible
    position as 1,1.

    @param glyphs: a dictionary of alternate border glyphs.
    @param color: border color as ansi sequence.

    @todo: Allow C{self.border} values to be two dimensional ansi art glyphs.
    """
    if color:
      echo (color)
    if not glyphs:
      glyphs = self.glyphs.copy()
      if self.partial:
        glyphs['left-vertical'] = glyphs['right-vertical'] = glyphs['fill']

    for row in range(0, self.h):
      # top to bottom
      for col in range (0, self.w):
        # left to right
        if (col == 0) or (col == self.w -1):
          if (row == 0) and (col == 0):
            # top left
            echo (self.pos(col, row) + glyphs['top-left'])
          elif (row == self.h -1) and (col == 0):
            # bottom left
            echo (self.pos(col, row) + glyphs['bot-left'])
          elif (row == 0):
            # top right
            echo (self.pos(col, row) + glyphs['top-right'])
          elif (row == self.h -1):
            # bottom right
            echo (self.pos(col, row) + glyphs['bot-right'])
          elif not self.partial and col == 0:
            # left vertical line
            echo (self.pos(col, row) + glyphs['left-vertical'])
          elif not self.partial and col == self.w -1:
            # right vertical line
            echo (self.pos(col, row) + glyphs['right-vertical'])
        elif (row == 0):
          echo (self.pos(col, row) + glyphs['top-horizontal'] *(self.w -2) +glyphs['top-right'])
          # top row
          break
        elif (row == self.h -1):
          # bottom row
          echo (self.pos(col, row) + glyphs['bot-horizontal'] *(self.w -2) +glyphs['bot-right'])
          break
    if color:
      echo (ansi.color())

  def noborder(self):
    """
    erase window border.
    """
    self.border (glyphs=self.emptyGlyph, color=ansi.color())

  def highlight(self):
    """
    Draw L{border} using window highlight color from theme, C{self.colors['active']}."

    @todo: rename to active()
    """
    self.border (color=self.colors['active'])

  def lowlight(self, partial=False):
    """
    Draw L{border} using window lowlight color from theme, C{self.colors['inactive']}."

    @todo: rename to inactive()
    """
    self.border (color=self.colors['inactive'])

  def fill(self, ch=-1, eraseborder=False):
    """
    Fill window with character ch.
    @param ch: fill character. C{glyphs['fill']} is used unless specified.
    @param eraseborder: When True, erase also the window border.
    """
    if eraseborder:
      x, y, w, h = 0, 0, self.w, self.h
    else:
      x, y, w, h = 1, 1, self.w-2, self.h-1

    if ch == -1:
      ch = self.glyphs['fill']
    for y in range(y, h):
      echo (self.pos(x, y) + (ch*w))

  def clean(self):
    """
    Erase entire window.
    """
    self.fill (ch=self.glyphs['erase'], eraseborder=True)

  def clear(self):
    """
    Clear contents of window (keep border).
    """
    self.fill (ch=self.glyphs['erase'])

  def resize(self, height=-1, width=-1, y=-1, x=-1):
    """
    Resize window dimensions to any mutually exclusive argument height, width, y, and x.
    """
    if height != -1: self.h = height
    if width != -1: self.w = width
    if y != -1: self.y = y
    if x != -1: self.x = x

  def isinview(self):
    """
    Check if window placementfits in end-user's entire display.
    @returns: True if entire window fits within display
    @todo: use session.screen_height and session.screen_width
    """
    return (self.x > 0 and self.x +self.w -1 <= session().width \
        and self.y > 0 and self.y +self.h -1 <= session().height)

  def iswithin(self, win):
    """
    Check if target window fits within our window.
    @param win: target window.
    @returns: True if target window fitself.
    """
    return (self.y >= win.y and self.y+self.h <= win.y+win.h \
        and self.x >= win.x and self.x+self.w <= win.x+win.w)

  def willfit(self, win):
    """
    Check if our window fits in target window.
    @param win: target window.
    @returns: True if our window fitself.
    """
    return (win.y >= self.y and win.y+win.h <= self.y+self.h \
        and win.x >= self.x and win.x+win.w <= self.x+self.w)

  def pos(self, x=-1, y=-1):
    """
    Return ansi sequence for absolute screen position for relative x, y
    position within window.

    @param x: horizontal coordinate right of (0,0) position of window
    @param y: vertical coordinate downward from (0,0) position of window
    @returns: absolute screen position of window

    @todo: track and allow pos() to restore cursor position after refresh.
      This could theoretically be tracked by evaluating the resume buffer,
      but a less expensive solution is necessary for a minor feature.
    """
    return (ansi.pos (x +self.x, y +self.y))

  def title(self, text, align='top'):
    """
    Display text aligned over border region of window.

    @param text: ansi string
    @param align: alignment, one of 'top', 'bottom', 'left', or 'right'

    @note: ANSI sequences text does not work with left or right alignment.
    """
    if align in ['top', 'bottom']:
      if align == 'top':
        y = 0
      if align == 'bottom':
        y = self.h-1
      x = self.w /2 -(ansilen(text) /2)
      echo (self.pos(x, y) +text)

    elif align in ['left', 'right']:
      y = self.h /2 -(len(text) /2)
      if align == 'left': x = 0
      if align == 'right': x = self.w
      for n in range(0, len(text)):
        echo (self.pos(x,y+n) +text[n])

class InteractiveAnsiWindow(AnsiWindow):
  # set to True when a timeout value is passed to run and that number of
  # seconds elapses without keypress.
  timeout = False

  # set to True when an exit key is pressed
  exit = False

  # The .run() method returns immediately after an action is taken or
  # a timeout occurs. Otherwise, .run blocks until .exit is flipped
  interactive = False

  # debug prints at least messages on bell for now,
  debug = False

  # supress sending ^G to output when the bell method is called
  silent = False

  KMAP = { \
    'refresh': ['\014'],
    'exit':    ['\030']
  }

  def bell(self, msg):
    """ Ring bell.
        @var msg: Currently displayed to console in debug mode, may be displayed in status line.
    """
    # TODO: print msg at status line
    if not self.silent:
      echo (bel)
    if self.debug:
      print msg
    return False

  def process_keystroke(self, key):
    """ Process the keystroke received by run method and take action.
    """
    if key in self.KMAP['refresh']: self.refresh ()
    if key in self.KMAP['exit']:    self.exit = True

  def run(self, key=None, timeout=None):
    """ The entry point for working with the pager window.
        @var key:
          pass in optional keystroke, otherwise it is read from input.
        @var timeout:
          return None after that time elapsed, or block indefinitely if unset.
    """
    pass

