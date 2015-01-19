""" Ansi Windowing package for x/84. """

GLYPHSETS = {
    'ascii': {
        'top-left': u'+',
        'bot-left': u'+',
        'top-right': u'+',
        'bot-right': u'+',
        'left-vert': u'|',
        'right-vert': u'|',
        'top-horiz': u'-',
        'bot-horiz': u'-', },
    'thin': {
        'top-left': chr(218).decode('cp437'),
        'bot-left': chr(192).decode('cp437'),
        'top-right': chr(191).decode('cp437'),
        'bot-right': chr(217).decode('cp437'),
        'left-vert': chr(179).decode('cp437'),
        'right-vert': chr(179).decode('cp437'),
        'top-horiz': chr(196).decode('cp437'),
        'bot-horiz': chr(196).decode('cp437'),
    },
}


class AnsiWindow(object):

    """
    Provides position-relative drawing routines within a region.

    The AnsiWindow base class provides position-relative window drawing
    routines to terminal interfaces, such as pager windows, editors, and
    lightbar lists, as well as some drawing niceties such as borders,
    text alignment
    """

    # pylint: disable=R0902,R0913
    #        Too many instance attributes
    #        Too many arguments

    def __init__(self, height, width, yloc, xloc, colors=None, glyphs=None):
        """
        Class initializer for base windowing class.

        :param int width: width of window.
        :param int height: height of window.
        :param int yloc: y-location of window.
        :param int xloc: x-location of window.
        :param dict colors: color theme.
        :param dict glyphs: bordering window character glyphs.
        """
        from x84.bbs.session import getterminal
        self._term = getterminal()

        self.height = height
        self.width = width
        self.yloc = yloc
        self.xloc = xloc
        self.init_theme(colors, glyphs)

        self._xpadding = 1
        self._ypadding = 1
        self._alignment = 'left'
        self._moved = False

    def init_theme(self, colors=None, glyphs=None):
        """
        Set glyphs and colors appropriate for "theming".

        This is called by the class initializer.
        """
        # set defaults,
        self.colors = {
            'normal': self._term.normal,
            'border': (self._term.number_of_colors and
                       self._term.cyan or self._term.normal),
        }
        self.glyphs = GLYPHSETS['thin'].copy()
        # allow user override
        if colors is not None:
            self.colors.update(colors)
        if glyphs is not None:
            self.glyphs.update(glyphs)

    @property
    def xpadding(self):
        """ Horizontal padding of window border. """
        return self._xpadding

    @xpadding.setter
    def xpadding(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._xpadding = value

    @property
    def ypadding(self):
        """ Vertical padding of window border. """
        return self._ypadding

    @ypadding.setter
    def ypadding(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._ypadding = value

    @property
    def alignment(self):
        """ Horizontal justification of text content for method ``align``. """
        return self._alignment

    @alignment.setter
    def alignment(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        assert value in ('left', 'right', 'center')
        self._alignment = value

    def align(self, text, width=None):
        """
        Return ``text`` aligned to ``width`` using ``self.alignment``.

        When None (default), the visible width of this window is used.
        """
        width = width if width is not None else (self.visible_width)
        return (self._term.rjust(text, width) if self.alignment == 'right' else
                self._term.ljust(text, width) if self.alignment == 'left' else
                self._term.center(text, width)
                )

    @property
    def visible_height(self):
        """ Visible height of window after accounting for padding.  """
        return self.height - (self.ypadding * 2)

    @property
    def visible_width(self):
        """ Visible width of window after accounting for padding. """
        return self.width - (self.xpadding * 2)

    def resize(self, height=None, width=None, yloc=None, xloc=None):
        """ Adjust window dimensions by given parameter. """
        if height is not None:
            self.height = height
        if width is not None:
            self.width = width
        if yloc is not None:
            self.yloc = yloc
        if xloc is not None:
            self.xloc = xloc

    def isinview(self):
        """ Whether this window is in bounds of terminal dimensions. """
        return (self.xloc >= 0
                and self.xloc + self.width <= self._term.width
                and self.yloc >= 0
                and self.yloc + self.height <= self._term.height)

    def willfit(self, win):
        """ Whether target window, ``win`` is within this windows bounds. """
        return (win.yloc >= self.yloc
                and win.yloc + win.height <= self.yloc + self.height
                and win.xloc >= self.xloc
                and win.xloc + win.w <= self.xloc + self.width)

    # deprecated alias
    iswithin = willfit

    def pos(self, yloc=None, xloc=None):
        """ Return sequence to move cursor to window-relative position.  """
        return self._term.move((yloc and yloc or 0) + self.yloc,
                               (xloc and xloc or 0) + self.xloc)

    def title(self, ansi_text):
        """ Return sequence for displaying text on top border of window. """
        xloc = self.width / 2 - min(self._term.length(ansi_text) / 2,
                                    self.width / 2)
        return self.pos(0, max(0, xloc)) + ansi_text

    def footer(self, text):
        """ Return sequence for displaying text on bottom border of window. """
        xloc = self.width / 2 - min(self._term.length(text) / 2,
                                    self.width / 2)
        return self.pos(max(0, self.height - 1), max(0, xloc)) + text

    def border(self):
        """ Return sequence suitable for drawing window border. """
        # pylint: disable=R0912
        #        Too many branches (17/12)
        topright = self.glyphs.get('top-right', u'*')
        thoriz = self.glyphs.get('top-horiz', u'-') * (max(0, self.width - 2))
        topleft = self.glyphs.get('top-left', u'/')
        leftvert = self.glyphs.get('left-vert', u'|')
        rightvert = self.glyphs.get('right-vert', u'|')
        botleft = self.glyphs.get('bot-left', u'\\')
        bhoriz = self.glyphs.get('bot-horiz', u'-') * (max(0, self.width - 2))
        botright = self.glyphs.get('bot-right', u'/')
        rstr = u''
        for row in range(0, self.height):
            for col in range(0, self.width):
                if col == 0 or col == self.width - 1:
                    rstr += (self.pos(row, col) + topleft
                             if row == 0 and col == 0 else
                             self.pos(row, col) + botleft
                             if row == self.height - 1 and col == 0 else
                             self.pos(row, col) + topright
                             if row == 0 else
                             self.pos(row, col) + botright
                             if row == self.height - 1 else
                             self.pos(row, col) + leftvert
                             if col == 0 else
                             self.pos(row, col) + rightvert
                             if col == self.width - 1 else
                             u'')
                elif row == 0:
                    # top row (column 1)
                    if thoriz == u'':
                        if topright != u'':
                            # prepare for top-right, (horiz skipped)
                            rstr += self.pos(row, max(0, self.width - 1))
                    else:
                        rstr += thoriz
                    rstr += topright
                    break
                elif row == self.height - 1:
                    # bottom row (column 1)
                    if bhoriz == u'':
                        if botright != u'':
                            # prepare for bot-right, (horiz skipped)
                            rstr += self.pos(row, max(0, self.width - 1))
                    else:
                        # horizontal line
                        rstr += bhoriz
                    # bot-right
                    rstr += botright
                    break
        return (self.colors.get('border', u'') + rstr +
                self.colors.get('normal', u''))

    def erase_border(self):
        """ Return sequence suitable for erasing only the window border. """
        save = self.glyphs.copy()
        for glyph in ('top-left', 'top-horiz', 'top-right',
                      'left-vert', 'right-vert',
                      'bot-left', 'bot-horiz', 'bot-right'):
            if 0 != len(self.glyphs.get(glyph, u'')):
                self.glyphs[glyph] = self.glyphs.get('erase', u' ')
        ucs = self.border()
        # pylint: disable=W0201
        #         Attribute 'glyphs' defined outside __init__
        self.glyphs = save
        return ucs

    def erase(self):
        """ Return sequence suitable for erasing full window (with border). """
        return u''.join([self.pos(y, 0)
                         + (self.glyphs.get('erase', u' ') * self.width)
                         for y in range(self.height)
                         ])

    def clear(self):
        """ Return sequence suitable for erasing contents window. """
        return u''.join([self.pos(self.ypadding + yloc, self.xpadding)
                         + (self.glyphs.get('erase', u' ')
                            * self.visible_width)
                         for yloc in range(self.visible_height)
                         ])

    @property
    def moved(self):
        """ Whether movement has occurred (bool). """
        return self._moved

    @moved.setter
    def moved(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._moved = value
