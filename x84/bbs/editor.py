"""
editor package for x/84, https://github.com/jquast/x84
"""

from x84.bbs.ansiwin import AnsiWindow

PC_KEYSET = {'refresh': [unichr(12), ],
             'backspace': [unichr(8), unichr(127), ],
             'backword': [unichr(23), ],
             'enter': [u'\r', ],
             'exit': [unichr(27), ], }


class LineEditor(object):

    """
    This unicode line editor is unaware of its (x, y) position.

    It is great for prompting a quick phrase on any terminal,
    such as a ``login:`` prompt.
    """
    # This should really be gnu/readline, but its not really accessible ..
    _hidden = False
    _width = 0

    def __init__(self, width=None, content=u'', hidden=False,
                 colors=None, glyphs=None, keyset=None):
        """
        :param width: the maximum input length.
        :param content: given default content.
        :param colors: optional dictionary containing key 'highlight'.
        :param keyset: optional dictionary of line editing values.
        """
        from x84.bbs.session import getterminal
        self._term = getterminal()
        self.content = content or u''
        self.hidden = hidden
        self._width = width
        self._input_length = self._term.length(content)

        self._quit = False
        self._carriage_returned = False

        self.init_keystrokes(keyset=keyset or PC_KEYSET.copy())
        self.init_theme(colors=colors, glyphs=glyphs)

    def init_theme(self, colors=None, glyphs=None, hidden=False):
        """
        Initialize colors['highlight'].
        """
        # set defaults,
        self.colors = {'highlight': self._term.reverse}

        # allow user override
        if colors is not None:
            self.colors.update(colors)
        if glyphs is not None:
            self.glyphs.update(glyphs)
        if hidden:
            self.hidden = hidden

    def init_keystrokes(self, keyset):
        """
        This initializer sets keyboard keys for backspace/exit.
        """
        self.keyset = keyset
        self.keyset['refresh'].append(self._term.KEY_REFRESH)
        self.keyset['backspace'].append(self._term.KEY_BACKSPACE)
        self.keyset['backspace'].append(self._term.KEY_DELETE)
        self.keyset['enter'].append(self._term.KEY_ENTER)
        self.keyset['exit'].append(self._term.KEY_ESCAPE)

    @property
    def quit(self):
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit

    @property
    def carriage_returned(self):
        """
        Returns True when last keystroke caused carriage to be returned.
        (KEY_ENTER was pressed)
        """
        return self._carriage_returned

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

    def refresh(self):
        """
        Returns unicode suitable for drawing edit line.

        No movement or positional sequences are returned.
        """
        disp_lightbar = u''.join((
            self._term.normal,
            self.colors.get('highlight', u''),
            ' ' * self.width,
            '\b' * self.width))
        content = self.content
        if self.hidden:
            content = self.hidden * self._term.length(self.content)
        return u''.join((disp_lightbar, content, self._term.cursor_visible))

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by read method and take action.
        """
        self._quit = False
        if keystroke in self.keyset['refresh']:
            return u'\b' * self._term.length(self.content) + self.refresh()
        elif keystroke in self.keyset['backspace']:
            if len(self.content) != 0:
                len_toss = self._term.length(self.content[-1])
                self.content = self.content[:-1]
                return u''.join((
                    u'\b' * len_toss,
                    u' ' * len_toss,
                    u'\b',))
        elif keystroke in self.keyset['backword']:
            if len(self.content) != 0:
                ridx = self.content.rstrip().rfind(' ') + 1
                toss = self._term.length(self.content[ridx:])
                move = len(self.content[ridx:])
                self.content = self.content[:ridx]
                return u''.join((
                    u'\b' * toss,
                    u' ' * move,
                    u'\b' * move,))
        elif keystroke in self.keyset['enter']:
            self._carriage_returned = True
        elif keystroke in self.keyset['exit']:
            self._quit = True
        elif type(keystroke) is int:
            return u''
        elif (ord(keystroke) >= ord(' ') and
                (self._term.length(self.content) < self.width or self.width is None)):
            self.content += keystroke
            return keystroke if not self.hidden else self.hidden
        return u''

    def read(self):
        """
        Reads input until the ENTER or ESCAPE key is pressed (Blocking).
        Allows backspacing. Returns unicode text, or None when canceled.
        """
        from x84.bbs import getch
        from x84.bbs.output import echo
        self._carriage_returned = False
        self._quit = False
        echo(self.refresh())
        while not (self.quit or self.carriage_returned):
            inp = getch()
            echo(self.process_keystroke(inp))
        echo(self._term.normal)
        if not self.quit:
            return self.content
        return None


class ScrollingEditor(AnsiWindow):

    """
    A single line Editor, requires absolute (yloc, xloc) position.

    Infinite horizontal scrolling is enabled or limited using max_length.
    """
    # pylint: disable=R0902,R0904
    #        Too many instance attributes (14/7)
    #        Too many public methods (33/20)

    def __init__(self, *args, **kwargs):
        """
        Construct a Line editor at (y,x) location..
        """
        from x84.bbs.session import getterminal
        self._term = getterminal()
        self._horiz_shift = 0
        self._horiz_pos = 0
        # self._enable_scrolling = False
        self._horiz_lastshift = 0
        self._scroll_pct = kwargs.pop('scroll_pct', 35.0)
        self._margin_pct = kwargs.pop('margin_pct', 20.0)
        self._carriage_returned = False
        self._max_length = kwargs.pop('max_length', 0)
        self._quit = False
        self._bell = False
        self.content = kwargs.pop('content', u'')
        self._input_length = self._term.length(self.content)
        # there are some flaws about how a 'height' of a window must be
        # '3', even though we only want 1; we must also offset (y, x) by
        # 1 and width by 2: issue #161.
        kwargs['height'] = 3
        self.init_keystrokes(keyset=kwargs.pop('keyset', PC_KEYSET.copy()))
        AnsiWindow.__init__(self, *args, **kwargs)

    def init_theme(self, colors=None, glyphs=None):
        AnsiWindow.init_theme(self, colors, glyphs)
        if 'highlight' not in self.colors:
            self.colors['highlight'] = self._term.yellow_reverse
        if 'strip' not in self.glyphs:
            self.glyphs['strip'] = u'$ '

    def init_keystrokes(self, keyset):
        """
        This initializer sets keyboard keys for various editing keystrokes.
        """
        self.keyset = keyset
        self.keyset['refresh'].append(self._term.KEY_REFRESH)
        self.keyset['backspace'].append(self._term.KEY_BACKSPACE)
        self.keyset['backspace'].append(self._term.KEY_DELETE)
        self.keyset['enter'].append(self._term.KEY_ENTER)
        self.keyset['exit'].append(self._term.KEY_ESCAPE)

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
        return self._input_length >= self.max_length

    @property
    def bell(self):
        """
        Returns True when user nears margin and bell has been sounded and
        carriage has not yet been returned.
        """
        margin = int(float(self.visible_width) * (float(self.scroll_pct) * .01))
        return bool(self._input_length >= self.visible_width - margin)

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

# jquast: disabled because this isn't actually honored -- what is probably
# intended her is some kind of mix-in with LineEditor, but they work quite
# differently -- one requires absolute (y, x) and the other doesn't use it
# at all.  However, if we can implement term.get_position() we could probably
# work something out about an optional (y, x) position for both.
#
#    @property
#    def enable_scrolling(self):
#        """
#        Enable horizontal scrolling of line editor.
#        Otherwise, input is limited to visible width.
#        """
#        return self._enable_scrolling
#
#    @enable_scrolling.setter
#    def enable_scrolling(self, value):
#        # pylint: disable=C0111
#        #         Missing docstring
#        self._enable_scrolling = value

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
        should be soon returned. This also indicates the distance from margin
        a user may type into until ScrollingEditor horizontally shifts.
        """
        return int(float(self.visible_width) * (float(self.margin_pct) * .01))

    @property
    def scroll_pct(self):
        """
        Number of columns, as a percentage of its total visible width, that
        will be scrolled when a user reaches the margin by percent.
        Default is 35.
        """
        return self._scroll_pct

    @scroll_pct.setter
    def scroll_pct(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._scroll_pct = float(value)
        assert value < 50, ("Bugs with values greater than 50 ...")

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
        enable_scrolling is True. When unset, the maximum length is
        infinite.
        """
        return self._max_length or float('inf')

    @max_length.setter
    def max_length(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._max_length = value

    @property
    def content(self):
        """ The contents of editor. """
        return self._content

    @content.setter
    def content(self, value):
        self._content = value
        self._input_length = self._term.length(value)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by read method and take action.
        """
        self._quit = False
        rstr = u''
        if keystroke in self.keyset['refresh']:
            rstr = self.refresh()
        elif keystroke in self.keyset['backspace']:
            rstr = self.backspace()
        elif keystroke in self.keyset['backword']:
            rstr = self.backword()
        elif keystroke in self.keyset['enter']:
            self._carriage_returned = True
            rstr = u''
        elif keystroke in self.keyset['exit']:
            self._quit = True
            rstr = u''
        elif type(keystroke) is int:
            rstr = u''
        else:
            if ord(keystroke) >= 0x20:
                rstr = self.add(keystroke)
        return rstr

    def read(self):
        """
        Reads input until the ENTER or ESCAPE key is pressed (Blocking).
        Allows backspacing. Returns unicode text, or None when canceled.
        """
        from x84.bbs import getch
        from x84.bbs.output import echo
        echo(self.refresh())
        self._quit = False
        self._carriage_returned = False
        while not (self.quit or self.carriage_returned):
            inp = getch()
            echo(self.process_keystroke(inp))
        if not self.quit:
            return self.content
        return None

    def fixate(self, x_adjust=0):
        """
        Return terminal sequence suitable for placing cursor at current
        position in window. Set x_adjust to -1 to position cursor 'on'
        the last character, or 0 for 'after' (default).
        """
        xpos = self._xpadding + self._horiz_pos + x_adjust
        return self.pos(1, xpos) + self._term.cursor_visible

    def refresh(self):
        """
        Return unicode sequence suitable for refreshing the entire
        line and placing the cursor.

        A strange by-product; if scrolling was not previously enabled,
        it is if wrapping must occur; this can happen if a
        non-scrolling editor was provided a very large .content
        buffer, then later .refresh()'d. -- essentially enabling
        infinite scrolling
        """
        # reset position and detect new position
        self._horiz_lastshift = self._horiz_shift
        self._horiz_shift = 0
        self._horiz_pos = 0
        #                  (self._term.length(self.content))
        for _count in range(self._input_length):
            if (self._horiz_pos >
                    (self.visible_width - self.scroll_amt)):
                self._horiz_shift += self.scroll_amt
                self._horiz_pos -= self.scroll_amt
                #self.enable_scrolling = True
            self._horiz_pos += 1
        if self._horiz_shift > 0:
            self._horiz_shift += len(self.glyphs['strip'])
            prnt = u''.join((
                self.glyphs['strip'],
                self.content[self._horiz_shift:],))
        else:
            prnt = self.content
        return u''.join((
            self.pos(self.ypadding, self.xpadding),
            self._term.normal,
            self.colors.get('highlight', u''),
            self.align(prnt),
            self.fixate(),))

    def backword(self):
        """
        Delete word behind cursor, using ' ' as boundary.
        in readline this is unix-word-rubout (C-w).
        """
        if 0 == len(self.content):
            return u''
        ridx = self.content.rstrip().rfind(' ') + 1
        self.content = self.content[:ridx]
        return self.refresh()

    def backspace(self):
        """
        Remove character from end of content buffer,
        scroll as necessary.
        """
        if 0 == len(self.content):
            return u''
        rstr = u''
        # measured backspace erases over double-wide (wcwidth)
        len_toss = self._term.length(self.content[-1])
        len_move = 1
        self.content = self.content[:-1]
        if self.is_scrolled and (self._horiz_pos < self.scroll_amt):
            # shift left,
            self._horiz_shift -= self.scroll_amt
            self._horiz_pos += self.scroll_amt
            rstr += self.refresh()
        else:
            rstr += u''.join((
                self.fixate(0),
                u'\b' * len_toss,
                u' ' * len_move,
                u'\b' * len_move,))
            self._horiz_pos -= 1
        return rstr

    def update(self, ucs=u''):
        """
        Replace or reset content.
        """
        self._horiz_shift = 0
        self._horiz_pos = 0
        self.content = ucs
        self._carriage_returned = False
        self._quit = False
        assert unichr(27) not in ucs, ('Editor is not ESC sequence-safe')

    def add(self, u_chr):
        """
        Returns output sequence necessary to add a character to
        content buffer.  An empty content buffer is returned if
        no data could be inserted. Sequences for re-displaying
        the full input line are returned when the character
        addition caused the window to scroll horizontally.
        Otherwise, the input is simply returned to be displayed
        ('local echo').
        """
        if self.eol:
            # cannot input, at end of line!
            return u''

        # append input to content directly to the backend variable,
        # so that we adjust the length only by the most recently-added
        # character.
        self._content += u_chr
        self._input_length += self._term.length(u_chr)

        # return character appended as output, ensure .fixate() is used first!
        self._horiz_pos += 1
        if self._horiz_pos >= (self.visible_width - self.margin_amt):
            # scrolling is required,
            return self.refresh()
        return self._term.normal + self.colors['highlight'] + u_chr
