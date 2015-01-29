""" Pager package for x/84. """
from x84.bbs.ansiwin import AnsiWindow
from x84.bbs.output import encode_pipe, decode_pipe
from x84.bbs.session import getterminal, getch
from x84.bbs.output import echo

VI_KEYSET = {
    'refresh': [unichr(12), ],
    'home': [u'0'],
    'end': [u'G'],
    'up': [u'k', u'K'],
    'down': [u'j', u'J', u'\r'],
    'pgup': [u'b', u'B', u''],
    'pgdown': [u'f', u'F', u''],
    'exit': [u'q', u'Q', unichr(27), ],
}


class Pager(AnsiWindow):

    """ Scrolling viewer. """

    def __init__(self, *args, **kwargs):
        """
        Class initializer.

        :param int width: width of window.
        :param int height: height of window.
        :param int yloc: y-location of window.
        :param int xloc: x-location of window.
        :param str content: initial pager contents.
        :param dict colors: color theme.
        :param dict glyphs: bordering window character glyphs.
        :param dict keyset: command keys, global ``VI_KEYSET`` is default.
        """
        self._quit = False
        self.init_keystrokes(keyset=kwargs.pop('keyset', VI_KEYSET.copy()))
        _content = kwargs.pop('content', u'') or u''
        AnsiWindow.__init__(self, *args, **kwargs)
        self.content = _content
        self._position = self.position = kwargs.pop('position', 0) or 0

    def init_keystrokes(self, keyset):
        """ Sets keyboard keys for various editing keystrokes. """
        term = getterminal()
        self.keyset = keyset
        self.keyset['home'].append(term.KEY_HOME)
        self.keyset['end'].append(term.KEY_END)
        self.keyset['pgup'].append(term.KEY_PGUP)
        self.keyset['pgdown'].append(term.KEY_PGDOWN)
        self.keyset['up'].append(term.KEY_UP)
        self.keyset['down'].append(term.KEY_DOWN)
        self.keyset['down'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_ESCAPE)

    @property
    def quit(self):
        """ Whether a 'quit' character has been handled, such as escape. """
        return self._quit

    @property
    def position_last(self):
        """ Previous position before last move. """
        return self._position_last

    @property
    def position(self):
        """ Index of content buffer displayed at top of window. """
        return self._position

    @position.setter
    def position(self, pos):
        # pylint: disable=C0111
        #         Missing docstring
        self._position_last = self._position

        # assign and bounds check
        self._position = min(max(0, pos), self.bottom)
        self.moved = (self._position_last != self._position)

    @property
    def visible_content(self):
        """ Content that is visible in window. """
        return self._content[self.position:self.position + self.visible_height]

    @property
    def visible_bottom(self):
        """ Bottom-most window row that contains content. """
        if self.bottom < self.visible_height:
            return self.bottom
        return len(self.visible_content) - 1

    @property
    def bottom(self):
        """ Bottom-most position that contains content. """
        maximum = self.visible_height
        return max(0, maximum - self.visible_height)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke and return string to refresh.

        :param blessed.keyboard.Keystroke keystroke: input from ``inkey()``.
        :rtype: str
        :returns: string sequence suitable for refresh.
        """
        self.moved = False
        rstr = u''
        keystroke = hasattr(keystroke, 'code') and keystroke.code or keystroke
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
        return rstr

    def read(self):
        """
        Blocking read-eval-print loop for pager.

        Processes user input, taking action upon and refreshing pager
        until the escape key is pressed.

        :rtype: None
        """
        self._quit = False
        echo(self.refresh())
        while not self.quit:
            echo(self.process_keystroke(getch()))

    def move_home(self):
        """
        Scroll to top and return refresh string.

        :rtype: str
        """
        self.position = 0
        if self.moved:
            return self.refresh()
        return u''

    def move_end(self):
        """
        Scroll to bottom and return refresh string.

        :rtype: str
        """
        self.position = len(self._content) - self.visible_height
        if self.moved:
            return self.refresh()
        return u''

    def move_pgup(self, num=1):
        """
        Scroll up ``num`` pages and return refresh string.

        :rtype: str
        """
        self.position -= (num * (self.visible_height))
        return self.refresh() if self.moved else u''

    def move_pgdown(self, num=1):
        """
        Scroll down ``num`` pages and return refresh string.

        :rtype: str
        """
        self.position += (num * (self.visible_height))
        return self.refresh() if self.moved else u''

    def move_down(self, num=1):
        """
        Scroll down ``num`` rows and return refresh string.

        :rtype: str
        """
        self.position += num
        if self.moved:
            return self.refresh()
        return u''

    def move_up(self, num=1):
        """
        Scroll up ``num`` rows and return refresh string.

        :rtype: str
        """
        self.position -= num
        if self.moved:
            return self.refresh()
        return u''

    def refresh_row(self, row):
        """
        Return unicode string suitable for refreshing pager row.

        :param int row: target row by visible index.
        :rtype: str
        """
        term = getterminal()
        ucs = u''
        if row < len(self.visible_content):
            ucs = self.visible_content[row]
        disp_position = self.pos(row + self.ypadding, self.xpadding)
        return u''.join((term.normal,
                         disp_position,
                         self.align(ucs),
                         term.normal))

    def refresh(self, start_row=0):
        """
        Return unicode string suitable for refreshing pager window.

        :param int start_row: refresh from only visible row 'start_row'
                              and downward. This can be useful if only
                              the last line is modified; or in an
                              'insert' operation: only the last line
                              need be refreshed.
        :rtype: str
        """
        term = getterminal()
        return u''.join(
            [term.normal] + [
                self.refresh_row(row)
                for row in range(start_row, len(self.visible_content))
            ] + [term.normal])

    def update(self, ucs):
        """
        Update content buffer with newline-delimited text.

        :rtype: str
        """
        self.content = ucs
        return self.refresh()

    @property
    def content(self):
        """
        Content of pager.

        Return value is "pipe encoded" by :func:`encode_pipe`.
        :rtype: str
        """
        return encode_pipe('\r\n'.join(self._content))

    @content.setter
    def content(self, ucs_value):
        # pylint: disable=C0111
        #         Missing method docstring
        self._content = self._content_wrap(decode_pipe(ucs_value))

    def _content_wrap(self, ucs):
        """ Return word-wrapped text ``ucs`` that contains newlines. """
        term = getterminal()
        lines = []
        for line in ucs.splitlines():
            if line.strip():
                lines.extend(term.wrap(line, self.visible_width - 1))
            else:
                lines.append(u'')
        return lines

    def append(self, ucs):
        """
        Update content buffer with additional line(s) of text.

        "pipe codes" in ``ucs`` are decoded by :func:`decode_pipe`.

        :param str ucs: unicode string to append-to content buffer.
        :rtype str
        :return: terminal sequence suitable for refreshing window.
        """
        self._content.extend(self._content_wrap(decode_pipe(ucs)))
        return self.move_end() or self.refresh(self.bottom)
