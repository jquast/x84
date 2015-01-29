""" Left/Right lightbar choice selector for x/84. """
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

    """ A two-state horizontal lightbar interface. """

    # pylint: disable=R0902,R0913,R0904
    #        Too many instance attributes (8/7)
    #        Too many arguments (6/5)
    #        Too many public methods (25/20)

    def __init__(self, yloc, xloc, width, left, right, **kwargs):
        """
        Class initializer.

        Initialize a selector of width, y x, and left/right values.

        :param int width: width of window.
        :param int yloc: y-location of selector.
        :param int xloc: x-location of selector.
        :param dict colors: color theme, only key value of ``selected``
                            and ``unselected`` is used.
        :param dict keyset: command keys, global ``VI_KEYSET`` is
                            used by default, augmented by application
                            keys such as home, end, pgup, etc.
        :param str left: text string of left-side selection.
        :param str right: text string of right-side selection.
        """
        self._left = self._selection = left
        self._right = right
        self._moved = False
        self._quit = False
        self._selected = False

        self.init_keystrokes(keyset=kwargs.pop('keyset', VI_KEYSET.copy()))

        AnsiWindow.__init__(self, height=1, width=width,
                            yloc=yloc, xloc=xloc, **kwargs)

    def init_theme(self, colors=None, glyphs=None):
        from x84.bbs.session import getterminal
        term = getterminal()
        colors = colors or {
            'selected': term.reverse_yellow,
            'unselected': term.bold_black,
        }
        AnsiWindow.init_theme(self, colors=colors, glyphs=glyphs)

    def init_keystrokes(self, keyset):
        """ Sets keyboard keys for various editing keystrokes. """
        from x84.bbs.session import getterminal
        self.keyset = keyset
        term = getterminal()
        self.keyset['refresh'].append(term.KEY_REFRESH)
        self.keyset['left'].append(term.KEY_LEFT)
        self.keyset['right'].append(term.KEY_RIGHT)
        self.keyset['enter'].append(term.KEY_ENTER)
        self.keyset['exit'].append(term.KEY_ESCAPE)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke and return string to refresh.

        :param blessed.keyboard.Keystroke keystroke: input from ``inkey()``.
        :rtype: str
        :returns: string sequence suitable for refresh.
        """
        self._moved = False
        keystroke = hasattr(keystroke, 'code') and keystroke.code or keystroke
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
        """ Reads input until the ENTER or ESCAPE key is pressed (Blocking). """
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
        """ Whether the carriage return character has been handled. """
        return self._selected

    @selected.setter
    def selected(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        # this setter should only be used to reset to 'False' for recycling
        assert isinstance(value, bool)
        self._selected = value

    @property
    def selection(self):
        """ Current selection. """
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
        """ Left-side value. """
        return self._left

    @left.setter
    def left(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._left = value

    @property
    def right(self):
        """ Right-side value. """
        return self._right

    @right.setter
    def right(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._right = value

    def refresh(self):
        """ Return string sequence suitable for refresh. """
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
        """ Move selection right, return string suitable for refresh. """
        if self.selection != self.right:
            self.selection = self.right
            return self.refresh()
        return u''

    def move_left(self):
        """ Move selection left, return string suitable for refresh. """
        if self.selection != self.left:
            self.selection = self.left
            return self.refresh()
        return u''

    def toggle(self):
        """ Toggle selection, return string suitable for refresh. """
        if self.selection == self.left:
            self.selection = self.right
        else:
            self.selection = self.left
        return self.refresh()

    @property
    def quit(self):
        """ Whether a 'quit' character has been handled, such as escape. """
        return self._quit
