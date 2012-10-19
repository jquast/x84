"""
ansiwin package for x/84 BBS http://github.com/jquast/x84
"""
from bbs.cp437 import CP437TABLE
from bbs.session import getsession
from bbs.strutils import ansilen

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
        self.height = height
        self.width = width
        self.yloc = yloc
        self.xloc = xloc
        self.init_theme ()

    def init_theme(self):
        """
        This initializer sets glyphs and colors appropriate for a "theme",
        override this method to create a common color and graphic set.
        """
        term = getsession().terminal
        if term.number_of_colors != 0:
            self.colors['border'] = term.cyan
            self.colors['highlight'] = term.cyan + term.reverse
            self.colors['lowlight'] = term.normal
            self.colors['normal'] = term.normal
        if getsession().env.get('TERM') == 'unknown':
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

    def resize(self, height=None, width=None, yloc=None, xloc=None):
        """
        Adjust window dimensions.
        """
        assert (height, width, yloc, xloc) != (None, None, None, None)
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
        term = getsession().terminal
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

    def pos(self, xloc=None, yloc=None):
        """
        Returns terminal sequence to move cursor to window-relative position.
        """
        term = getsession().terminal
        if xloc is None:
            xloc = 0
        if yloc is None:
            yloc = 0
        return term.move (yloc + self.yloc, xloc + self.xloc)

    def title(self, ansi_text):
        """
        Returns sequence that positions and displays unicode sequence
        'ansi_text' at the title location of the window.
        """
        xloc = self.width / 2 - (min(ansilen(ansi_text) / 2, self.width / 2))
        return self.pos(xloc=xloc, yloc=0) + ansi_text

    def footer(self, ansi_text):
        """
        Returns sequence that positions and displays unicode sequence
        'ansi_text' at the bottom edge of the window.
        """
        xloc = self.width / 2 - (min(ansilen(ansi_text) / 2, self.width / 2))
        return self.pos(xloc=xloc, yloc=self.height) + ansi_text


    def border(self):
        """
        Return a unicode sequence suitable for drawing a border of this window
        using self.colors['border'] and glyphs: 'top-left', 'top-horiz',
        'top-right', 'left-vert', 'right-vert', 'bot-left', 'bot-horiz', and
        'bot-right'.
        """
        #pylint: disable=R0912
        #        Too many branches (17/12)
        ret = self.colors.get('border', u'')
        thoriz = self.glyphs.get('top-horiz', u'') * (self.width - 2)
        bhoriz = self.glyphs.get('bot-horiz', u'') * (self.width - 2)
        topright = self.glyphs.get('top-right', u'')
        botright = self.glyphs.get('bot-right', u'')
        for row in range(0, self.height):
            # top to bottom
            for col in range (0, self.width):
                # left to right
                if (col == 0) or (col == self.width - 1):
                    ret += self.pos(col, row)
                    if (row == 0) and (col == 0):
                        # top left
                        ret += self.glyphs.get('top-left', u'')
                    elif (row == self.height - 1) and (col == 0):
                        # bottom left
                        ret += self.glyphs.get('bot-left', u'')
                    elif (row == 0):
                        # top right
                        ret += self.glyphs.get('top-right', u'')
                    elif (row == self.height - 1):
                        # bottom right
                        ret += self.glyphs.get('bot-right', u'')
                    elif col == 0:
                        # left vertical line
                        ret += self.glyphs.get('left-vert', u'')
                    elif col == self.width - 1:
                        # right vertical line
                        ret += self.glyphs.get('right-vert', u'')
                elif (row == 0):
                    # top row (column 1)
                    if thoriz == u'':
                        if topright != u'':
                            # prepare for top-right, (horiz skipped)
                            ret += self.pos(self.width -1, row)
                    else:
                        # horizontal line
                        ret += thoriz
                    # top-right,
                    ret += topright
                    break
                elif (row == self.height - 1):
                    # bottom row (column 1)
                    if bhoriz == u'':
                        if botright != u'':
                            # prepare for bot-right, (horiz skipped)
                            ret += self.pos(self.width -1, row)
                    else:
                        # horizontal line
                        ret += bhoriz
                    # top-right,
                    ret += botright
                    break
        ret += self.colors.get('border', u'')
        return ret

    def erase(self):
        """
        Erase window contents (including border)
        """
        return self.pos(0, 0) + u''.join([self.pos(xloc=0, yloc=y) +
            self.glyphs.get('erase', u'') for y in range(self.height)])

    def clear(self):
        """
        Erase only window contents, border remains.
        """
        ret = self.pos(1, 1)
        ret += u''.join([self.pos(xloc=1, yloc=y) + self.glyphs('erase', u'')
            for y in range(self.height -2)])
        return ret
