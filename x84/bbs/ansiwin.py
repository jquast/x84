"""
ansiwin package for x/84, http://github.com/jquast/x84
"""
from x84.bbs.cp437 import CP437TABLE

GLYPHSETS = { 'unknown':
        { 'top-left': u'+',
            'bot-left': u'+',
            'top-right': u'+',
            'bot-right': u'+',
            'left-vert': u'|',
            'right-vert': u'|',
            'top-horiz': u'-',
            'bot-horiz': u'-',
            'fill': u' ',
            'erase': u' ',
            },
        'thin': {
            'top-left': CP437TABLE[unichr(218)],
            'bot-left': CP437TABLE[unichr(192)],
            'top-right': CP437TABLE[unichr(191)],
            'bot-right': CP437TABLE[unichr(217)],
            'left-vert': CP437TABLE[unichr(179)],
            'right-vert': CP437TABLE[unichr(179)],
            'top-horizontal': CP437TABLE[unichr(196)],
            'bot-horizontal': CP437TABLE[unichr(196)],
            'fill': u' ',
            'erase': u' ',
            },
        'vert_thick': {
            'top-left': CP437TABLE[unichr(213)],
            'bot-left': CP437TABLE[unichr(211)],
            'top-right': CP437TABLE[unichr(183)],
            'bot-right': CP437TABLE[unichr(189)],
            'left-vert': CP437TABLE[unichr(186)],
            'right-vert': CP437TABLE[unichr(186)],
            'top-horizontal': CP437TABLE[unichr(196)],
            'bot-horizontal': CP437TABLE[unichr(196)],
            'fill': u' ',
            'erase': u' ',
            },
        }

class AnsiWindow(object):
    """
    The AnsiWindow base class provides position-relative window drawing
    routines to terminal interfaces, such as pager windows, editors, and
    lightbar lists.
    """
    #pylint: disable=R0902
    #        Too many instance attributes (8/7)
    _glyphs = dict()
    _colors = dict()

    def __init__(self, height, width, yloc, xloc):
        """
        Construct an ansi window. Its base purpose is to provide
        window-relativie positions using the pos() method.
        """
        self.height = height
        self.width = width
        self.yloc = yloc
        self.xloc = xloc
        self.glyphs = dict()
        self.init_theme ()
        self._xpadding = 1
        self._ypadding = 1
        self._alignment = 'left'

    def init_theme(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override this method to create a common color and graphic set.
        """
        import x84.bbs.session
        session = x84.bbs.session.getsession()
        term = x84.bbs.session.getterminal()
        if term.number_of_colors != 0:
            self.colors['border'] = term.cyan
            self.colors['highlight'] = term.cyan + term.reverse
            self.colors['lowlight'] = term.normal
            self.colors['normal'] = term.normal
        if session.env.get('TERM') == 'unknown':
            self.glyphs = GLYPHSETS['unknown']
        else:
            self.glyphs = GLYPHSETS['thin']

    @property
    def glyphs(self):
        """
        Key table for unicode characters for draw routines.
        """
        return self._glyphs

    @glyphs.setter
    def glyphs(self, value):
        #pylint: disable=E0102
        #        method already defined line
        #pylint: disable=C0111
        #        Missing docstring
        self._glyphs = value

    @property
    def colors(self):
        """
        Key table for terminal color sequences for draw routines.
        """
        return self._colors

    @colors.setter
    def colors(self, value):
        #pylint: disable=C0111
        #        Missing docstring
        self._colors = value

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

    def align(self, text, width=None):
        """
        justify Ansi text alignment property and width. When None (default),
        the visible width after padding is used.
        """
        import x84.bbs.output
        return (x84.bbs.output.Ansi(text).rjust
                if self.alignment == 'right'
                else x84.bbs.output.Ansi(text).ljust
                if self.alignment == 'left'
                else x84.bbs.output.Ansi(text).center
                )(width if width is not None else self.width)

    @property
    def visible_height(self):
        """
        The visible height of the editor window after vertical padding.
        """
        return self.height - (self._ypadding * 2)

    @property
    def visible_width(self):
        """
        Visible width of lightbar after accounting for horizontal padding.
        """
        return self.width - (self._xpadding * 2)

    def resize(self, height=None, width=None, yloc=None, xloc=None):
        """
        Adjust window dimensions.
        """
        if height is not None:
            self.height = height
        if width is not None:
            self.width = width
        if yloc is not None:
            self.yloc = yloc
        if xloc is not None:
            self.xloc = xloc

    def isinview(self):
        """
        Returns True if window is in view of the terminal window.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        return (self.xloc > 0 and self.xloc +self.width -1 <= term.width
            and self.yloc > 0 and self.yloc +self.height -1 <= term.height)

    def iswithin(self, win):
        """
        Returns True if our window is within the bounds of window
        """
        return (self.yloc >= win.yloc
            and self.yloc + self.height <= win.yloc + win.height
            and self.xloc >= win.xloc
            and self.xloc + self.width <= win.xloc + win.width)

    def willfit(self, win):
        """
        Returns True if target window is within our bounds
        """
        return (win.yloc >= self.yloc
            and win.yloc + win.height <= self.yloc + self.height
            and win.xloc >= self.xloc
            and win.xloc + win.w <= self.xloc + self.width)

    def pos(self, yloc=None, xloc=None):
        """
        Returns terminal sequence to move cursor to window-relative position.
        """
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        if yloc is None:
            yloc = 0
        if xloc is None:
            xloc = 0
        return term.move (yloc + self.yloc, xloc + self.xloc)

    def title(self, ansi_text):
        """
        Returns sequence that positions and displays unicode sequence
        'ansi_text' at the title location of the window.
        """
        import x84.bbs.output
        xloc = self.width / 2 - (
                min(len(x84.bbs.output.Ansi(ansi_text)) / 2, self.width / 2))
        return self.pos(0, xloc) + ansi_text

    def footer(self, ansi_text):
        """
        Returns sequence that positions and displays unicode sequence
        'ansi_text' at the bottom edge of the window.
        """
        import x84.bbs.output
        xloc = self.width / 2 - (
                min(len(x84.bbs.output.Ansi(ansi_text)) / 2, self.width / 2))
        return self.pos(self.height, xloc) + ansi_text


    def border(self):
        """
        Return a unicode sequence suitable for drawing a border of this window
        using self.colors['border'] and glyphs: 'top-left', 'top-horiz',
        'top-right', 'left-vert', 'right-vert', 'bot-left', 'bot-horiz', and
        'bot-right'.
        """
        #pylint: disable=R0912
        #        Too many branches (17/12)
        import x84.bbs.session
        term = x84.bbs.session.getterminal()
        rstr = self.colors.get('border', u'')
        thoriz = self.glyphs.get('top-horiz', u'') * (self.width - 2)
        bhoriz = self.glyphs.get('bot-horiz', u'') * (self.width - 2)
        topright = self.glyphs.get('top-right', u'')
        botright = self.glyphs.get('bot-right', u'')
        for row in range(0, self.height):
            # top to bottom
            for col in range (0, self.width):
                # left to right
                if (col == 0) or (col == self.width - 1):
                    rstr += self.pos(row, col)
                    if (row == 0) and (col == 0):
                        # top left
                        rstr += self.glyphs.get('top-left', u'')
                    elif (row == self.height - 1) and (col == 0):
                        # bottom left
                        rstr += self.glyphs.get('bot-left', u'')
                    elif (row == 0):
                        # top right
                        rstr += self.glyphs.get('top-right', u'')
                    elif (row == self.height - 1):
                        # bottom right
                        rstr += self.glyphs.get('bot-right', u'')
                    elif col == 0:
                        # left vertical line
                        rstr += self.glyphs.get('left-vert', u'')
                    elif col == self.width - 1:
                        # right vertical line
                        rstr += self.glyphs.get('right-vert', u'')
                elif (row == 0):
                    # top row (column 1)
                    if thoriz == u'':
                        if topright != u'':
                            # prepare for top-right, (horiz skipped)
                            rstr += self.pos(row, self.width -1)
                    else:
                        # horizontal line
                        rstr += thoriz
                    # top-right,
                    rstr += topright
                    break
                elif (row == self.height - 1):
                    # bottom row (column 1)
                    if bhoriz == u'':
                        if botright != u'':
                            # prepare for bot-right, (horiz skipped)
                            rstr += self.pos(row, self.width -1)
                    else:
                        # horizontal line
                        rstr += bhoriz
                    # top-right,
                    rstr += botright
                    break
        rstr += self.colors.get('border', u'')
        return rstr + term.normal

    def erase(self):
        """
        Erase window contents (including border)
        """
        return self.pos(0, 0) + u''.join([self.pos(y, 0) +
            self.glyphs.get('erase', u'') for y in range(self.height)])

    def clear(self):
        """
        Erase only window contents, border remains.
        """
        rstr = self.pos(1, 1)
        rstr += u''.join([self.pos(y, 1) + self.glyphs.get('erase', u'')
            for y in range(self.height -2)])
        return rstr
