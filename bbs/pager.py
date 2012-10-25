"""
Pager class for x/84, http://github.com/jquast/x84/
"""
import bbs.output
import bbs.ansiwin
import bbs.session

NETHACK_KEYSET = {
        'refresh': [unichr(12), ],
        'home': [u'y', ],
        'end': [u'n', ],
        'up': [u'k', ],
        'pgup': [u'K', ],
        'down': [u'j', ],
        'pgdown': [u'J', ],
        'exit': [u'q', u'Q', ],
        }

class Pager(bbs.ansiwin.AnsiWindow):
    """
    Scrolling ansi viewer
    """
    #pylint: disable=R0904,R0902
    #        Too many public methods (24/20)
    #        Too many instance attributes (11/7)

    def __init__(self, height, width, yloc, xloc):
        """
        Initialize a pager of height, width, y, and x position.
        """
        bbs.ansiwin.AnsiWindow.__init__ (self, height, width, yloc, xloc)
        self._xpadding = 1
        self._ypadding = 1
        self._col = 0
        self._row = 0
        self._position = 0
        self._position_last = 0
        self._moved = False
        self._quit = False
        self.content = list ()
        self.keyset = NETHACK_KEYSET
        self.init_keystrokes ()

    @property
    def moved(self):
        """
        Returnes: True if last call to process_keystroke() resulted in
        movement.
        """
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
        # bounds check
        if self._position < 0:
            self._position = 0
        if self._position > self.bottom:
            self._position = self.bottom

    @property
    def visible_content(self):
        """
        Returns content that is visible in window
        """
        return self.content[self.position:self.position + self.visible_height]

    @property
    def bottom(self):
        """
        Returns bottom-most position of window that contains content
        """
        return max(0, len(self.content) - self.visible_height)


    def init_keystrokes(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override or inherit this method to create a common color and graphic
        set.
        """
        term = bbs.session.getsession().terminal
        self.keyset['home'].append (term.KEY_HOME)
        self.keyset['end'].append (term.KEY_END)
        self.keyset['pgup'].append (term.KEY_PPAGE)
        self.keyset['pgdown'].append (term.KEY_NPAGE)
        self.keyset['up'].append (term.KEY_KEY_UP)
        self.keyset['down'].append (term.KEY_DOWN)
        self.keyset['exit'].append (term.KEY_EXIT)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by run method and return terminal
        sequence suitable for refreshing when that keystroke modifies the
        window.
        """
        self._position_last = self._position
        rstr = u''
        if keystroke in self.keyset['refresh']:
            rstr += self.refresh ()
        elif keystroke in self.keyset['up']:
            rstr += self.move_up ()
        elif keystroke in self.keyset['down']:
            rstr += self.move_down ()
        elif keystroke in self.keyset['home']:
            rstr += self.move_home ()
        elif keystroke in self.keyset['end']:
            rstr += self.move_end ()
        elif keystroke in self.keyset['pgup']:
            rstr += self.move_pgup ()
        elif keystroke in self.keyset['pgdown']:
            rstr += self.move_pgdown ()
        elif keystroke in self.keyset['exit']:
            self._quit = True
        else:
            bbs.session.logger.warn ('unhandled, %r', keystroke
                    if type(keystroke) is not int
                    else bbs.session.getsession().terminal.keyname(keystroke))
        return rstr

    def move_home(self):
        """
        Scroll to top.
        """
        self.position = 0
        if self.moved:
            return self.refresh ()
        return u''

    def move_end(self):
        """
        Scroll to bottom.
        """
        self.position = len(self.content) - self.visible_height
        if self.moved:
            return self.refresh ()
        return u''

    def move_pgup(self, num=1):
        """
        Scroll up ``num`` pages.
        """
        self.position -= (num * (self.visible_height))
        return self.refresh() if self.moved else u''

    def move_pgdown(self, num=1):
        """
        Scroll down ``num`` pages.
        """
        self.position += (num * (self.visible_height))
        return self.refresh() if self.moved else u''

    def move_down(self, num=1):
        """
        Scroll down ``num`` rows.
        """
        self.position += num
        if self.moved:
            return self.refresh ()
        return u''

    def move_up(self, num=1):
        """
        Scroll up ``num`` rows.
        """
        self.position -= num
        if self.moved:
            return self.refresh ()
        return u''

    def refresh(self, start_row=0):
        """
        Return unicode string suitable for refreshing pager window from
        visible content row 'start_row' and downward. This can be useful if
        only the last line is modified; only the last line need be refreshed.
        """
        term = bbs.session.getsession().terminal
        # draw window contents
        rstr = u''
        row = 0
        for row, line in enumerate(self.visible_content):
            if row < start_row:
                continue
            yloc = row + self.ypadding
            rstr += self.pos (yloc, self.xpadding)
            rstr += line
            len_line = bbs.output.Ansi(line).__len__()
            rstr += u' ' * max(0, self.visible_width - len_line)
        # clear to end of window
        yloc = row + self.ypadding
        while yloc < self.visible_height - 1:
            yloc += 1
            rstr += self.pos (yloc, self.xpadding)
            rstr += u' ' * (self.visible_width)
        return rstr + term.normal

    def update(self, unibytes):
        """
        Update content buffer with lines of ansi unicodes as single unit.
        """
        self.content = bbs.output.Ansi(unibytes
                ).wrap(self.visible_width - 1).split('\r\n')
        return self.refresh ()

    def append(self, unibytes):
        """
        Update content buffer with additional lines of ansi unicodes.
        """
        self.content.extend (bbs.output.Ansi(unibytes
            ).wrap(self.visible_width - 1).split('\r\n'))
        return self._end() or self.refresh(self.bottom)
