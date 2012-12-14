"""
editor package for x/84, https://github.com/jquast/x84
"""

from x84.bbs.ansiwin import AnsiWindow

PC_KEYSET = {'refresh': [unichr(12), ],
             'backspace': [unichr(8), unichr(127), ],
             'enter': [u'\r', ],
             'exit': [unichr(27), ], }


class LineEditor(object):
    """
    This unicode line editor is unaware of its (x, y) position and is great
    for prompting a quick phrase on any terminal, such as a login: prompt.
    """
    # This should really be gnu/readline, but its not really accessible ..
    _hidden = False
    _width = 0
    _timeout = None
    _highlight = None

    @property
    def highlight(self):
        """
        highlight: when of non-zero length, a terminal sequence such as
        term.cyan_reverse before printing ' '*width + '\b'+width, used before
        reading input in read() and refresh(). this gives the effect of
        economic and terminal-agnostic 'input field'. By default term.reverse
        is used. Set to u'' to disable.
        """
        import x84.bbs.session
        if self._highlight is None:
            return x84.bbs.session.getterminal().reverse
        return self._highlight

    @highlight.setter
    def highlight(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._highlight = value

    @property
    def hidden(self):
        """
        When not False, represents a single 'mask' character to hide input
        with, such as a password prompt
        """
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        assert value is False or 1 == len(value)
        self._hidden = value

    @property
    def width(self):
        """
        When non-zero, represents the upperbound limit of characters to receive
        on input until no more characters are accepted.
        """
        return self._width

    @width.setter
    def width(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._width = value

    def __init__(self, width=None, content=u''):
        """
        Arguments:
            width: the maximum input length
        """
        self._width = width
        self.content = content

    def refresh(self):
        """
        Returns unicode byts suitable for drawing line.
        No movement or positional sequences are returned.
        """
        rstr = u''
        if 0 != len(self.highlight):
            rstr += self.highlight
            rstr += ' ' * self.width
            rstr += '\b' * self.width
        if self.hidden:
            rstr += self.hidden * len(self.content)
        else:
            rstr += self.content
        return rstr

    def read(self):
        """
        Reads input until the ENTER or ESCAPE key is pressed (Blocking).
        Allows backspacing. Returns unicode text, or None when cancelled.
        """
        import x84.bbs.session
        import x84.bbs.output
        x84.bbs.output.echo(self.refresh())
        session = x84.bbs.session.getsession()
        term = x84.bbs.session.getterminal()
        while True:
            inp = session.read_event('input')
            if inp == term.KEY_EXIT:
                if 0 != len(self.highlight):
                    x84.bbs.output.echo(term.normal)
                return None
            elif inp == term.KEY_ENTER:
                if 0 != len(self.highlight):
                    x84.bbs.output.echo(term.normal)
                return self.content
            elif inp == term.KEY_BACKSPACE:
                if len(self.content) > 0:
                    self.content = self.content[:-1]
                    x84.bbs.output.echo(u'\b \b')
            elif (type(inp) is not int
                    and ord(inp) >= ord(' ')
                    and (len(self.content) < self.width or self.width == 0)):
                self.content += inp
                if self.hidden:
                    x84.bbs.output.echo(self.hidden)
                else:
                    x84.bbs.output.echo(inp)


class ScrollingEditor(AnsiWindow):
    """
    A single line Editor fully aware of its (y, x).
    Infinite horizontal scrolling is enabled with the enable_scrolling
    property. When True, scrolling amount is limited using max_length.
    """
    # pylint: disable=R0902,R0904
    #        Too many instance attributes (14/7)
    #        Too many public methods (33/20)
    def __init__(self, width, yloc, xloc):
        """
        Construct a Line editor at (y,x) location of width (n).
        """
        self._horiz_shift = 0
        self._horiz_pos = 0
        self._enable_scrolling = False
        self._horiz_lastshift = 0
        self._scroll_pct = 35.0
        self._margin_pct = 20.0
        self._carriage_returned = False
        self._max_length = 0
        self._quit = False
        self._bell = False
        self._trim_char = '$ '
        self.keyset = PC_KEYSET
        self.content = u''
        height = 3  # 2 of 3 for top and bottom border
        # (optionaly displayed .. is this best x/y coord?
        #   once working, lets set default as borderless!)
        AnsiWindow.__init__(self, height, width, yloc, xloc)
        self.init_keystrokes()
    __init__.__doc__ = AnsiWindow.__init__.__doc__

    @property
    def position(self):
        """
        Tuple of shift amount and column position of line editor.
        """
        return (self._horiz_shift, self._horiz_pos)

    @property
    def eol(self):
        """
        Return True when no more input can be accepted (end of line).
        """
        return len(self.content) >= self.max_length

    @property
    def trim_char(self):
        """
        When scrolling, this unicode string is prefixed to the line to
        indicate it has been shifted.
        """
        return self._trim_char

    @trim_char.setter
    def trim_char(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._trim_char = value

    @property
    def bell(self):
        """
        Returns True when user nears margin and bell has been sounded and
        carriage has not yet been returned.
        """
        return int(float(self.visible_width) * (float(self.scroll_pct) * .01))

    @bell.setter
    def bell(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._bell = value

    @property
    def carriage_returned(self):
        """
        Returns True when last keystroke caused carriage to be returned.
        (KEY_ENTER was pressed)
        """
        return self._carriage_returned

    @property
    def quit(self):
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit

    @property
    def enable_scrolling(self):
        """
        Enable horizontal scrolling of line editor.
        Otherwise, input is limited to visible width.
        """
        return self._enable_scrolling

    @enable_scrolling.setter
    def enable_scrolling(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._enable_scrolling = value

    @property
    def is_scrolled(self):
        """
        Returns True if the horizontal editor is in a scrolled state.
        """
        return self._horiz_shift > 0

    @property
    def scroll_amt(self):
        """
        Returns number of columns horizontal editor will scroll, calculated by
        scroll_pct.
        """
        return int(float(self.visible_width) * (float(self.scroll_pct) * .01))

    @property
    def margin_amt(self):
        """
        Returns number of columns from right-edge that the horizontal editor
        signals bell=True, indicating that the end is near and the carriage
        should be returned.
        """
        return int(float(self.visible_width) * (float(self.margin_pct) * .01))

    @property
    def scroll_pct(self):
        """
        Number of columns, as a percentage of its total visible width, that
        will be scrolled when a user reaches the margin and enable_scrolling
        is True. Default is 35.
        """
        return self._scroll_pct

    @scroll_pct.setter
    def scroll_pct(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._scroll_pct = float(value)

    @property
    def margin_pct(self):
        """
        Number of columns away from input length limit, as a percentage of its
        total visible width, that will alarm the bell. This simulates the bell
        of a typewriter as a signaling mechanism. Default is 20.
        """
        # .. unofficially; intended to be used be a faked multi-line editor, by
        # using the bell as a wrap signal to instantiate another line editor
        # and 'return the carriage'
        return self._margin_pct

    @margin_pct.setter
    def margin_pct(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._margin_pct = float(value)

    @property
    def max_length(self):
        """
        Maximum line length. This also limits infinite scrolling when
        enable_scrolling is True. When unset, the maximum length is the
        visible width of the window.
        """
        return self._max_length or self.visible_width

    @max_length.setter
    def max_length(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._max_length = value

    def init_keystrokes(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override or inherit this method to create a common color and graphic
        set.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        self.keyset = PC_KEYSET
        self.keyset['refresh'].append(term.KEY_REFRESH)
        self.keyset['backspace'].append(term.KEY_BACKSPACE)
        self.keyset['enter'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_EXIT)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by run method and take action.
        """
        self._quit = False
        if keystroke in self.keyset['refresh']:
            return self.refresh()
        elif keystroke in self.keyset['backspace']:
            return self.backspace()
        elif keystroke in self.keyset['enter']:
            self._carriage_returned = True
            return u''
        elif keystroke in self.keyset['exit']:
            self._quit = True
            return u''
        elif type(keystroke) is int:
            return u''
        return self.add(keystroke)

    def fixate(self, x_adjust=0):
        """
        Return terminal sequence suitable for placing cursor at current
        position in window. Set x_adjust to -1 to position cursor 'on'
        the last character, or 0 for 'after' (default).
        """
        xpos = self._xpadding + self._horiz_pos + x_adjust
        return self.pos(1, xpos)

    def refresh(self):
        """
        Return unicode sequence suitable for refreshing the entire line
        and placing the cursor.
        """
        # reset position and detect new position
        self._horiz_lastshift = self._horiz_shift
        self._horiz_shift = 0
        self._horiz_pos = 0
        # pylint: disable=W0612
        #        Unused variable 'loop_cnt'
        for loop_cnt in range(len(self.content)):
            if self._horiz_pos > (self.visible_width - self.scroll_amt):
                self._horiz_shift += self.scroll_amt
                self._horiz_pos -= self.scroll_amt
                # if scrolling was not previously enabled, it is now!
                self.enable_scrolling = True
            self._horiz_pos += 1
        if self._horiz_shift > 0:
            scrl = self._horiz_shift + len(self.trim_char)
            prnt = self.trim_char + self.content[scrl:]
            prnt += (self.glyphs.get('erase', u'~')
                     * (self.visible_width - len(prnt)))
        else:
            prnt = self.content
        return (self.pos(self.ypadding, self.xpadding)
                + prnt + self.fixate())

    def backspace(self):
        """
        Remove character from end of content buffer, scroll as necessary.
        """
        if 0 == len(self.content):
            return u''
        rstr = u''
        self.content = self.content[:-1]
        if self.is_scrolled:
            if self._horiz_pos < (self.visible_width - self.scroll_amt):
                # shift left,
                self._horiz_shift -= self.scroll_amt
                self._horiz_pos += self.scroll_amt
                rstr += self.refresh()
        rstr += self.fixate(-1)
        rstr += ' \b'
        self._horiz_pos -= 1
        return rstr

    def update(self, ucs=u''):
        """
        Replace or reset content.
        """
        self._horiz_shift = 0
        self._horiz_pos = 0
        self.content = ucs
        assert unichr(27) not in ucs, ('Editor is not sequence-safe')

    def add(self, u_chr):
        """
        Returns output sequence necessary to add a character to content buffer.
        An empty content buffer is returned if no data could be inserted.
        sequences for re-displaying the full input line are returned when the
        character addition caused the window to scroll horizontally.
        Otherwise, the input is simply returned to be displayed ('local echo').
        """
        if self.eol and not self.enable_scrolling:
            # cannot input, at end of line!
            return u''
        # append to input
        self.content += u_chr
        if self._horiz_pos >= (self.visible_width):
            # scrolling is required,
            return self.refresh()
        # return character appended as output, ensure .fixate() is used first!
        self._horiz_pos += 1
        return u_chr
