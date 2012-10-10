"""
Horizontal Line Editor class for X/84 BBS, http://1984.ws
$Id: editor.py,v 1.1 2009/05/18 01:24:16 dingo Exp $

A single line editor that scrolls horizontally

"""
__author__ = "Jeffrey Quast <dingo@1984.ws>"
__copyright__ = "Copyright (c) 2006, 2007, 2009 Jeffrey Quast <dingo@1984.ws>"
__license__ = "ISC"

from output import echo
from input import getch
from ansiwin import InteractiveAnsiWindow

class HorizEditor(InteractiveAnsiWindow):

    # horizontal shifting control
    shift, lastShift = 0, -1

    # limit user input to this length
    maxlen = 0

    # becomes True when return is pressed
    enter = False

    # cursor position within ansi window
    col = 0

    # scroll horizontally by this amount as a relative percent of visible window
    shiftPercent = 35

    def __init__(self, width, yloc, xloc, xpad=0, maxlen=0):
        self.content = ''
        self.xpad = xpad
        self.maxlen = maxlen
        # calculate self.visibleWidth
        self.adjwidth (width)
        InteractiveAnsiWindow.__init__ (self, height=3, width=width, yloc=yloc,
                xloc=xloc)
        self.KMAP = { \
          'refresh': [self.terminal.KEY_REFRESH],
          'erase':   [self.terminal.KEY_BACKSPACE],
          'enter':   [self.terminal.KEY_ENTER],
          'exit':    [self.terminal.KEY_EXIT]
        }

    def adjwidth(self, width):
        """ Adjust the window width and recalculate visibleWidth.
            @var width: New window width.
        """
        self.w = width
        self.visibleWidth = self.w -(self.xpad *2)
        self.shiftCol = int(float(self.visibleWidth)*(self.shiftPercent*.01))

    def data(self):
        """ @return: Data in content buffer as one string, each row joined by newline """
        return self.content

    def writeString(self, data, col=-1):
        """ Echo string to pager window.
            @var data: String
            @var col: Column. Default of -1 is active column.
        """
        if col == -1:
            col = self.col
        echo (self.pos(xloc=self.xpad +col, yloc=1) +data)

    def update(self, data='', refresh=True):
        """ Update content buffer.
            @var refresh: Set to refresh on update.
            @return: True when refreshed.
        """
        self.content = ''
        self.col, self.shift = 0, 0
        for ch in data:
            self.add (ch)
        if refresh: self.refresh ()

    def add(self, ch, refresh=True):
        """ Add character to content buffer, scroll as necessary.
            @var ch: Character to add.
        """
        if self.maxlen and len(self.content) == self.maxlen:
            return self.bell ('character maximum reached')

        self.content += ch
        if self.col >= (self.visibleWidth):
            self.shift += self.shiftCol
            self.col -= self.shiftCol-1
            if refresh:
                self.refresh ()
        else:
            if refresh:
                self.fixate (-1)
                self.writeString(ch)
            self.col += 1

    def erase(self):
        """ Remove character from end of content buffer, scroll as necessary.
        """
        if not len(self.content):
            return self.bell ('at left margin')
        self.content = self.content[:-1]
        if self.shift and self.col < (self.visibleWidth -self.shiftCol):
            self.shift -= self.shiftCol
            self.col += self.shiftCol
            self.refresh ()
            self.col -= 1
        else:
            self.col -= 1
        self.fixate ()
        self.writeString(' \b')

    def refresh(self):
        """ Refresh window.
            @var startCol: Refresh only from this column
        """
        from bbs.session import getsession
        term = getsession().terminal
        echo (term.normal)
        nextSeq, c = 0, 0
        data = self.data()
        self.lastShift = self.shift
        for n in range(len(data)):
            if c > (self.visibleWidth -self.shiftCol):
                # shift window horizontally by self.shiftCol characters
                c -= self.shiftCol
                self.shift += self.shiftCol
        data = data[self.shift:]
        self.writeString (data +(self.visibleWidth -len(data))*self.glyphs['erase'], 0)
        self.fixate ()

    def fixate(self, mode=0):
        """ Fixate cursor at current position in window,
            @var mode: set to -1 for position on last character,
                       or 0 for after last character.
            @return: True
        """
        echo (self.pos(xloc=self.xpad +self.col +mode, yloc=1))
        return True

    def process_keystroke(self, key):
        """ Process the keystroke received by run method and take action.
        """
        if key in self.KMAP['refresh']:   self.refresh ()
        elif key in self.KMAP['exit']:    self.exit = True
        elif key in self.KMAP['erase']:   self.erase ()
        elif key in self.KMAP['enter']:   self.enter = True
        else:
            self.add (key)

    def run(self, key=None, timeout=None):
        """ The entry point for working with the pager window.
            @var key:
              pass in optional keystroke, otherwise it is read from input.
            @var timeout:
              return None after that time elapsed, or block indefinitely if unset.
        """
        self.enter, self.timeout, self.exit = False, False, False
        while True:
            if self.lastShift == -1:
                self.refresh ()
                self.fixate ()
            if not key:
                key = getch (timeout)
                self.timeout = (not key) # Boolean: True if we timed out
            self.lastkey = key
            self.process_keystroke (key)
            if self.interactive:
                return key
            if self.exit or self.enter:
                break
            key = None
