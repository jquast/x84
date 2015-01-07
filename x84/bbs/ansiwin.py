"""
Ansi Windowing package for x/84, http://github.com/jquast/x84
"""
from x84.bbs.session import getterminal

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
    The AnsiWindow base class provides position-relative window drawing
    routines to terminal interfaces, such as pager windows, editors, and
    lightbar lists, as well as some drawing niceities such as borders,
    text alignment
    """
    # pylint: disable=R0902
    #        Too many instance attributes (8/7)

    def __init__(self, height, width, yloc, xloc, colors=None, glyphs=None):
        """
        Constructor class for a simple Window.
        """
        self.height = height
        self.width = width
        self.yloc = yloc
        self.xloc = xloc
        self.init_theme(colors, glyphs)

        self._xpadding = 1
        self._ypadding = 1
        self._alignment = 'left'
        self._moved = False

#        assert self.isinview(), (
#            'AnsiWindow(height={self.height}, width={self.width}, '
#            'yloc={self.yloc}, xloc={self.xloc}) not in viewport '
#            'Terminal(height={term.height}, width={term.width})'
#            .format(self=self, term=getterminal()))

    def init_theme(self, colors=None, glyphs=None):
        """
        This initializer sets glyphs and colors appropriate for a "theme".
        """
        # set defaults,
        term = getterminal()
        self.colors = {
            'normal': term.normal,
            'border': term.number_of_colors and term.cyan or term.normal,
        }
        self.glyphs = GLYPHSETS['thin'].copy()
        # allow user override
        if colors is not None:
            self.colors.update(colors)
        if glyphs is not None:
            self.glyphs.update(glyphs)

    @property
    def xpadding(self):
        """
        Horizontal padding of window border
        """
        return self._xpadding

    @xpadding.setter
    def xpadding(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._xpadding = value

    @property
    def ypadding(self):
        """
        Veritcal padding of window border
        """
        return self._ypadding

    @ypadding.setter
    def ypadding(self, value):
        # pylint: disable=C0111
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
        Return ``text`` alignmnd to ``width`` using self.alignment.

        When None (default), the visible width of this window is used.
        """
        term = getterminal()
        width = width if width is not None else (self.visible_width)
        return (term.rjust(text, width) if self.alignment == 'right' else
                term.ljust(text, width) if self.alignment == 'left' else
                term.center(text, width)
                )

    @property
    def visible_height(self):
        """
        The visible height of the editor window after vertical padding.
        """
        return self.height - (self.ypadding * 2)

    @property
    def visible_width(self):
        """
        Visible width of lightbar after accounting for horizontal padding.
        """
        return self.width - (self.xpadding * 2)

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
        term = getterminal()
        return (self.xloc >= 0
                and self.xloc + self.width <= term.width
                and self.yloc >= 0
                and self.yloc + self.height <= term.height)

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
        term = getterminal()
        return term.move((yloc and yloc or 0) + self.yloc,
                         (xloc and xloc or 0) + self.xloc)

    def title(self, ansi_text):
        """
        Returns sequence that positions and displays unicode sequence
        'ansi_text' at the title location of the window.
        """
        term = getterminal()
        xloc = self.width / 2 - min(term.length(ansi_text) / 2, self.width / 2)
        return self.pos(0, max(0, xloc)) + ansi_text

    def footer(self, ansi_text):
        """
        Returns sequence that positions and displays unicode sequence
        'ansi_text' at the bottom edge of the window.
        """
        term = getterminal()
        xloc = self.width / 2 - min(term.length(ansi_text) / 2, self.width / 2)
        return self.pos(max(0, self.height - 1), max(0, xloc)) + ansi_text

    def border(self):
        """
        Return a unicode sequence suitable for drawing a border of this window
        using self.colors 'border', 'normal' and glyphs:
        'top-left', 'top-horiz', 'top-right', 'left-vert', 'right-vert',
        'bot-left', 'bot-horiz', and 'bot-right'.
        """
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
                if (col == 0) or (col == self.width - 1):
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
                elif (row == 0):
                    # top row (column 1)
                    if thoriz == u'':
                        if topright != u'':
                            # prepare for top-right, (horiz skipped)
                            rstr += self.pos(row, max(0, self.width - 1))
                    else:
                        rstr += thoriz
                    rstr += topright
                    break
                elif (row == self.height - 1):
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
        """
        Return a unicode sequence suitable for erasing
        the border of this window.
        """
        save = self.glyphs.copy()
        for glyph in ('top-left', 'top-horiz', 'top-right',
                      'left-vert', 'right-vert',
                      'bot-left', 'bot-horiz', 'bot-right'):
            if 0 != len(self.glyphs.get(glyph, u'')):
                self.glyphs[glyph] = self.glyphs.get('erase', u' ')
        ucs = self.border()
        self.glyphs = save
        return ucs

    def erase(self):
        """
        Return a unicode sequence suitable for erasing
        this window (includes border).
        """
        return u''.join([self.pos(y, 0)
                         + (self.glyphs.get('erase', u' ') * self.width)
                         for y in range(self.height)
                         ])

    def clear(self):
        """
        Return a unicode sequence suitable for erasing
        the contents of this window (border remains).
        """
        return u''.join([self.pos(self.ypadding + yloc, self.xpadding)
                         + (self.glyphs.get('erase', u' ')
                            * self.visible_width)
                         for yloc in range(self.visible_height)
                         ])

    @property
    def moved(self):
        """
        Returns True if movement has occured, can be reset to
        False by caller.
        """
        return self._moved

    @moved.setter
    def moved(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        assert type(value) is bool
        self._moved = value
