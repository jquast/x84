"""
lightbar package for x/84 BBS, http://github.com/jquast/x84
"""
from x84.bbs.ansiwin import AnsiWindow

NETHACK_KEYSET = {'home': [u'y', '0'],
                  'end': [u'n', 'G'],
                  'pgup': [u'h', u'b'],
                  'pgdown': [u'l', u'f'],
                  'up': [u'k'],
                  'down': [u'j'],
                  'enter': [u'\r'],
                  'exit': [u'q', u'Q', unichr(27), ],
                  }


class Lightbar (AnsiWindow):
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
    content = list()

    def __init__(self, height, width, yloc, xloc):
        """
        Initialize a lightbar of height, width, y and x position.
        """
        AnsiWindow.__init__(self, height, width, yloc, xloc)
        self._vitem_idx = 0
        self._vitem_shift = 0
        self._vitem_lastidx = 0
        self._vitem_lastshift = 0
        self._selected = False
        self._quit = False
        self.keyset = NETHACK_KEYSET
        self.init_keystrokes()
        self.init_theme()

    def update(self, keyed_uchars=None):
        """
        Replace content of lightbar with iterable of aribitrary (key, unicode).
        unicode is displayed to the user, and key can be used for any
        programming purposes, such as sorting or identifying.
        """
        if keyed_uchars is None:
            keyed_uchars = (None, u'',)
        self.content = list(keyed_uchars)
        self.position = (self.vitem_idx, self.vitem_shift)

    def refresh_row(self, row):
        """
        Return unicode byte sequence suitable for moving to location ypos of
        window-relative row, and displaying any valid entry there, or using
        glyphs['erase'] if out of bounds. Strings are ansi color safe, and
        will be trimmed using glyphs['strip'] if their displayed width is
        wider than window.
        """
        import x84.bbs.session
        from x84.bbs.output import Ansi
        pos = self.pos(self.ypadding + row, self.xpadding)
        entry = self.vitem_shift + row
        if entry >= len(self.content):
            # out-of-bounds;
            return u''.join((pos,
                self.glyphs.get('erase', u' ') * self.visible_width,))

        def fit_row(ucs):
            """ Strip a unicode row to fit window boundry, if necessary """
            column = self.visible_width + 1
            wrapped = Ansi(ucs).wrap(column).splitlines()
            if len(wrapped) > 1:
                marker = self.glyphs.get('strip', u' $')
                marker_column = self.visible_width - len(marker)
                wrapped = Ansi(ucs).wrap(marker_column).splitlines()
                ucs = Ansi(wrapped[0].rstrip()).ljust(marker_column) + marker
                return ucs
            return (Ansi(ucs).ljust(column))

        term = x84.bbs.session.getterminal()
        # allow ucs data with '\r\n', to accomidate soft and hardbreaks; just
        # don't display them, really wrecks up cusor positioning.
        ucs = self.content[entry][1].strip(u'\r\n')

        # highlighted entry; strip of ansi sequences, use color 'highlight'
        # trim and append '$ ' if it cannot fit,
        if entry == self.index:
            ucs = Ansi(ucs).seqfill()
            if len(Ansi(ucs)) > self.visible_width:
                ucs = fit_row(ucs)
            return u''.join((pos,
                             self.colors.get('highlight', u''),
                             self.align(ucs),
                             term.normal,))
        # unselected entry; retain ansi sequences, decode any pipe characters,
        # trim and append '$ ' if it cannot fit
        ucs = Ansi(ucs).decode_pipe()
        if len(Ansi(ucs)) > self.visible_width:
            ucs = fit_row(ucs)
        return u''.join((pos,
                         self.colors.get('lowlight', u''),
                         self.align(ucs),
                         term.normal,))

    def fixate(self):
        """
        Reterm unicode terminal sequence for moving cursor to current
        selection.
        """
        return self.pos(self.ypadding + self.vitem_idx,
                        self.xpadding + self.visible_width)

    def refresh(self):
        """
        Refresh full lightbar window contents
        """
        return u''.join(self.refresh_row(ypos) for ypos in
                        range(max(self.visible_bottom, self.visible_height)))

    def refresh_quick(self):
        """
        Redraw only the 'dirty' portions after a 'move' has occured;
        otherwise redraw entire contents (page has shifted).
        """
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

    def init_theme(self):
        """
        Initialize color['highlight'].
        """
        from x84.bbs.session import getterminal
        self.colors['highlight'] = getterminal().reverse_green
        self.glyphs['strip'] = u' $'  # indicates content was stripped
        AnsiWindow.init_theme(self)

    def init_keystrokes(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override or inherit this method to create a common color and graphic
        set.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        self.keyset = NETHACK_KEYSET
        self.keyset['home'].append(term.KEY_HOME)
        self.keyset['end'].append(term.KEY_END)
        self.keyset['pgup'].append(term.KEY_PGUP)
        self.keyset['pgdown'].append(term.KEY_PGDOWN)
        self.keyset['up'].append(term.KEY_UP)
        self.keyset['down'].append(term.KEY_DOWN)
        self.keyset['enter'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_ESCAPE)

    def process_keystroke(self, key):
        """
        Process the keystroke received by run method and take action.
        """
        self._moved = False
        self._selected = False
        self._vitem_lastidx = self.vitem_idx
        self._vitem_lastshift = self.vitem_shift
        rstr = u''
        if key in self.keyset['home']:
            rstr = self.move_home()
        elif key in self.keyset['end']:
            rstr = self.move_end()
        elif key in self.keyset['pgup']:
            rstr = self.move_pageup()
        elif key in self.keyset['pgdown']:
            rstr = self.move_pagedown()
        elif key in self.keyset['up']:
            rstr = self.move_up()
        elif key in self.keyset['down']:
            rstr = self.move_down()
        elif key in self.keyset['enter']:
            self.selected = True
        elif key in self.keyset['exit']:
            self._quit = True
        return rstr

    def read(self):
        """
        Reads input until the ENTER or ESCAPE key is pressed (Blocking).
        Allows backspacing. Returns unicode text, or None when canceled.
        """
        from x84.bbs import getch
        from x84.bbs.output import echo
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
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit

    @property
    def index(self):
        """
        Selected index of self.content
        """
        return self.vitem_shift + self.vitem_idx

    @property
    def at_bottom(self):
        """
        Returns True if current selection is last in list
        """
        return self.index == len(self.content) - 1

    @property
    def at_top(self):
        """
        Returns True if current selection is first in list
        """
        return self.index == 0

    @property
    def selection(self):
        """
        Selected content of self.content by index
        """
        return (self.content[self.index]
                if self.index >= 0 and self.index < len(self.content)
                else (None, None))

    @property
    def selected(self):
        """
        Returns True when keyset['enter'] key detected in process_keystroke
        """
        return self._selected

    @selected.setter
    def selected(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        # this setter should only be used to reset to 'False' for recycling
        assert type(value) is bool
        self._selected = value

    @property
    def last_index(self):
        """
        Previously selected index of self.content
        """
        return self._vitem_lastshift + self._vitem_lastidx

    @property
    def position(self):
        """
        Tuple pair (row, page). 'row' is index from top of window,
        and 'page' is number of page items scrolled.
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
        """
        Returns content that is visible in window
        """
        # pylint: disable=W0612
        #        Unused variable 'item'
        item, shift = self.position
        return self.content[shift:shift + self.visible_height]

    @property
    def visible_bottom(self):
        """
        Visible bottom-most item of lightbar.
        """
        if self.vitem_shift + (self.visible_height - 1) > len(self.content):
            return len(self.content)
        else:
            return self.visible_height

    @property
    def vitem_idx(self):
        """
        Index of selected item relative by index to only the length of the list
        that is visible, without accounting for scrolled content.
        """
        # pylint: disable=C0111
        #         Missing docstring
        return self._vitem_idx

    @vitem_idx.setter
    def vitem_idx(self, value):
        # pylint: disable=C0111
        #        Missing docstring
        if self._vitem_idx != value:
            self._vitem_lastidx = self._vitem_idx
            self._vitem_idx = value
            self._moved = True

    @property
    def vitem_shift(self):
        """
        Index of top-most item in viewable window, non-zero when scrolled.
        This value effectively represents the number of items not in view
        due to paging.
        """
        # pylint: disable=C0111
        #         Missing docstring
        return self._vitem_shift

    @vitem_shift.setter
    def vitem_shift(self, value):
        # pylint: disable=C0111
        #        Missing docstring
        if self._vitem_shift != value:
            self._vitem_lastshift = self._vitem_shift
            self._vitem_shift = value
            self._moved = True

    def _chk_bounds(self):
        """
        Shift pages and selection until a selection is within bounds
        """
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
        """
        Move selection down one row.
        """
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
        """
        Move selection to index of lightbar content.
        """
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
        """
        Move selection up one row.
        """
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
        """
        Move selection down one page.
        """
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
        """
        Move selection up one page.
        """
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
        """
        Move selection to the very top and first entry of the list.
        """
        if (0, 0) == (self.vitem_idx, self.vitem_shift):
            return u''  # already at home
        self.vitem_idx = 0
        self.vitem_shift = 0
        return self.refresh_quick()

    def move_end(self):
        """
        Move selection to the very last and final entry of the list.
        """
        if len(self.content) < self.visible_height:
            if self.vitem_idx == len(self.content) - 1:
                return u''  # already at end
            self.vitem_idx = len(self.content) - 1
        else:
            self.vitem_shift = len(self.content) - self.visible_height
            self.vitem_idx = self.visible_height - 1
        return self.refresh_quick()
