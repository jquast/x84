"""
Pager class for X/84 BBS, http://1984.ws
$Id: pager.py,v 1.4 2010/01/06 19:45:52 dingo Exp $

This is used to display data in a scrollable AnsiWindow region. It handles
newline, word, and hard character breaks.

"""
__author__ = "Jeffrey Quast <dingo@1984.ws>"
__copyright__ = "Copyright (c) 2006, 2007, 2009 Jeffrey Quast <dingo@1984.ws>"
__license__ = "ISC"

import curses
from input import getch
from output import echo
from strutils import ansilen, chkseq, seqc
#from ansi import color
from ansiwin import InteractiveAnsiWindow

class ParaClass(InteractiveAnsiWindow):
    # represents the visible width and height, which may be smaller than the
    # AnsiWindow.w and AnsiWindow.h due to xpad and ypad respectively
    visibleWidth, visibleHeight = 0, 0

    # padd content buffer column or rows, by xpad or ypad resptively
    xpad, ypad = 0, 0

    # represents the row in the content buffer displayed at the top of the window
    top = 0

    # used to check if movement occured, requiring refresh
    lastTop = 0

    # col and row represent the x and y cursor position
    col, row = 0, 0

    # when digits are entered, they are queued and passed as an argument
    # to some movements, such as 10G for 'goto line #10'
    numAction = -1

    # default action keymap, each action contains a list of
    # keys that trigger that action.
    KMAP = { \
      'refresh': ['\014'],
      'goto':    ['G'],
      'gotopct': ['%'],
      'exit':    [curses.KEY_EXIT, 'q', 'Q'],
      'up':      [curses.KEY_UP, 'k'],
      'down':    [curses.KEY_DOWN, 'j'],
      'end':     [curses.KEY_END, 'L'],
      'home':    [curses.KEY_HOME, 'H'],
      'pgup':    [curses.KEY_PPAGE, curses.KEY_LEFT, 'h', 'K', 'b'],
      'pgdown':  [curses.KEY_NPAGE, curses.KEY_RIGHT, 'l', 'J', ' ', 'f'] \
    }

    debug = False

    def __init__(self, h, w, y, x, xpad=0, ypad=0):
        InteractiveAnsiWindow.__init__ (self, h, w, y, x)
        self.content = []
        self.xpad, self.ypad = xpad, ypad
        self.adjheight(h) # calculate self.visibleHeight
        self.adjwidth(w)  # calculate self.visibleWidth

    def changeRow(self, data, row=-1):
        """ Replace row.
            @data: Data that replaces
            @row: Target row to replace with data.
        """
        if row == -1:
            row = self.row
        while self.top +row >= len(self.content):
            self.content.append ('')
        self.content[self.top +row] = data

    def adjheight(self, height):
        """ Adjust the window height and recalculate visibleHeight.
            @var height: New window height.
        """
        self.h = height
        self.visibleHeight = self.h -(self.ypad *2)

    def adjwidth(self, width):
        """ Adjust the window width and recalculate visibleWidth.
            @var width: New window width.
        """
        self.w = width
        self.visibleWidth = self.w -(self.xpad *2)

    def getRow(self, row=-1):
        """ Retreive row from buffer.
            @var row: Target row. Default of -1 returns active row.
            @return: String of characters at target row.
        """
        if row == -1:
            row = self.row
        try:
            return self.content[self.top + row]
        except:
            raise ValueError, "Value out of range, top:%s, row:%s" % (self.top, row)

    def writeString(self, data, col=-1, row=-1):
        """ Echo string to pager window.
            @var data: String
            @var col: Column. Default of -1 is active column.
            @var row: Row. Default of -1 is active row.
        """
        if row == -1:
            row = self.row
        if col == -1:
            col = self.col
        echo (self.pos(self.xpad +col, self.ypad +row) +data)

    def add(self, data='', refresh=True, scrollToBottom=True):
        """ Lines wrap to new row at newlines, or word
            breaks at margin. If no spaces occur, a hard wrap occurs at margin.
            @var data: New buffer content as single string, containing newlines for row breaks.
            @var refresh: Set to False to disable drawing when complete
            @var scrollToBottom: Set to True to scroll to bottom after refresh
        """
        saveTop = self.top
        self.top = 0
        row = len(self.content)
        remaining = ''

        # replace all of the ansi.right(n) sequences with
        # erase to prevent 'bleeding' when scrolling
        data = seqc(data, ch=self.glyphs['erase'])

        while data.strip() or remaining.strip():
            nlset = [(x, z) for x, z in [(data.find(seq), seq) for seq in ['\r\n','\n']] if x != -1]
            if not nlset:
                nlpos, nlseq = -1, ''
            else:
                nlpos, nlseq = min(nlset)
            newline = nlpos != -1
            if newline and ansilen(data[:nlpos], max=self.visibleWidth+1) <= self.visibleWidth:
                remaining = data[nlpos+len(nlseq):] +remaining
                data = data[:nlpos]
            else:
                newline = False
            if newline or ansilen(data, max=self.visibleWidth+1) <= self.visibleWidth:
                # write data to content  buffer
                self.changeRow(data, row)
                data = remaining
                remaining = ''
                row += 1
                continue

            wordbreak = data[1:].find(' ') != -1
            pos, nextSeq, c = 0, 0, 0
            while True:
                if wordbreak:
                    # break at nearest word to margin
                    npos = data[pos+1:].find(' ')
                    if npos == -1:
                        break
                    if ansilen(data[:pos +npos +1]) >= self.visibleWidth-1:
                        pos += 1 # forward past ' '
                        break
                    pos += npos +1
                else:
                    # break on margin
                    if nextSeq <= pos:
                        nextSeq = pos +chkseq(data[pos:])
                    if nextSeq <= pos:
                        c += 1
                        if c == self.visibleWidth -1:
                            break
                    pos += 1
            remaining = data[pos:] + remaining
            data = data[:pos]
        self.top = saveTop
        if refresh:
            if scrollToBottom:
                self.end (silent=True)
            self.refresh ()

    def update(self, data='', refresh=True, scrollToBottom=False):
        """ Update content buffer.
            @var data: New buffer content as single string, containing newlines for row breaks.
            @var refresh: Set to False to disable drawing when complete
            @var scrollToBottom: Set to True to scroll to bottom after refresh
        """
        self.adjscroll (0)
        self.row, self.top = 0, 0
        self.content = []
        self.add (data, refresh, scrollToBottom)

    def drawRow(self, row=-1):
        """ Draw visual row in buffer
            @var: Draw this row. Default of -1 draws current row.
        """
        if row == -1:
            row = self.row
        dataline = self.getRow(row)
        self.writeString(dataline
            +self.glyphs['erase']*(self.visibleWidth-ansilen(dataline)), 0, row)

    def data(self):
        """ @return: Data in content buffer as one string, each row joined by newline """
        return '\n'.join(self.content)

    def refresh(self, startRow=0):
        """ Refresh window.
            @var startRow: Refresh only from this visible row on
        """
        echo (self.terminal.normal)
        row = 0
        for row, line in enumerate(self.content[self.top : self.top +self.visibleHeight]):
            if row < startRow:
                continue
            self.drawRow (row)
        while row < self.visibleHeight -1:
            # clear to end of window
            row += 1
            self.writeString(self.glyphs['erase']*self.visibleWidth, 0, row)
        self.lastTop = self.top
        return True

    def scrollIndicator(self):
        """ returns one of '', '-', '+', or '+/-' to indicate scroll availability """
        # XXX for now, only return '+/-'
        if len(self.content) >self.visibleHeight:
            return '+/-'
        return ''

    def adjscroll(self, row):
        """ Adjust scroll position.
            @var row: Row number representing position in buffer to display at top of visible window.
            @return True: if scroll position is changed
        """
        self.lastTop = self.top
        # bounds checking
        while row < 0:
            row += 1
        while row > len(self.content) -1:
            row -= 1
        if self.top != row:
            self.top = row
            self.row = self.top +self.row
            return True
        return False

    def up(self, n=-1):
        """ Scroll up by row.
            @var n: Number of rows. Default of -1 moves one row.
            @return: True if not at top
        """
        if n == -1: n=1
        if self.top > 0 and self.adjscroll(self.top -n):
            return self.refresh ()
        self.bell ('cannot scroll up: at beginning')
        return False

    def down(self, n=-1):
        """ Scroll down by row.
            @var n: Number of rows. Default of -1 moves one row.
            @return: True if not at bottom
        """
        if n == -1: n=1
        if self.top < len(self.content) -self.visibleHeight:
            self.adjscroll(self.top +n)
            return self.refresh()
        return self.bell ('cannot scroll down: at bottom')

    def gotopct(self, n=-1):
        """ Goto location of buffer by relative percent.
            @var n: value as percent, ie: 50% == int(50).
            @return: True if window is scrolled.
        """
        if n == -1:
            return self.bell ('Must specify digit for goto-percent')
        return self.goto(int((len(self.content)-1)*(float(n)*.01)))

    def goto(self, n=-1):
        """ Goto line number.
            @var: Destination line. Default of -1 moves to end.
            @return: True if window is scrolled.
        """
        if n == -1:
            return self.end ()
        if n >= 0 and n <= len(self.content)-1:
            if n > len(self.content) -self.visibleHeight:
                n = len(self.content) -self.visibleHeight
            if self.adjscroll (n):
                return self.refresh ()
        else:
            return self.end ()
        return False

    def home(self, silent=True):
        """ Scroll to top.
            @return True if window is scrolled.
        """
        if self.top > 0 and self.adjscroll(0):
            return self.refresh ()
        return not silent or self.bell ('cannot home: at beginning')

    def end(self, silent=False):
        """ Scroll to bottom.
            @return: True if window is scrolled.
        """
        if (len(self.content) -self.visibleHeight < 0):
            self.adjscroll (0)
            return self.refresh ()
        elif (self.adjscroll (len(self.content) -self.visibleHeight)):
            return self.refresh ()
        if not silent:
            return self.bell ('cannot end: at bottom')
        return False

    def pgup(self, n=-1):
        """ Scroll up by page.
            @var n: Number of pages. Default of -1 scrolls one page.
            @return: True if window is scrolled.
        """
        if n == -1: n=1
        if self.top > self.visibleHeight +1 and self.adjscroll(n *(self.top -self.visibleHeight +1)):
            return self.refresh ()
        elif self.top > 0 and self.adjscroll (0):
            return self.refresh ()
        self.bell ('cannot page up: at beginning')
        return False

    def pgdown(self, n=-1):
        """ Scroll down by page.
            @var n: Number of pages. Default of -1 scrolls one page.
            @return: True if window is scrolled.
        """
        if n == -1: n=1
        if (self.top < len(self.content) -1 -((self.visibleHeight -1)*2) \
          and self.adjscroll(n *(self.top +self.visibleHeight -1))):
            return self.refresh ()
        elif (self.top < len(self.content) -1 -self.visibleHeight +1 \
          and self.adjscroll( n*(len(self.content) -1 -self.visibleHeight +1))):
            return self.refresh ()
        self.bell ('cannot page down: at bottom')
        return False

    def fixate(self, mode=0):
        """ Fixate cursor at current position in window,
            @var mode: set to -1 for position on last character,
                       or 0 for after last character.
            @return: True
        """
        echo (self.pos(self.xpad +self.col +mode, self.ypad +self.row))
        return True

    def adjcursor_x(self, column):
        """ Adjust position of cursor to value of column.
            @return: True if position is changed
        """
        end = ansilen(self.getRow())
        if column > end:
            # out of x range, force cursor to end of line
            column = end
        elif column < 0:
            column = 0
        if column != self.col:
            self.col = column
            return True
        return False

    def adjcursor_y(self, row):
        """ Adjust position of cursor to value of row.
            @return: True if position is changed or window is scrolled.
        """
        adjusted = False
        while row >= self.visibleHeight:
            row -= 1
            self.adjscroll (self.top +1)
            adjusted = True
        while row < 0:
            row += 1
            self.adjscroll (self.top -1)
            adjusted = True
        if row != self.row:
            self.row = row
            # call adjcursor_x, to ensure we are within bounds
            self.adjcursor_x (self.col)
            return True
        return adjusted

    def cursor_left(self, n=1):
        """ position cursor one column left.
            @return: True if not already at left margin.
        """
        if self.adjcursor_x (self.col +(n *-1)):
            return self.fixate ()
        return self.bell('cannot move left: at left margin')

    def cursor_right(self, n=1):
        """ position cursor one column right.
            @return: True if not already at right margin.
        """
        if self.adjcursor_x (self.col +n):
            return self.fixate ()
        return self.bell('cannot move right: at right margin')

    def cursor_home(self):
        """ position cursor at far left margin.
            @return: True if not already at left margin.
        """
        if self.adjcursor_x (0):
            return self.fixate()
        return self.bell('cannot move home: at left margin')

    def cursor_end(self):
        """ position cursor at far right margin.
            @return: True if not already at right margin.
        """
        if self.adjcursor_x (ansilen(self.getRow())):
            return self.fixate()
        return self.bell('cannot move end: at right margin')

    def cursor_up(self, n=-1):
        """ position cursor one row up
            @return: True on success
        """
        if n == -1: n=1
        if self.adjcursor_y (self.row +(n *-1)):
            self.adjcursor_x (self.col)
            if self.lastTop != self.top:
                self.refresh ()
            return self.fixate ()
        return self.bell('cannot move up: at top')

    def cursor_down(self, n=-1):
        """ position cursor one row down
            @return: True on success
        """
        if n == -1: n=1
        if self.adjcursor_y (self.row +n):
            self.adjcursor_x (self.col)
            if self.lastTop != self.top:
                self.refresh ()
            return self.fixate ()
        return self.bell('cannot move down: at bottom')

    def cursor_pgup(self, n=-1):
        """ position cursor one page up.
            @return: True on success.
        """
        if n == -1: n=1
        if self.pgup(n) or self.adjcursor_y (0):
            return self.fixate ()
        return False

    def cursor_pgdown(self, n=-1):
        """ position cursor one page down.
            @return: True on success.
        """
        if n == -1: n=1
        if self.pgdown(n) \
        or self.adjcursor_y (self.visibleHeight -1):
            return self.fixate ()
        return False

    def process_keystroke(self, key):
        """ Process the keystroke received by run method and take action.
        """
        if self.debug and key == '\003':
            print self.data()
        if   key in self.KMAP['refresh']: self.refresh ()
        elif key in self.KMAP['goto']:    self.goto    (self.numAction)
        elif key in self.KMAP['gotopct']: self.gotopct (self.numAction)
        elif key in self.KMAP['up']:      self.up      (self.numAction)
        elif key in self.KMAP['down']:    self.down    (self.numAction)
        elif key in self.KMAP['home']:    self.home    (silent=False)
        elif key in self.KMAP['end']:     self.end     (silent=False)
        elif key in self.KMAP['pgup']:    self.pgup    (self.numAction)
        elif key in self.KMAP['pgdown']:  self.pgdown  (self.numAction)
        elif key in self.KMAP['exit']:    self.exit = True
        else:
            if self.debug:
                print 'edit: throwing out key: ' +str(ord(key))
        # start numAction over
        self.numAction = -1

    def run(self, key=None, timeout=None):
        """ The entry point for working with the pager window.
            @var key:
              pass in optional keystroke, otherwise it is read from input.
            @var timeout:
              return None after that time elapsed, or block indefinitely if unset.
        """
        self.timeout, self.exit = False, False
        while True:
            if self.lastTop == -1:
                self.refresh ()
                self.fixate ()
            if not key:
                key = getch (timeout)
                self.timeout = (not key) # Boolean: True if we timed out
            self.lastkey = key
            self.process_keystroke (key)
            if self.interactive:
                return key
            if self.exit:
                return
            key = None
        return
