# ideally ..
#from curses import ACS_VLINE, ACS_HLINE
#                   ACS_ULCORNER, ACS_URCORNER,
#                   ACS_BLCORNER, ACS_BRCORNER
from output import echo
from strutils import ansilen

class AnsiWindow:

  def __init__(self, h, w, y, x, partial=False):
    from session import getsession
    self.h, self.w = h, w
    self.y, self.x = y, x
    self.partial = partial
    self.terminal = getsession().terminal

    self.glyphs = { \
      'top-left':       '+',
      'bot-left':       '+',
      'top-right':      '+',
      'bot-right':      '+',
      'left-vertical':  '|',
      'right-vertical': '|',
      'top-horizontal': '-',
      'bot-horizontal': '-',
      'fill':           ' ',
      'erase':          ' ', }

    self.colors = { \
      'highlight':  self.terminal.normal + self.terminal.red_reverse,
      'ghostlight': self.terminal.normal + self.terminal.brown_reverse,
      'lowlight':   self.terminal.normal,
      'active':     self.terminal.normal + self.terminal.bold_blue,
      'inactive':   self.terminal.normal + self.terminal.bold_white
    }

    self.emptyGlyph = dict([(k, ' ') for k in \
      'top-horizontal bot-horizontal right-vertical ' \
      'left-vertical bot-left bot-right top-left top-right'.split()])

  def border(self, glyphs=None, color=None):
    if color is not None:
      echo (color)
    if glyphs is None:
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
      echo (self.terminal.normal)

  def noborder(self):
    self.border (glyphs=self.emptyGlyph, color=self.terminal.normal)

  def highlight(self):
    self.border (color=self.colors['active'])

  def lowlight(self):
    self.border (color=self.colors['inactive'])

  def fill(self, ch=-1, eraseborder=False):
    if eraseborder:
      x, y, w, h = 0, 0, self.w, self.h
    else:
      x, y, w, h = 1, 1, self.w-2, self.h-1

    if ch == -1:
      ch = self.glyphs['fill']
    for y in range(y, h):
      echo (self.pos(x, y) + (ch*w))

  def clean(self):
    self.fill (ch=self.glyphs['erase'], eraseborder=True)

  def clear(self):
    self.fill (ch=self.glyphs['erase'])

  def resize(self, height=-1, width=-1, y=-1, x=-1):
    if height != -1: self.h = height
    if width != -1: self.w = width
    if y != -1: self.y = y
    if x != -1: self.x = x

  def isinview(self):
    return (self.x > 0 and self.x +self.w -1 <= getsession().width \
        and self.y > 0 and self.y +self.h -1 <= getsession().height)

  def iswithin(self, win):
    return (self.y >= win.y and self.y+self.h <= win.y+win.h \
        and self.x >= win.x and self.x+self.w <= win.x+win.w)

  def willfit(self, win):
    return (win.y >= self.y and win.y+win.h <= self.y+self.h \
        and win.x >= self.x and win.x+win.w <= self.x+self.w)

  def pos(self, x=-1, y=-1):
    return self.terminal.move \
        (y +self.y if y != None else 0,
         x +self.x if x != None else 0)

  def title(self, text, align='top'):
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
  timeout = False
  exit = False
  interactive = False
  debug = False
  silent = False

  KMAP = { \
    'refresh': ['\014'],
    'exit':    ['\030']
  }

  def bell(self, msg):
    # TODO: print msg at status line
    if not self.silent:
      echo ('\a')
    if self.debug:
      print msg
    return False

  def process_keystroke(self, key):
    if key in self.KMAP['refresh']: self.refresh ()
    if key in self.KMAP['exit']:    self.exit = True

  def run(self, key=None, timeout=None):
    pass
