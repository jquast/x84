"""
lightbar package for x/84 BBS, http://github.com/jquast/x84
"""
import x84.bbs.ansiwin
import x84.bbs.session

NETHACK_KEYSET = { 'home': [u'y', ],
                   'end': [u'n', ],
                   'pgup': [u'h', ],
                   'pgdown': [u'l', ],
                   'up': [u'k', ],
                   'down': [u'j', ],
                   'enter': [u'\r', ],
                   'exit': [u'q', ],
}

class Lightbar (x84.bbs.ansiwin.AnsiWindow):
    """
    This Windowing class offers a classic 'lightbar' interface.

    Instantiate with yloc, xloc, height, and width, then call the update method
    with a list of unicode strings. send keycodes to process_keystroke () to
    interactive with the 'lightbar'.
    """
    #pylint: disable=R0902
    #         Too many instance attributes (15/7)
    #pylint: disable=R0904
    #         Too many public methods (29/20)
    content = list ()

    def __init__(self, height, width, yloc, xloc):
        """
        Initialize a lightbar of height, width, y and x position.
        """
        x84.bbs.ansiwin.AnsiWindow.__init__(self, height, width, yloc, xloc)
        self._vitem_idx = 0
        self._vitem_lastidx = 0
        self._vitem_shift = 0
        self._vitem_lastshift = 0
        self._moved = False
        self._selected = False
        self._quit = False
        self.keyset = NETHACK_KEYSET
        self.init_keystrokes()
        self.init_theme()

    def update(self, keyed_uchars=None):
        """
        Replace content of lightbar with a unicode list.
        """
        if keyed_uchars is None:
            keyed_uchars = (None, u'',)
        self.content = list(keyed_uchars)
        self.position = (self.vitem_idx, self.vitem_shift)

    def refresh_row(self, row):
        """
        Return unicode byte sequence suitable for moving to location ypos of
        window-relative row, and displaying any valid entry there, or using
        glyphs['fill'] if out of bounds.
        """
        term = x84.bbs.session.getterminal()
        unibytes = u''
        unibytes += self.pos(self.ypadding + row, self.xpadding)
        entry = self.vitem_shift + row
        if entry >= len(self.content):
            # out-of-bounds;
            return self.glyphs['fill'] * self.visible_width
        unibytes += (self.colors['selected']
                if entry == self.index
                else self.colors['unselected'])
        unibytes += self.content[entry][1]
        return unibytes + term.normal

    def refresh (self):
        """
        Refresh full lightbar window contents
        """
        return u''.join(self.refresh_row (ypos) for ypos in
                range(self.visible_bottom))

    def refresh_quick (self):
        """
        Redraw only the 'dirty' portions after a 'move' has occured unless
        the page has shifted, then a full refresh is necessary.
        """
        unibytes = u''
        if (self._vitem_lastshift != self.vitem_shift
                and self._vitem_lastshift != - 1):
            # page shift, refresh entire page
            unibytes += self.refresh ()
        elif self.moved:
            if self._vitem_lastidx != -1:
                # unselected old entry
                unibytes += self.refresh_row (self._vitem_lastidx)
                # and selected new entry
                unibytes += self.refresh_row (self.vitem_idx)
        return unibytes

    def init_theme(self):
        """
        Initialize colors['selected'] and colors['unselected'].
        """
        term = x84.bbs.session.getterminal()
        self.colors['selected'] = term.reverse_green
        self.colors['unselected'] = term.white

    def init_keystrokes(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override or inherit this method to create a common color and graphic
        set.
        """
        self.keyset = NETHACK_KEYSET
        term = x84.bbs.session.getterminal()
        self.keyset['home'].append (term.KEY_HOME)
        self.keyset['end'].append (term.KEY_END)
        self.keyset['pgup'].append (term.KEY_PPAGE)
        self.keyset['pgdown'].append (term.KEY_NPAGE)
        self.keyset['up'].append (term.KEY_KEY_UP)
        self.keyset['down'].append (term.KEY_DOWN)
        self.keyset['enter'].append (term.KEY_ENTER)
        self.keyset['exit'].append (term.KEY_EXIT)

    def process_keystroke(self, key):
        """
        Process the keystroke received by run method and take action.
        """
        self._moved = False
        rstr = u''
        if key in self.keyset['home']:
            rstr += self.move_home ()
        elif key in self.keyset['end']:
            rstr += self.move_end ()
        elif key in self.keyset['pgup']:
            rstr += self.move_pageup ()
        elif key in self.keyset['pgdown']:
            rstr += self.move_pagedown ()
        elif key in self.keyset['up']:
            rstr += self.move_up ()
        elif key in self.keyset['down']:
            rstr += self.move_down ()
        elif key in self.keyset['enter']:
            self.selected = True
        elif key in self.keyset['exit']:
            self._quit = True
        return rstr

    @property
    def moved(self):
        """
        Returns: True if last call to process_keystroke() caused a new entry to
        be selected. The caller can send keystrokes and check this flag to
        indicate wether the current selection should be re-examined.
        """
        return self._moved

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
    def selection(self):
        """
        Selected content of self.content by index
        """
        return (self.content[self.index]
                if self.index > 0 and self.index < len(self.content)
                else (None, None))

    @property
    def selected(self):
        """
        Returns True when keyset['enter'] key detected in process_keystroke
        """
        return self._selected

    @selected.setter
    def selected(self, value):
        #pylint: disable=C0111
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
        Returns tuple pair (item, shift). 'item' being the listed index from
        top of window, and 'shift' being the number of items scrolled.
        """
        return (self.vitem_idx, self.vitem_shift)

    @property
    def visible_content(self):
        """
        Returns content that is visible in window
        """
        #pylint: disable=W0612
        #        Unused variable 'item'
        item, shift = self.position
        return self.content[shift:shift + self.visible_height]

    @position.setter
    def position(self, pos_tuple):
        #pylint: disable=C0111
        #         Missing docstring
        self.vitem_idx, self.vitem_shift = pos_tuple
        self._chk_bounds ()

    @property
    def vitem_idx(self):
        """
        Index of selected item relative by index to only the length of the list
        that is visible, without accounting for scrolled content.
        """
        #pylint: disable=C0111
        #         Missing docstring
        return self._vitem_idx

    @vitem_idx.setter
    def vitem_idx(self, value):
        #pylint: disable=C0111
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
        #pylint: disable=C0111
        #         Missing docstring
        return self._vitem_shift

    @vitem_shift.setter
    def vitem_shift(self, value):
        #pylint: disable=C0111
        #        Missing docstring
        if self._vitem_shift != value:
            self._vitem_lastshift = self._vitem_shift
            self._vitem_shift = value
            self._moved = True

    def _chk_bounds (self):
        """
        Shift pages and selection until a selection is within bounds
        """
        # if selected item is out of range of new list, then scroll to last
        # page, and move selection to end of screen,
        if self.vitem_shift and self.index +1 > len(self.content):
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
        if self.index >= len(self.content):
            return u''
        if self.vitem_idx + 1 < self.visible_bottom:
            self.vitem_idx += 1
        elif self.vitem_idx < len(self.content):
            self.vitem_shift += 1
        return u''

    def move_up(self):
        """
        Move selection up one row.
        """
        if 0 == self.index:
            return u''
        elif self.vitem_idx >= 1:
            self.vitem_idx -= 1
        elif self.vitem_shift > 0:
            self.vitem_shift -= 1
        return u''

    def move_pagedown(self):
        """
        Move selection down one page.
        """
        if len(self.content) < self.visible_height:
            self.vitem_idx = len(self.content) - 1
        elif (self.vitem_shift + self.visible_height < len(self.content)
                -self.visible_height):
            self.vitem_shift = self.vitem_shift + self.visible_height
        elif self.vitem_shift != len(self.content) - self.visible_height:
            # shift window to last page
            self.vitem_shift = len(self.content) - self.visible_height
        else:
            # already at last page, goto end
            return self.move_end ()
        return u''

    def move_pageup(self):
        """
        Move selection up one page.
        """
        if len(self.content) < self.visible_height - 1:
            self.vitem_idx = 0
        if self.vitem_shift - self.visible_height > 0:
            self.vitem_shift = self.vitem_shift - self.visible_height
        elif self.vitem_shift > 0:
            self.vitem_shift = 0
        else:
            # already at first page, goto home
            return self.move_home ()
        return

    def move_home(self):
        """
        Move selection to the very top and first entry of the list.
        """
        if (0, 0) != (self.vitem_idx, self.vitem_shift):
            self.vitem_idx = 0
            self.vitem_shift = 0
        return u''

    def move_end(self):
        """
        Move selection to the very last and final entry of the list.
        """
        if len(self.content) < self.visible_height:
            self.vitem_idx = len(self.content) - 1
        else:
            self.vitem_shift = len(self.content) -self.visible_height
            self.vitem_idx = self.visible_height - 1
        return u''

    @property
    def visible_bottom(self):
        """
        Visible bottom-most item of lightbar.
        """
        if self.vitem_shift + (self.visible_height -1) > len(self.content):
            return len(self.content)
        else:
            return self.visible_height


