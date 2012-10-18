"""
leftright package for X/84 BBS, https://github.com/jquast/x84
"""
from __future__ import division
import bbs.session
import bbs.ansiwin

import math
import logging

logger = logging.getLogger()

VI_KEYSET = { 'refresh': [unichr(12),],
              'toggle': [u' ',],
              'left': [u'hj',],
              'right': [u'kl',],
              'enter': [u'\r',],
              'exit': [unichr(27), u'q'],
              }


class Selector(bbs.ansiwin.AnsiWindow):
    """
    A two-state horizontal lightbar interface.
    """
    _left = u'Left'
    _right = u'Right'
    _selection = _left
    _width = None
    _moved = False
    keyset = dict()

    def __init__(self, yloc, xloc, width=None):
        """
        Set screen position of Selector UI and optional display width. If
        unset, a suitable width of medium padding is used.
        """
        self.xloc = xloc
        self.yloc = xloc
        if width is None:
            width = 2 * (len(self._left) + len(self._right))
        bbs.ansiwin.AnsiWindow.__init__(self,
                height=1, width=width, yloc=yloc, xloc=xloc)
        self.init_theme ()
        self.init_keystrokes ()

    def init_theme (self):
        term = bbs.session.getsession().terminal
        self.colors ['selected'] = term.reverse
        self.colors ['unselected'] = term.normal

    def init_keystrokes (self):
        """
        add application keys (left, right) to keyset.
        """
        self.keyset = VI_KEYSET
        term = bbs.session.getsession().terminal
        if u'' != term.KEY_REFRESH:
            self.keyset['refresh'].append (
                term.KEY_REFRESH)
        if u'' != term.KEY_LEFT:
            self.keyset['left'].append (
                term.KEY_LEFT)
        if u'' != term.KEY_RIGHT:
            self.keyset['right'].append (
                term.KEY_RIGHT)
        if u'' != term.KEY_ENTER:
            self.keyset['enter'].append (
                term.KEY_ENTER)
        if u'' != term.KEY_EXIT:
            self.keyset['exit'].append (
                term.KEY_EXIT)

    def process_keystroke(self, keystroke):
        """
        Process a keystroke, toggling self.selection and returning string
        suitable for refresh when changed.
        """
        self._moved = False
        if keystroke in self.keyset['refresh']:
            return self.refresh ()
        elif keystroke in self.keyset['left']:
            return self.move_left ()
        elif keystroke in self.keyset['right']:
            return self.move_right ()
        elif keystroke in self.keyset['toggle']:
            return self.toggle ()
        elif keystroke in self.keyset['exit']:
            self._quit = True
            return u''
        term = getsession().terminal
        logger.debug ('invalid key, %s', term.keyname(keystroke))
        return u''

    @property
    def moved(self):
        """
        Returns: True if last call to process_keystroke() caused a new entry to
        be selected. The caller can send keystrokes and check this flag to
        indicate wether the current selection should be re-examined.
        """
        return self._moved

    @property
    def selection(self):
        """
        Current selection.
        """
        return self._selection

    @selection.setter
    def selection(self, value):
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
        self._left = value

    @property
    def right(self):
        """
        Right-side value
        """
        return self._right

    @right.setter
    def right(self, value):
        self._right = value

    def refresh(self):
        """
        Return terminal sequence suitable for re-drawing left/right menubar.
        """
        rstr = self.pos(0, 0)
        attrs = (self.colors['selected'], self.colors['unselected'])
        a_left = 0 if self.selection == self.left else 1
        a_right = 1 if self.selection == self.left else 0
        rstr += a_left + self.left.center(math.ceil(self.width / 2))
        rstr += a_right + self.right.center(math.floor(self.width / 2))
        return rstr

    def move_right(self):
        """
        Force state to right, returning unicode string suitable for refresh.
        If state is unchanged, an empty string is returned.
        """
        if self.selection != self.right:
            self.selection = self.right
            return self.refresh ()
        return u''

    def move_left(self):
        """
        Force state to left, returning unicode string suitable for refresh.
        If state is unchanged, an empty string is returned.
        """
        if self.selection != self.left:
            self.selection = self.left
            return self.refresh ()
        return u''

    def toggle(self):
        """
        Toggle selection and return unicode string suitable for refresh.
        """
        if self.selection == self.left:
            self.selection = self.right
        else:
            self.selection = self.left
        return self.refresh ()

    @property
    def quit(self):
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit
