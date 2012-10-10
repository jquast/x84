# ideally ..
#from curses import ACS_VLINE, ACS_HLINE
#                   ACS_ULCORNER, ACS_URCORNER,
#                   ACS_BLCORNER, ACS_BRCORNER
from output import echo
from strutils import ansilen

class AnsiWindow:

    def __init__(self, height, width, yloc, xloc, partial=False):
        from session import getsession
        self.height, self.width = height, width
        self.yloc, self.xloc = yloc, xloc
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
                glyphs['left-vertical'] = glyphs['right-vertical'] \
                        = glyphs['fill']

        for row in range(0, self.height):
            # top to bottom
            for col in range (0, self.width):
                # left to right
                if (col == 0) or (col == self.width - 1):
                    if (row == 0) and (col == 0):
                        # top left
                        echo (self.pos(col, row) + glyphs['top-left'])
                    elif (row == self.height - 1) and (col == 0):
                        # bottom left
                        echo (self.pos(col, row) + glyphs['bot-left'])
                    elif (row == 0):
                        # top right
                        echo (self.pos(col, row) + glyphs['top-right'])
                    elif (row == self.height - 1):
                        # bottom right
                        echo (self.pos(col, row) + glyphs['bot-right'])
                    elif not self.partial and col == 0:
                        # left vertical line
                        echo (self.pos(col, row) + glyphs['left-vertical'])
                    elif not self.partial and col == self.width - 1:
                        # right vertical line
                        echo (self.pos(col, row) + glyphs['right-vertical'])
                elif (row == 0):
                    echo (self.pos(col, row) + glyphs['top-horizontal'] \
                            * (self.width - 2) + glyphs['top-right'])
                    # top row
                    break
                elif (row == self.height - 1):
                    # bottom row
                    echo (self.pos(col, row) + glyphs['bot-horizontal'] \
                            * (self.width - 2) + glyphs['bot-right'])
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
            xloc, yloc, width, height = 0, 0, self.width, self.height
        else:
            xloc, yloc, width, height = 1, 1, self.width-2, self.height-1
        if ch == -1:
            ch = self.glyphs['fill']
        for yloc in range(yloc, height):
            echo (self.pos(xloc, yloc) + (ch * width))

    def clean(self):
        self.fill (ch=self.glyphs['erase'], eraseborder=True)

    def clear(self):
        self.fill (ch=self.glyphs['erase'])

    def resize(self, height=-1, width=-1, yloc=-1, xloc=-1):
        if height != -1: self.height = height
        if width != -1: self.width = width
        if yloc != -1: self.yloc = yloc
        if xloc != -1: self.xloc = xloc

    def isinview(self):
        return (self.xloc > 0
                and self.xloc +self.width -1 <= getsession().width
                and self.yloc > 0
                and self.yloc +self.height -1 <= getsession().height)

    def iswithin(self, win):
        return (self.yloc >= win.yloc
                and self.yloc + self.height <= win.yloc + win.height
                and self.xloc >= win.xloc
                and self.xloc + self.width <= win.xloc + win.width)

    def willfit(self, win):
        return (win.yloc >= self.yloc
                and win.yloc + win.height <= self.yloc + self.height
                and win.xloc >= self.xloc
                and win.xloc + win.w <= self.xloc + self.width)

    def pos(self, xloc=-1, yloc=-1):
        return self.terminal.move \
            (yloc +self.yloc if yloc != None else 0,
             xloc +self.xloc if xloc != None else 0)

    def title(self, text, align='top'):
        if align in ['top', 'bottom']:
            yloc = 0 if align == 'top' else self.height-1
            xloc = self.width /2 -(ansilen(text) /2)
            echo (self.pos(xloc, yloc) +text)

        # hmm ...
        elif align in ['left', 'right']:
            y = self.height /2 -(len(text) /2)
            if align == 'left': xloc = 0
            if align == 'right': xloc = self.width
            for num in range(0, len(text)):
                echo (self.pos(xloc,yloc + num) + text[n])
        else:
            assert False

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
