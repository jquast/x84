"""
lightwin package for x/84 BBS, http://github.com/jquast/x84
"""

from bbs.ansiwin import AnsiWindow
import logging
logger = logging.getLogger()

NETHACK_KEYSET = { 'home': [u'y', ], 'end': [u'n', ], 'pgup': [u'h', ],
'pgdown': [u'l', ], 'up': [u'k', ], 'down': [u'j', ], 'quit': [u'q', ], }

class LightClass (AnsiWindow):
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
    _alignment = 'left'
    _vitem_idx = 0
    _vitem_lastidx = 0
    _vitem_shift = 0
    _vitem_lastshift = 0
    _items_len = 0
    _xpadding = 0
    _ypadding = 0
    _moved = False
    _quit = False
    content = list()
    keyset = dict

    @property
    def update(self, unicodelist=None):
        """
        Replace content of lightbar with a unicode list.
        """
        if unicodelist is None:
            unicodelist = [u'',]
        self.content = unicodelist
        self.position = (self.vitem_idx, self.vitem_shift)

    def refresh_row(self, ypos):
        """
        Return unicode byte sequence suitable for moving to location ypos of
        window-relative row, and displaying any valid entry there, or using
        glyphs['fill'] if out of bounds.
        """
        unibytes = u''
        # moveto (ypos),
        unibytes += self.pos(xloc=self.xpadding, yloc=self.ypadding + ypos)
        entry = self.vitem_shift + ypos
        if entry >= len(self.content):
            # out-of-bounds; empty window
            return self.glyphs['fill'] * self._visible_width
        # colorize,
        unibytes += (self.colors['highlight'] if entry == self.index
                else self.colors['lowlight'])
        # justified text,
        unibytes += self._align(self.content[entry], self._visible_width)
        unibytes += self.colors['normal']
        return unibytes

    def refresh (self):
        """
        Refresh full lightbar window contents
        """
        return u''.join(self.refresh_row (ypos) for ypos in
                range(self._visible_bottom))

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
                # unlight old entry
                unibytes += self.refresh_row (self._vitem_lastidx)
                # highlight new entry
                unibytes += self.refresh_row (self.vitem_idx)
        return unibytes


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
            self.keyset['home'].append (
                term.KEY_HOME)
        if u'' != term.KEY_END:
            self.keyset['end'].append (
                term.KEY_END)
        if u'' != term.KEY_PPAGE:
            self.keyset['pageup'].append (
                term.KEY_PPAGE)
        if u'' != term.KEY_NPAGE:
            self.keyset['pagedown'].append (
                term.KEY_NPAGE)
        if u'' != term.KEY_UP:
            self.keyset['up'].append (
                term.KEY_KEY_UP)
        if u'' != term.KEY_DOWN:
            self.keyset['down'].append (
                term.KEY_DOWN)
        if u'' != term.KEY_EXIT:
            self.keyset['quit'].append (
                term.KEY_EXIT)

    def process_keystroke(self, key):
        """
        Process the keystroke received by run method and take action.
        """
        self._moved = False
        if key in self.keyset['home']:
            self._home ()
        elif key in self.keyset['end']:
            self._end ()
        elif key in self.keyset['pgup']:
            self._pageup ()
        elif key in self.keyset['pgdown']:
            self._pagedown ()
        elif key in self.keyset['up']:
            self._up ()
        elif key in self.keyset['down']:
            self._down ()
        elif key in self.keyset['quit']:
            self._quit = True

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
        return self.content[self.index]

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
            logger.debug ('vitem_idx %d->%d', self._vitem_idx, value)
            self._vitem_idx = value
            self.moved = True

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
            self.moved = True

    def _chk_bounds (self):
        """
        Shift pages and selection until a selection is within bounds
        """
        # if selected item is out of range of new list, then scroll to last
        # page, and move selection to end of screen,
        if self.vitem_shift and self.index +1 > len(self.content):
            logger.warn ('vshift %d; vidx %d( index %d ) out of range for %d.',
                    self.vitem_shift, self.vitem_idx, self.index,
                    len(self.content))
            self.vitem_shift = len(self.content) - self._visible_height + 1
            self.vitem_idx = self._visible_height - 2

        # if we are a shifted window, shift 1 line up while keeping our
        # lightbar position until the bottom-most item is within visable range.
        while (self.vitem_shift and self.vitem_shift + self._visible_height - 1
                > len(self.content)):
            self.vitem_shift -= 1
            self.vitem_idx += 1

        # When a window is not shiftable, ensure selection is less than
        # total items. (truncate to last item)
        while self.vitem_idx > 0 and self.index >= len(self.content):
            self.vitem_idx -= 1

    def _down(self):
        """
        Move selection down one row.
        """
        if self.index >= len(self.content):
            return
        if self.vitem_idx + 1 < self._visible_bottom:
            self.vitem_idx += 1
        elif self.vitem_idx < len(self.content):
            self.vitem_shift += 1

    def _up(self):
        """
        Move selection up one row.
        """
        if 0 == self.index:
            return
        elif self.vitem_idx >= 1:
            self.vitem_idx -= 1
        elif self.vitem_shift > 0:
            self.vitem_shift -= 1

    def _pagedown(self):
        """
        Move selection down one page.
        """
        if len(self.content) < self._visible_height:
            self.vitem_idx = len(self.content) - 1
        elif (self.vitem_shift + self._visible_height < len(self.content)
                -self._visible_height):
            self.vitem_shift = self.vitem_shift + self._visible_height
        elif self.vitem_shift != len(self.content) - self._visible_height:
            # shift window to last page
            self.vitem_shift = len(self.content) - self._visible_height
        else:
            # already at last page, goto end
            self._end ()

    def _pageup(self):
        """
        Move selection up one page.
        """
        if len(self.content) < self._visible_height - 1:
            self.vitem_idx = 0
        if self.vitem_shift - self._visible_height > 0:
            self.vitem_shift = self.vitem_shift - self._visible_height
        elif self.vitem_shift > 0:
            self.vitem_shift = 0
        else:
            # already at first page, goto home
            self._home ()

    def _home(self):
        """
        Move selection to the very top and first entry of the list.
        """
        if (0, 0) != (self.vitem_idx, self.vitem_shift):
            self.vitem_idx = 0
            self.vitem_shift = 0

    def _end(self):
        """
        Move selection to the very last and final entry of the list.
        """
        if len(self.content) < self._visible_height:
            self.vitem_idx = len(self.content) - 1
        else:
            self.vitem_shift = len(self.content) -self._visible_height
            self.vitem_idx = self._visible_height - 1

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

    @property
    def alignment(self):
        """
        Justification of text content. One of 'left', 'right', or 'center'.
        """
        return self._alignment

    @alignment.setter
    def alignment(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        assert value in ('left', 'right', 'center')
        self._alignment = value

    def _align(self, text, width):
        """
        justify text to width according to alignment prperty
        """
        return (text.rjust if self.alignment == 'right' else
                text.ljust if self.alignment == 'left' else
                text.center)(width)

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
    def _visible_bottom(self):
        """
        Visible bottom-most item of lightbar.
        """
        if self.vitem_shift + (self._visible_height -1) > len(self.content):
            return len(self.content)
        else:
            return self._visible_height

