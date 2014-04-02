"""
Pager class for x/84, http://github.com/jquast/x84/
"""
from x84.bbs.ansiwin import AnsiWindow
from x84.bbs.output import Ansi
import logging

VI_KEYSET = {
    'refresh': [unichr(12), ],
    'home': [],
    'end': [],
    'up': [u'k', u'K'],
    'down': [u'j', u'J', u'\r'],
    'pgup': [u'b', u'B'],
    'pgdown': [u'f', u'F'],
    'exit': [u'q', u'Q', unichr(27), ],
}


class Pager(AnsiWindow):
    """
    Scrolling ansi viewert d
    """
    # pylint: disable=R0904,R0902
    #        Too many public methods (24/20)
    #        Too many instance attributes (11/7)

    def __init__(self, height, width, yloc, xloc):
        """
        Initialize a pager of height, width, y, and x position.
        """
        AnsiWindow.__init__(self, height, width, yloc, xloc)
        self._position = self._position_last = 0
        self._quit = False
        self.content = list()
        self.keyset = VI_KEYSET.copy()
        self.init_keystrokes()

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
        Index of content buffer displayed at top of window.
        """
        return self._position

    @position.setter
    def position(self, pos):
        # pylint: disable=C0111
        #         Missing docstring
        self._position_last = self.position
        self._position = pos
        # bounds check
        if self._position < 0:
            self._position = 0
        if self._position > self.bottom:
            self._position = self.bottom
        self.moved = (self._position_last != self._position)

    @property
    def visible_content(self):
        """
        Returns content that is visible in window
        """
        return self.content[self.position:self.position + self.visible_height]

    @property
    def visible_bottom(self):
        """
        Returns bottom-most window row that contains content
        """
        if self.bottom < self.visible_height:
            return self.bottom
        return len(self.visible_content) - 1

    @property
    def bottom(self):
        """
        Returns bottom-most position that contains content
        """
        return max(0, len(self.content) - self.visible_height)

    def init_keystrokes(self):
        """
        This initializer sets keys appropriate for navigation.
        override or inherit this method to create a common keyset.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        self.keyset['home'].append(term.KEY_HOME)
        self.keyset['end'].append(term.KEY_END)
        self.keyset['pgup'].append(term.KEY_PGUP)
        self.keyset['pgdown'].append(term.KEY_PGDOWN)
        self.keyset['up'].append(term.KEY_UP)
        self.keyset['down'].append(term.KEY_DOWN)
        self.keyset['down'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_ESCAPE)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by run method and return terminal
        sequence suitable for refreshing when that keystroke modifies the
        window.
        """
        import x84.bbs.session
        self.moved = False
        rstr = u''
        if keystroke in self.keyset['refresh']:
            rstr += self.refresh()
        elif keystroke in self.keyset['up']:
            rstr += self.move_up()
        elif keystroke in self.keyset['down']:
            rstr += self.move_down()
        elif keystroke in self.keyset['home']:
            rstr += self.move_home()
        elif keystroke in self.keyset['end']:
            rstr += self.move_end()
        elif keystroke in self.keyset['pgup']:
            rstr += self.move_pgup()
        elif keystroke in self.keyset['pgdown']:
            rstr += self.move_pgdown()
        elif keystroke in self.keyset['exit']:
            self._quit = True
        else:
            logger = logging.getLogger()
            logger.debug(
                'unhandled, %r', keystroke if type(keystroke) is not int
                else x84.bbs.session.getterminal().keyname(keystroke))
        return rstr

    def read(self):
        """
        Reads input until ESCAPE key is pressed (Blocking).  Returns None.
        """
        from x84.bbs import getch
        from x84.bbs.session import getsession
        from x84.bbs.output import echo
        session = getsession()
        self._quit = False
        echo(self.refresh())
        while not self.quit:
            echo(self.process_keystroke(getch()))

    def move_home(self):
        """
        Scroll to top.
        """
        self.position = 0
        if self.moved:
            return self.refresh()
        return u''

    def move_end(self):
        """
        Scroll to bottom.
        """
        self.position = len(self.content) - self.visible_height
        if self.moved:
            return self.refresh()
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
            return self.refresh()
        return u''

    def move_up(self, num=1):
        """
        Scroll up ``num`` rows.
        """
        self.position -= num
        if self.moved:
            return self.refresh()
        return u''

    def refresh_row(self, row):
        """
        Return unicode string suitable for refreshing pager window at
        visible row.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        ucs = (Ansi(self.visible_content[row])
               if row < len(self.visible_content)
               else u'')
        return u''.join((
            term.normal,
            self.pos(row + self.ypadding, self.xpadding),
            self.align(ucs),
            term.normal))

    def refresh(self, start_row=0):
        """
        Return unicode string suitable for refreshing pager window from
        optional visible content row 'start_row' and downward. This can be
        useful if only the last line is modified; or in an 'insert' operation,
        only the last line need be refreshed.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        return u''.join(
            [term.normal] + [self.refresh_row(row)
                for row in range(start_row, len(self.visible_content))]
            + [term.normal])

    def update(self, ucs):
        """
        Update content buffer with '\n'-delimited lines of Ansi.
        """
        try:
            self.content = Ansi(Ansi(ucs).decode_pipe()).wrap(
                self.visible_width).splitlines()
        except AssertionError, err:
            # indeterminate length
            logger = logging.getLogger()
            logger.warn('%s in [%r]', err, ucs)
            self.content = ucs.split('\r\n')
        return self.refresh()

    def append(self, ucs):
        """
        Update content buffer with additional lines of ansi unicodes.
        """
        self.content.extend(Ansi(Ansi(ucs).decode_pipe())
                            .wrap(self.visible_width - 1).splitlines())
        return self.move_end() or self.refresh(self.bottom)
