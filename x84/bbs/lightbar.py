""" Lightbar package for x/84. """

# local imports
from x84.bbs.ansiwin import AnsiWindow
from x84.bbs.session import getterminal, getch
from x84.bbs.output import decode_pipe, echo


#: default command-key mapping.
NETHACK_KEYSET = {'home': [u'y', '0'],
                  'end': [u'n', 'G'],
                  'pgup': [u'h', u'b'],
                  'pgdown': [u'l', u'f'],
                  'up': [u'k'],
                  'down': [u'j'],
                  'enter': [u'\r'],
                  'exit': [u'q', u'Q', unichr(27), ],
                  }


class Lightbar(AnsiWindow):

    """
    This Windowing class offers a classic 'lightbar' interface.

    Instantiate with yloc, xloc, height, and width, then call the update method
    with a list of unicode strings. send keycodes to process_keystroke () to
    interactive with the 'lightbar'.
    """

    # pylint: disable=R0902
    #         Too many instance attributes (15/7)
    # pylint: disable=R0904
    #         Too many public methods (29/20)
    def __init__(self, *args, **kwargs):
        """
        Class initializer.

        Initialize a lightbar of height, width, y and x, and position.

        :param int width: width of window.
        :param int height: height of window.
        :param int yloc: y-location of window.
        :param int xloc: x-location of window.
        :param dict colors: color theme, only key value of ``highlight``
                            is used.
        :param dict glyphs: bordering window character glyphs.
        :param dict keyset: command keys, global ``NETHACK_KEYSET`` is
                            used by default, augmented by application
                            keys such as home, end, pgup, etc.
        :param list content: Lightbar content as list of tuples, an empty list
                             is used by default.  Tuples must be in form of
                             ``(key, str)``.  ``key`` may have any suitable
                             significance for the caller.  ``str``, however,
                             must be of a unicode terminal sequence.
        """
        self._selected = False
        self._quit = False
        self._vitem_idx = self._vitem_shift = -1
        self.content = kwargs.pop('content', list())

        pos = kwargs.pop('position', (0, 0)) or (0, 0)

        self.init_keystrokes(
            keyset=kwargs.pop('keyset', NETHACK_KEYSET.copy()))

        AnsiWindow.__init__(self, *args, **kwargs)
        self.position = pos

    def init_theme(self, colors=None, glyphs=None):
        """ Set color and bordering glyphs theme. """
        colors = colors or {'highlight': getterminal().reverse_yellow}
        glyphs = glyphs or {'strip': u' $'}
        AnsiWindow.init_theme(self, colors, glyphs)

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
        self.keyset['enter'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_ESCAPE)

    def update(self, keyed_uchars=None):
        """ Replace content with with sequence of (key, str).

        ``key`` may have any suitable significance for the caller.  ``str``,
        however, must be of a unicode terminal sequence.
        """
        if keyed_uchars is None:
            keyed_uchars = (None, u'',)
        self.content = list(keyed_uchars)
        self.position = (self.vitem_idx, self.vitem_shift)

    def refresh_row(self, row):
        """ Return string sequence suitable for refreshing current selection.

        Return unicode byte sequence suitable for moving to location ypos of
        window-relative row, and displaying any valid entry there, or using
        glyphs['erase'] if out of bounds. Strings are ansi color safe, and
        will be trimmed using glyphs['strip'] if their displayed width is
        wider than window.
        """
        term = getterminal()

        pos = self.pos(self.ypadding + row, self.xpadding)
        entry = self.vitem_shift + row
        if entry >= len(self.content):
            # out-of-bounds;
            disp_erase = self.glyphs.get('erase', u' ') * self.visible_width
            return u''.join((pos, disp_erase,))

        def fit_row(ucs):
            """ Strip a unicode row to fit window boundry, if necessary """
            column = self.visible_width - 1
            wrapped = term.wrap(ucs, column)
            if len(wrapped) > 1:
                marker = self.glyphs.get('strip', u' $')
                marker_column = self.visible_width - len(marker)
                wrapped = term.wrap(ucs, marker_column)
                ucs = term.ljust(wrapped[0].rstrip(), marker_column) + marker
                return ucs
            return term.ljust(ucs, column)

        # allow ucs data with '\r\n', to accomidate soft and hardbreaks; just
        # don't display them, really wrecks up cusor positioning.
        ucs = self.content[entry][1].strip(u'\r\n')

        # highlighted entry; strip of ansi sequences, use color 'highlight'
        # trim and append '$ ' if it cannot fit,
        if entry == self.index:
            ucs = term.strip_seqs(ucs)
            if term.length(ucs) > self.visible_width:
                ucs = fit_row(ucs)
            return u''.join((pos,
                             term.normal,
                             self.colors.get('highlight', u''),
                             self.align(ucs),
                             term.normal,))
        # unselected entry; retain ansi sequences, decode any pipe characters,
        # trim and append '$ ' if it cannot fit
        ucs = decode_pipe(ucs)
        if term.length(ucs) > self.visible_width:
            ucs = fit_row(ucs)
        return u''.join((pos,
                         self.colors.get('lowlight', u''),
                         self.align(ucs),
                         term.normal,))

    def fixate(self):
        """ Return string sequence suitable for "fixating" cursor position. """
        return self.pos(self.ypadding + self.vitem_idx,
                        self.xpadding + self.visible_width)

    def refresh(self):
        """ Return string sequence suitable for refreshing lightbar. """
        return u''.join(self.refresh_row(ypos) for ypos in
                        range(max(self.visible_bottom, self.visible_height)))

    def refresh_quick(self):
        """ Redraw only the 'dirty' portions after a 'move' has occurred. """
        if self.moved:
            if (self._vitem_lastshift != self.vitem_shift):
                # page shift, refresh entire page
                return self.refresh()
            if self._vitem_lastidx != self.vitem_idx:
                # unhighlight last selection, highlight new
                return (self.refresh_row(self._vitem_lastidx)
                        + self.refresh_row(self.vitem_idx))
            else:
                # just highlight new ..
                return (self.refresh_row(self.vitem_idx))
        return u''

    def process_keystroke(self, key):
        """
        Process the keystroke and return string to refresh.

        :param blessed.keyboard.Keystroke keystroke: input from ``inkey()``.
        :rtype: str
        :returns: string sequence suitable for refresh.
        """
        self._moved = False
        self._selected = False
        self._vitem_lastidx = self.vitem_idx
        self._vitem_lastshift = self.vitem_shift
        rstr = u''
        keystroke = hasattr(key, 'code') and key.code or key
        if keystroke in self.keyset['home']:
            rstr = self.move_home()
        elif keystroke in self.keyset['end']:
            rstr = self.move_end()
        elif keystroke in self.keyset['pgup']:
            rstr = self.move_pageup()
        elif keystroke in self.keyset['pgdown']:
            rstr = self.move_pagedown()
        elif keystroke in self.keyset['up']:
            rstr = self.move_up()
        elif keystroke in self.keyset['down']:
            rstr = self.move_down()
        elif keystroke in self.keyset['enter']:
            self.selected = True
        elif keystroke in self.keyset['exit']:
            self._quit = True
        return rstr

    def read(self):
        """
        Reads input until the ENTER or ESCAPE key is pressed (Blocking).

        Returns selection content, or None when canceled.
        """
        self._selected = False
        self._quit = False
        echo(self.refresh())
        while not (self.selected or self.quit):
            echo(self.process_keystroke(getch()))
        if self.quit:
            return None
        return self.selection[0]

    @property
    def quit(self):
        """ Whether a 'quit' character has been handled, such as escape. """
        return self._quit

    @property
    def index(self):
        """ Selected index of self.content. """
        return self.vitem_shift + self.vitem_idx

    @property
    def at_bottom(self):
        """ Whether current selection is pointed at final entry. """
        return self.index == len(self.content) - 1

    @property
    def at_top(self):
        """ Whether current selection is pointed at the first entry. """
        return self.index == 0

    @property
    def selection(self):
        """ Selected content of self.content by index. """
        return (self.content[self.index]
                if self.index >= 0 and self.index < len(self.content)
                else (None, None))

    @property
    def selected(self):
        """  Whether carriage return was detected by process_keystroke. """
        return self._selected

    @selected.setter
    def selected(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        # this setter should only be used to reset to 'False' for recycling
        assert isinstance(value, bool)
        self._selected = value

    @property
    def last_index(self):
        """ Previously selected index of self.content. """
        return self._vitem_lastshift + self._vitem_lastidx

    @property
    def position(self):
        """
        Tuple pair (row, page).

        ``row`` is the index from top of window, and 'page' is number of page
        items scrolled.
        """
        return (self.vitem_idx, self.vitem_shift)

    @position.setter
    def position(self, pos_tuple):
        # pylint: disable=C0111
        #         Missing docstring
        self.vitem_idx, self.vitem_shift = pos_tuple
        self._chk_bounds()

    @property
    def visible_content(self):
        """ Returns visible content only. """
        _, shift = self.position
        return self.content[shift:shift + self.visible_height]

    @property
    def visible_bottom(self):
        """ Visible bottom-most item of lightbar. """
        if self.vitem_shift + (self.visible_height - 1) > len(self.content):
            return len(self.content)
        else:
            return self.visible_height

    @property
    def vitem_idx(self):
        """
        Relative visible item index within view.

        Index of selected item relative by index to only the length of the list
        that is visible, without accounting for scrolled content.
        """
        return self._vitem_idx

    @vitem_idx.setter
    def vitem_idx(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        if self._vitem_idx != value:
            self._vitem_lastidx = self._vitem_idx
            self._moved = True
        self._vitem_idx = value

    @property
    def vitem_shift(self):
        """
        Index of top-most item in viewable window, non-zero when scrolled.

        This value effectively represents the number of items not in view
        due to paging.
        """
        return self._vitem_shift

    @vitem_shift.setter
    def vitem_shift(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        if self._vitem_shift != value:
            self._vitem_lastshift = self._vitem_shift
            self._moved = True
        self._vitem_shift = value

    def _chk_bounds(self):
        """ Shift pages and selection until selection is within bounds. """
        # if selected item is out of range of new list, then scroll to last
        # page, and move selection to end of screen,
        if self.vitem_shift and (self.index + 1) > len(self.content):
            self.vitem_shift = len(self.content) - self.visible_height + 1
            self.vitem_idx = self.visible_height - 2

        # if we are a shifted window, shift 1 line up while keeping our
        # lightbar position until the bottom-most item is within visable range.
        while (self.vitem_shift and self.vitem_shift + self.visible_height - 1
                > len(self.content)):
            self.vitem_shift -= 1
            self.vitem_idx += 1

        # When a window is not shiftable, ensure selection is less than
        # total items. (truncate to last item)
        while self.vitem_idx > 0 and self.index >= len(self.content):
            self.vitem_idx -= 1

    def move_down(self):
        """ Move selection down one row, return string suitable for refresh. """
        if self.at_bottom:
            # bounds check
            return u''
        if self.vitem_idx + 1 < self.visible_bottom:
            # move down 1 row
            self.vitem_idx += 1
        elif self.vitem_idx < len(self.content):
            # scroll down 1 row
            self.vitem_shift += 1
        return self.refresh_quick()

    def goto(self, index):
        """ Move selection to given index. """
        assert index >= 0 and index < len(self.content)
        row, shift = self.position
        while (row + shift) < index:
            if row < (self.visible_height - 1):
                row += 1
            else:
                shift += 1
        while (row + shift) > index:
            if row > 0:
                row -= 1
            else:
                shift -= 1
        self.position = row, shift
        return self.refresh_quick()

    def move_up(self):
        """ Move selection up one row, return string suitable for refresh. """
        if self.at_top:
            # bounds check
            return u''
        elif self.vitem_idx >= 1:
            # move up 1 row
            self.vitem_idx -= 1
        elif self.vitem_shift > 0:
            # scroll up 1 row
            self.vitem_shift -= 1
        return self.refresh_quick()

    def move_pagedown(self):
        """ Move selection down one page, return string suitable for refresh. """
        if len(self.content) < self.visible_height:
            # move to last entry
            if self.vitem_idx == len(self.content) - 1:
                return u''  # already at end
            self.vitem_idx = len(self.content) - 1
        elif (self.vitem_shift + self.visible_height
                < (len(self.content) - self.visible_height)):
            # previous page
            self.vitem_shift = self.vitem_shift + self.visible_height
        elif self.vitem_shift != len(self.content) - self.visible_height:
            # shift window to last page
            self.vitem_shift = len(self.content) - self.visible_height
        else:
            # already at last page, goto end
            return self.move_end()
        return self.refresh_quick()

    def move_pageup(self):
        """ Move selection up one page, return string suitable for refresh. """
        if len(self.content) < self.visible_height - 1:
            self.vitem_idx = 0
        if self.vitem_shift - self.visible_height > 0:
            # previous page
            self.vitem_shift = self.vitem_shift - self.visible_height
        elif self.vitem_shift > 0:
            # shift window to first page
            self.vitem_shift = 0
        else:
            # already at first page, goto home
            return self.move_home()
        return self.refresh_quick()

    def move_home(self):
        """ Move selection to first row, return string suitable for refresh. """
        if (0, 0) == (self.vitem_idx, self.vitem_shift):
            return u''  # already at home
        self.vitem_idx = 0
        self.vitem_shift = 0
        return self.refresh_quick()

    def move_end(self):
        """ Move selection to final row, return string suitable for refresh. """
        if len(self.content) < self.visible_height:
            if self.vitem_idx == len(self.content) - 1:
                return u''  # already at end
            self.vitem_idx = len(self.content) - 1
        else:
            self.vitem_shift = len(self.content) - self.visible_height
            self.vitem_idx = self.visible_height - 1
        return self.refresh_quick()
