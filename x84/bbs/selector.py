"""
Left/Right lightbar choice selector for x/84, https://github.com/jquast/x84
"""
from x84.bbs.ansiwin import AnsiWindow

VI_KEYSET = {
    'refresh': [unichr(12)],
    'toggle': [u' '],
    'left': [u'h'],
    'right': [u'l'],
    'enter': [u'\r'],
    'exit': [u'q', u'Q', unichr(27), ],
}


class Selector(AnsiWindow):
    """
    A two-state horizontal lightbar interface.
    """
    # pylint: disable=R0902,R0913,R0904
    #        Too many instance attributes (8/7)
    #        Too many arguments (6/5)
    #        Too many public methods (25/20)

    def __init__(self, yloc, xloc, width, left, right):
        """
        Set screen position of Selector UI and display width of both. The
        highlighted selection is displayed using the self.highlight attribute,
        in order (left, right). The default selection is left.
        """
        self._left = self._selection = left
        self._right = right
        self._moved = False
        self._quit = False
        self._selected = False
        AnsiWindow.__init__(self, 1, width, yloc, xloc)  # height is 1
        self.init_theme()
        self.keyset = VI_KEYSET
        self.init_keystrokes()

    def init_theme(self):
        """
        Initialize colors['selected'] and colors['unselected'].
        """
        from x84.bbs.session import getterminal
        term = getterminal()
        AnsiWindow.init_theme(self)
        self.colors['selected'] = term.reverse
        self.colors['unselected'] = term.normal

    def init_keystrokes(self):
        """
        Merge curses-detected application keys into a VI_KEYSET-formatted
        keyset, for keys 'refresh', 'left', 'right', 'enter', and 'exit'.
        """
        from x84.bbs.session import getterminal
        term = getterminal()
        self.keyset['refresh'].append(term.KEY_REFRESH)
        self.keyset['left'].append(term.KEY_LEFT)
        self.keyset['right'].append(term.KEY_RIGHT)
        self.keyset['enter'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_ESCAPE)

    def process_keystroke(self, keystroke):
        """
        Process a keystroke, toggling self.selection and returning string
        suitable for refresh when changed.
        """
        self._moved = False
        if keystroke in self.keyset['refresh']:
            return self.refresh()
        elif keystroke in self.keyset['left']:
            return self.move_left()
        elif keystroke in self.keyset['right']:
            return self.move_right()
        elif keystroke in self.keyset['toggle']:
            return self.toggle()
        elif keystroke in self.keyset['exit']:
            self._quit = True
        elif keystroke in self.keyset['enter']:
            self._selected = True
        return u''

    def read(self):
        """
        Reads input until the ENTER or ESCAPE key is pressed (Blocking).
        Allows backspacing. Returns unicode text, or None when cancelled.
        """
        from x84.bbs import getch
        from x84.bbs.output import echo
        self._selected = False
        self._quit = False
        echo(self.refresh())
        while not (self.selected or self.quit):
            echo(self.process_keystroke(getch()) or u'')
        if self.quit:
            return None
        return self.selection

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
    def selection(self):
        """
        Current selection.
        """
        return self._selection

    @selection.setter
    def selection(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        assert value in (self._left, self._right)
        if self._selection != value:
            self._moved = True
            self._selection = value

    @property
    def left(self):
        """
        Left-side value
        """
        return self._left

    @left.setter
    def left(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._left = value

    @property
    def right(self):
        """
        Right-side value
        """
        return self._right

    @right.setter
    def right(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._right = value

    def refresh(self):
        """
        Return terminal sequence suitable for re-drawing left/right menubar.
        """
        import math
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        attr_l = (self.colors.get('selected', u'')
                  if self.selection == self.left
                  else self.colors.get('unselected'))
        attr_r = (self.colors.get('selected', u'')
                  if self.selection == self.right
                  else self.colors.get('unselected'))
        return u''.join((
            self.pos(0, 0), term.normal, attr_l,
            self.left.center(int(math.ceil(float(self.width) / 2))),
            term.normal, attr_r,
            self.right.center(int(math.floor(float(self.width) / 2))),
            term.normal,))

    def move_right(self):
        """
        Force state to right, returning unicode string suitable for refresh.
        If state is unchanged, an empty string is returned.
        """
        if self.selection != self.right:
            self.selection = self.right
            return self.refresh()
        return u''

    def move_left(self):
        """
        Force state to left, returning unicode string suitable for refresh.
        If state is unchanged, an empty string is returned.
        """
        if self.selection != self.left:
            self.selection = self.left
            return self.refresh()
        return u''

    def toggle(self):
        """
        Toggle selection and return unicode string suitable for refresh.
        """
        if self.selection == self.left:
            self.selection = self.right
        else:
            self.selection = self.left
        return self.refresh()

    @property
    def quit(self):
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit
