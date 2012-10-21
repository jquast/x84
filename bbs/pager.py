"""
Pager class for x/84, http://github.com/jquast/x84/
"""
import textwrap
import bbs.output
import bbs.ansiwin

NETHACK_KEYSET = {
        'refresh': [unichr(12), ],
        'home': [u'y', ],
        'end': [u'n', ],
        'pgup': [u'h', u'K'],
        'pgdown': [u'l', u'J'],
        'up': [u'k', ],
        'down': [u'j', ],
        'exit': [u'q', u'Q'],
        }

class Pager(bbs.ansiwin.AnsiWindow):
    """
    Scrolling ansi viewer
    """
    #pylint: disable=R0904,R0902
    #        Too many public methods (24/20)
    #        Too many instance attributes (11/7)

    def __init__(self, height, width, yloc, xloc):
        bbs.ansiwin.AnsiWindow.__init__ (self, height, width, yloc, xloc)
        self._xpadding = 1
        self._ypadding = 1
        self._col = 0
        self._row = 0
        self._position = 0
        self._position_last = 0
        self._moved = False
        self._quit = False
        self.content = list ()
        self.keyset = dict ()
        self.init_keystrokes ()

    @property
    def moved(self):
        """
        Returnes: True if last call to process_keystroke() resulted in
        movement.
        """
        return self._position != self._position_last

    @property
    def quit(self):
        """
        Returns: True if a terminating or quit character was handled by
        process_keystroke(), such as the escape key, or 'q' by default.
        """
        return self._quit

    @property
    def position_last(self):
        """
        Previous position before last move
        """
        return self._position_last

    @property
    def position(self):
        """
        Returns the row in the content buffer displayed at top of window.
        """
        return self._position

    @position.setter
    def position(self, pos):
        #pylint: disable=C0111
        #         Missing docstring
        self._position_last = self.position
        self._position = pos
        # bounds check
        if self._position < 0:
            self._position = 0
        bottom = max(0, len(self.content) - self._visible_height)
        if self._position > bottom:
            self._position = bottom

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
            self.keyset['home'].append (term.KEY_HOME)
        if u'' != term.KEY_END:
            self.keyset['end'].append (term.KEY_END)
        if u'' != term.KEY_PPAGE:
            self.keyset['pgup'].append (term.KEY_PPAGE)
        if u'' != term.KEY_NPAGE:
            self.keyset['pgdown'].append (term.KEY_NPAGE)
        if u'' != term.KEY_UP:
            self.keyset['up'].append (term.KEY_KEY_UP)
        if u'' != term.KEY_DOWN:
            self.keyset['down'].append (term.KEY_DOWN)
        if u'' != term.KEY_EXIT:
            self.keyset['exit'].append (term.KEY_EXIT)

    def process_keystroke(self, keystroke):
        """
        Process the keystroke received by run method and return terminal
        sequence suitable for refreshing when that keystroke modifies the
        window.
        """
        #pylint: disable=R0911
        #        Too many return statements (9/6)
        self._position_last = self._position
        if keystroke in self.keyset['refresh']:
            return self.refresh ()
        elif keystroke in self.keyset['up']:
            return self._up ()
        elif keystroke in self.keyset['down']:
            return self._down ()
        elif keystroke in self.keyset['home']:
            return self._home ()
        elif keystroke in self.keyset['end']:
            return self._end ()
        elif keystroke in self.keyset['pgup']:
            return self._pgup ()
        elif keystroke in self.keyset['pgdown']:
            return self._pgdown ()
        elif keystroke in self.keyset['exit']:
            self._quit = True
            return u''
        return u''

    def _home(self):
        """
        Scroll to top.
        """
        self.position = 0
        if self.moved:
            return self.refresh ()
        return u''

    def _end(self):
        """
        Scroll to bottom.
        """
        self.position = len(self.content) - self._visible_height
        if self.moved:
            return self.refresh ()
        return u''

    def _pgup(self, num=1):
        """
        Scroll up ``num`` pages.
        """
        self.position -= (num * (self._visible_height))
        return self.refresh() if self.moved else u''

    def _pgdown(self, num=1):
        """
        Scroll down ``num`` pages.
        """
        self.position += (num * (self._visible_height))
        return self.refresh() if self.moved else u''

    def _down(self, num=1):
        """
        Scroll down ``num`` rows.
        """
        self.position -= num
        if self.moved:
            return self.refresh ()
        return u''

    def _up(self, num=1):
        """
        Scroll up ``num`` rows.
        """
        self.position += num
        if self.moved:
            return self.refresh ()
        return u''

    def refresh(self, start_row=0):
        """
        Return unicode string suitable for refreshing pager window.
        """
        row = 0
        rstr = u''
        term = bbs.session.getsession().terminal
        visc = self.content[self.position:self.position + self._visible_height]
        xloc = self.xpadding
        # draw window contents
        for row, line in enumerate(visc):
            yloc = row + self.ypadding
            if yloc < start_row:
                continue
            rstr += self.pos (yloc, xloc) + line
        # clear to end of window
        yloc = row + self.ypadding
        while yloc < self._visible_height -1:
            yloc += 1
            rstr += self.pos (row, xloc) + u' ' * self._visible_width
        rstr += term.normal
        return rstr

    def update(self, unibytes):
        """
        Update content buffer with new ansi unicodes.
        """
        if unichr(27) in unibytes:
            self._update_ansi (unibytes)
        else:
            # standard ascii uses the python 'textwrap' module :D
            self.content = textwrap.wrap(unibytes, self._visible_width)
        return self.refresh()

    def append(self, unibytes):
        """
        Update content buffer with additional lines, using ansi unicodes.
        """
        if unichr(27) in unibytes:
            self._update_ansi ('\n'.join(self.content) + '\n' + unibytes)
        else:
            self.content.extend (textwrap.wrap(unibytes, self._visible_width))
        return self._end()

    def _update_ansi(self, unibytes=u''):
        """
        Update content buffer with new ansi art.
        """
        #pylint: disable=R0914,R0912
        #        Too many local variables (17/15)
        #        Too many branches (15/12)
        save_pos = self.position
        self.position = 0
        row = len(self.content)
        remaining = u''
        # replace all of the ansi.right(n) sequences with
        # ' ' to prevent 'bleeding' over 'ghost' glyphs when
        # scrolling (at the cost of some extra bytes).
        unibytes = bbs.output.Ansi(unibytes).seqfill()
        # my own, ansi-safe textwrap ..
        while unibytes.strip() or remaining.strip():
            nlset = [(x, z)
                    for x, z in [(unibytes.find(seq), seq)
                        for seq in ['\r\n','\n']] if x != -1
                    ] # ^-- you're not supposed to do this !
            if 0 == len(nlset):
                nlp, nlseq = -1, u''
            else:
                nlp, nlseq = min(nlset)
            newline = nlp != -1
            if (newline and max(self._visible_width + 1,
                len(bbs.output.Ansi(unibytes[:nlp]))) <= self._visible_width):
                remaining = unibytes[nlp + len(nlseq):] + remaining
                unibytes = unibytes[:nlp]
            else:
                newline = False
            if (newline or max(self._visible_width + 1,
                len(bbs.output.Ansi(unibytes))) <= self._visible_width):
                # write unibytes to content  buffer
                while row >= len(self.content):
                    self.content.append (u'')
                self.content[row] = unibytes
                unibytes = remaining
                remaining = u''
                row += 1
                continue
            wordbreak = unibytes[1:].find(' ') != -1
            pos = 0
            nxt = 0
            col = 0
            while True:
                if wordbreak:
                    # break at nearest word to margin
                    npos = unibytes[pos+1:].find(' ')
                    if npos == -1:
                        break
                    if (len(bbs.output.Ansi(unibytes[:pos + npos + 1]))
                            >= self._visible_width-1):
                        pos += 1 # forward past ' '
                        break
                    pos += npos +1
                else:
                    # break on margin
                    if nxt <= pos:
                        nxt = pos + bbs.output.Ansi(unibytes[pos:]).seqlen()
                    if nxt <= pos:
                        col += 1
                        if col == self._visible_width -1:
                            break
                    pos += 1
            remaining = unibytes[pos:] + remaining
            unibytes = unibytes[:pos]
        self.position = save_pos
        return self.refresh ()
