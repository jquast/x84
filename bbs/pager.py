"""
Pager class for x/84, http://github.com/jquast/x84/
"""
import textwrap

import bbs.output
import bbs.ansiwin

NETHACK_KEYSET = {
        'refresh': [unichr(12), ],
        'home': [u'y', ],
        'end': [u'n', ],
        'pgup': [u'h', u'K'],
        'pgdown': [u'l', u'J'],
        'up': [u'k', ],
        'down': [u'j', ],
        'exit': [u'q', u'Q'],
        }

class Pager(bbs.ansiwin.AnsiWindow):
    _xpadding = 0
    _ypadding = 0
    _col = 0
    _row = 0
    _position = 0
    _position_last = 0
    _moved = False
    _quit = False
    content = list ()
    keyset = dict ()

    def __init__(self, height, width, yloc, xloc):
        bbs.ansiwin.AnsiWindow.__init__ (self, height, width, yloc, xloc)
        self.init_keystrokes ()

    @property
    def moved(self):
        return self._position != self._position_last

    @property
    def quit(self):
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit

    @property
    def position_last(self):
        """
        Previous position before last move
        """
        return self._position_last

    @property
    def position(self):
        """
        Returns the row in the content buffer displayed at top of window.
        """
        return self._position

    @position.setter
    def position(self, pos):
        #pylint: disable=C0111
        #         Missing docstring
        self._position_last = self.position
        self._position = pos
        if self.position < 0:
            self.position = 0
        bottom = max(0, len(self.content) - self._visible_height)
        if self.position > bottom:
           self.position = bottom

    @property
    def _visible_width(self):
        """
        Visible width of lightbar after accounting for horizontal padding.
        """
        return self.width - (self.xpadding * 2)

    @property
    def _visible_height(self):
        """
        Visible height of lightbar after accounting for vertical padding.
        """
        return self.height - (self.ypadding * 2)

    @property
    def xpadding(self):
        """
        Horizontal padding of window border
        """
        return self._xpadding

    @xpadding.setter
    def xpadding(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._xpadding = value

    @property
    def ypadding(self):
        """
        Horizontal padding of window border
        """
        return self._ypadding

    @ypadding.setter
    def ypadding(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._ypadding = value


    def init_keystrokes(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override or inherit this method to create a common color and graphic
        set.
        """
        from bbs.session import getsession
        self.keyset = NETHACK_KEYSET
        term = getsession().terminal
        if u'' != term.KEY_HOME:
            self.keyset['home'].append (term.KEY_HOME)
        if u'' != term.KEY_END:
            self.keyset['end'].append (term.KEY_END)
        if u'' != term.KEY_PPAGE:
            self.keyset['pgup'].append (term.KEY_PPAGE)
        if u'' != term.KEY_NPAGE:
            self.keyset['pgdown'].append (term.KEY_NPAGE)
        if u'' != term.KEY_UP:
            self.keyset['up'].append (term.KEY_KEY_UP)
        if u'' != term.KEY_DOWN:
            self.keyset['down'].append (term.KEY_DOWN)
        if u'' != term.KEY_EXIT:
            self.keyset['exit'].append (term.KEY_EXIT)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by run method and return terminal
        sequence suitable for refreshing when that keystroke modifies the
        window.
        """
        if keystroke in self.keyset['refresh']:
            return self.refresh ()
        elif keystroke in self.keyset['up']:
            return self._up ()
        elif keystroke in self.keyset['down']:
            return self._down ()
        elif keystroke in self.keyset['home']:
            return self._home ()
        elif keystroke in self.keyset['end']:
            return self._end ()
        elif keystroke in self.keyset['pgup']:
            return self._pgup ()
        elif keystroke in self.keyset['pgdown']:
            return self._pgdown ()
        elif keystroke in self.keyset['exit']:
            self._quit = True
            return u''
        return u''

    def _home(self):
        """
        Scroll to top.
        """
        self.position = 0
        if self.moved:
            return self.refresh ()
        return u''

    def _end(self, silent=False):
        """
        Scroll to bottom.
        """
        self.position = len(self.content) - self._visible_height
        if self.moved:
            return self.refresh ()
        return u''

    def _pgup(self, num=1):
        """
        Scroll up ``num`` pages.
        """
        self.position -= (num * (self._visible_height))
        return self.refresh() if self.moved else u''

    def _pgdown(self, num=1):
        """
        Scroll down ``num`` pages.
        """
        self.position += (num * (self._visible_height))
        return self.refresh() if self.moved else u''

    def _down(self, num=1):
        """
        Scroll down ``num`` rows.
        """
        self.position -= num
        return self.refresh() if self.moved == True else u''

    def _up(self, num=1):
        """
        Scroll up ``num`` rows.
        """
        self.position += num
        return self.refresh() if self.moved == True else u''

    def refresh(self, start_row=0):
        """
        Return unicode string suitable for refreshing pager window, starting at
        row ``start_row``.
        """
        term = bbs.session.getsession().terminal
        rstr = u''
        row = 0
        visc = self.content[self.position:self.position + self._visible_height]
        for row, line in enumerate(visc):
            if row < start_row:
                continue
            rstr += self.pos (row, self.xpadding)
            rstr += line
        while row < self._visible_height -1:
            # clear to end of window
            row += 1
            rstr += self.pos (row, self.xpadding)
            rstr += u' ' * self._visible_width
        rstr += term.normal
        return rstr

    def update(self, unibytes):
        """
        Update content buffer with new unicode bytes. If unichr(27) (escape) is
        found in unibytes, it is processed according as ansi art.
        """
        if unichr(27) in unibytes:
            self._update_ansi (unibytes)
        else:
            # standard ascii uses the python 'textwrap' module :D
            self.content = textwrap.wrap(unibytes, self._visible_width)
        return self.refresh()

    def _update_ansi(self, unibytes=u''):
        """
        Update content buffer with new ansi art.
        """
        save_pos = self.position
        self.position = 0
        row = len(self.content)
        remaining = u''
        # replace all of the ansi.right(n) sequences with
        # ' ' to prevent 'bleeding' over 'ghost' glyphs when
        # scrolling (at the cost of some extra bytes).
        unibytes = bbs.output.Ansi(unibytes).seq_fill()

        # my own, ansi-safe textwrap ..
        while unibytes.strip() or remaining.strip():
            nlset = [(x, z) for x, z in [(unibytes.find(seq), seq) for seq in
                ['\r\n','\n']] if x != -1]
            if 0 == len(nlset):
                nlp, nlseq = -1, u''
            else:
                nlp, nlseq = min(nlset)
            newline = nlp!= -1
            if (newline and max(self._visible_width + 1,
                len(bbs.output.Ansi(unibytes[:nlp]))) <= self._visible_width):
                remaining = unibytes[nlp + len(nlseq):] + remaining
                unibytes = unibytes[:nlp]
            else:
                newline = False
            if (newline or max(self._visible_width + 1,
                len(bbs.output.Ansi(unibytes))) <= self._visible_width):
                # write unibytes to content  buffer
                while row >= len(self.content):
                    self.content.append (u'')
                self.content[row] = unibytes
                unibytes = remaining
                remaining = u''
                row += 1
                continue
            wordbreak = unibytes[1:].find(' ') != -1
            pos = 0
            nxt = 0
            col = 0
            while True:
                if wordbreak:
                    # break at nearest word to margin
                    npos = unibytes[pos+1:].find(' ')
                    if npos == -1:
                        break
                    if (len(bbs.output.Ansi(unibytes[:pos + npos + 1]))
                            >= self._visible_width-1):
                        pos += 1 # forward past ' '
                        break
                    pos += npos +1
                else:
                    # break on margin
                    if nxt <= pos:
                        nxt = pos + bbs.output.Ansi(unibytes[pos:]).seqlen()
                    if nxt <= pos:
                        col += 1
                        if col == self._visible_width -1:
                            break
                    pos += 1
            remaining = unibytes[pos:] + remaining
            unibytes = unibytes[:pos]
        self.position = save_pos
        return self.refresh ()

#    def update_row(self, unibytes, row=None):
#        """
#        Replace current row, or specified by index ``row``.
#        """
#        if row is None:
#            row = self._row
#        while self.position + row >= len(self.content):
#            self.content.append (u'')
#        self.content[self.position + row] = unibytes
#
#    def writeString(self, data, col=-1, row=-1):
#        """ Echo string to pager window.
#            @var data: String
#            @var col: Column. Default of -1 is active column.
#            @var row: Row. Default of -1 is active row.
#        """
#        if row == -1:
#            row = self._row
#        if col == -1:
#            col = self._col
#        echo (self.pos(self.xpadding +col, self.ypadding +row) +data)
#
#
#    def getRow(self, row=-1):
#        """ Retreive row from buffer.
#            @var row: Target row. Default of -1 returns active row.
#            @return: String of characters at target row.
#        """
#        if row == -1:
#            row = self._row
#        try:
#            return self.content[self.position + row]
#        except:
#            raise ValueError, "Value out of range, top:%s, row:%s" % (self.position, row)
#

#    def update(self, data=u'', scrollToBottom=False):
#        """ Update content buffer.
#            @var data: New buffer content as single string, containing newlines for row breaks.
#            @var scrollToBottom: Set to True to scroll to bottom after refresh
#        """
#        self.position = 0
#        self._row = 0
#        self.content = []
#        return self.add (data, scrollToBottom)
#
#    def drawRow(self, row):
#        """ Draw visual row in buffer
#            @var: Draw this row. Default of -1 draws current row.
#        """
#        dataline = self.content[row]
#        self.writeString(dataline
#            +self.glyphs['erase']*(self._visible_width-ansilen(dataline)), 0, row)
#
#    def data(self):
#        """ @return: Data in content buffer as one string, each row joined by newline """
#        return '\n'.join(self.content)
#

#
#    def scrollIndicator(self):
#        """ returns one of '', '-', '+', or '+/-' to indicate scroll availability """
#        # XXX for now, only return '+/-'
#        if len(self.content) >self._visible_height:
#            return '+/-'
#        return ''
#    def fixate(self, mode=0):
#        """ Fixate cursor at current position in window,
#            @var mode: set to -1 for position on last character,
#                       or 0 for after last character.
#            @return: True
#        """
#        echo (self.pos(self.xpadding +self._col +mode, self.ypadding +self._row))
#        return True
#
#    def adjcursor_x(self, column):
#        """ Adjust position of cursor to value of column.
#            @return: True if position is changed
#        """
#        end = ansilen(self.getRow())
#        if column > end:
#            # out of x range, force cursor to end of line
#            column = end
#        elif column < 0:
#            column = 0
#        if column != self._col:
#            self._col = column
#            return True
#        return False
#
#    def adjcursor_y(self, row):
#        """ Adjust position of cursor to value of row.
#            @return: True if position is changed or window is scrolled.
#        """
#        adjusted = False
#        while row >= self._visible_height:
#            row -= 1
#            self.adjscroll (self.position +1)
#            adjusted = True
#        while row < 0:
#            row += 1
#            self.adjscroll (self.position -1)
#            adjusted = True
#        if row != self._row:
#            self._row = row
#            # call adjcursor_x, to ensure we are within bounds
#            self.adjcursor_x (self._col)
#            return True
#        return adjusted
#
#    def cursor_left(self, n=1):
#        """ position cursor one column left.
#            @return: True if not already at left margin.
#        """
#        if self.adjcursor_x (self._col +(n *-1)):
#            return self.fixate ()
#        return self.bell('cannot move left: at left margin')
#
#    def cursor_right(self, n=1):
#        """ position cursor one column right.
#            @return: True if not already at right margin.
#        """
#        if self.adjcursor_x (self._col +n):
#            return self.fixate ()
#        return self.bell('cannot move right: at right margin')
#
#    def cursor_home(self):
#        """ position cursor at far left margin.
#            @return: True if not already at left margin.
#        """
#        if self.adjcursor_x (0):
#            return self.fixate()
#        return self.bell('cannot move home: at left margin')
#
#    def cursor_end(self):
#        """ position cursor at far right margin.
#            @return: True if not already at right margin.
#        """
#        if self.adjcursor_x (ansilen(self.getRow())):
#            return self.fixate()
#        return self.bell('cannot move end: at right margin')
#
#    def cursor_up(self, n=-1):
#        """ position cursor one row up
#            @return: True on success
#        """
#        if n == -1: n=1
#        if self.adjcursor_y (self._row +(n *-1)):
#            self.adjcursor_x (self._col)
#            if self.position_last != self.position:
#                self.refresh ()
#            return self.fixate ()
#        return self.bell('cannot move up: at top')
#
#    def cursor_down(self, n=-1):
#        """ position cursor one row down
#            @return: True on success
#        """
#        if n == -1: n=1
#        if self.adjcursor_y (self._row +n):
#            self.adjcursor_x (self._col)
#            if self.position_last != self.position:
#                self.refresh ()
#            return self.fixate ()
#        return self.bell('cannot move down: at bottom')
#
#    def cursor_pgup(self, n=-1):
#        """ position cursor one page up.
#            @return: True on success.
#        """
#        if n == -1: n=1
#        if self.pgup(n) or self.adjcursor_y (0):
#            return self.fixate ()
#        return False
#
#    def cursor_pgdown(self, n=-1):
#        """ position cursor one page down.
#            @return: True on success.
#        """
#        if n == -1: n=1
#        if self.pgdown(n) \
#        or self.adjcursor_y (self._visible_height -1):
#            return self.fixate ()
#        return False
#
#
#
#
#
#
#
#
#
#
#
#
#
#
##XXX
#    def run(self, key=None, timeout=None):
#        """ The entry point for working with the pager window.
#            @var key:
#              pass in optional keystroke, otherwise it is read from input.
#            @var timeout:
#              return None after that time elapsed, or block indefinitely if unset.
#        """
#        self.timeout, self.exit = False, False
#        while True:
#            if self.position_last == -1:
#                self.refresh ()
#                self.fixate ()
#            if not key:
#                key = getch (timeout)
#                self.timeout = (not key) # Boolean: True if we timed out
#            self.lastkey = key
#            self.process_keystroke (key)
#            if self.interactive:
#                return key
#            if self.exit:
#                return
#            key = None
#        return
#
#
#
