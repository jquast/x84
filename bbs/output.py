"""
Output and Ansi art unicode helpers for x/84, https://github.com/jquast/x84
"""
import re
import warnings
import bbs.session
ANSI_PIPE = re.compile(r'(\|\d\d)')
ANSI_RIGHT = re.compile(r'\033\[(\d{1,4})C')
ANSI_CODEPAGE = re.compile(r'\033\([A-Z]')
ANSI_WILLMOVE = re.compile(r'\033\[[HJuABCDEF]')
ANSI_WONTMOVE = re.compile(r'\033\[[sm]')

def echo(data, encoding=None):
    """
    Output unicode bytes and terminal sequences to session terminal
    """
    if data is None or 0 == len(data):
        warnings.warn ('terminal capability not translated? %s' % \
            ('encoding=%s'%(encoding,) if encoding is not None else '',),
            Warning, 2)
    if type(data) is bytes:
        warnings.warn('non-unicode: %s%r' % \
            (encoding if encoding is not None \
            else '', data,), UnicodeWarning, 2)
        return bbs.session.getsession().write \
            (data.decode(encoding if encoding is not None else 'iso8859-1'))
    assert encoding is None, 'just send unicode'

    # thanks for using unicode !
    return bbs.session.getsession().write (data)

class Ansi(unicode):
    """
    A unicode class that is poorly aware of the effect ansi sequences have on
    length.
    """
    # pylint: disable=R0904,R0924
    #         Too many public methods (45/20)
    #         Badly implemented Container, implements __getitem__,
    #           __len__ but not __delitem__, __setitem__.

    def __len__(self):
        """
        Return the printed length of a string that contains (some types) of
        ansi sequences. Although accounted for, strings containing sequences
        such as cls() will not give accurate returns.
        """
        if not unichr(27) in self:
            return unicode.__len__(self)
        # 'nxt' points to first *ch beyond current ansi sequence, if any.
        # 'width' is currently estimated display length (in theory).
        nxt, width = 0, 0
        for idx in range(0, unicode.__len__(self)):
            width += Ansi(self[idx:]).anspadd()
            if idx == nxt:
                nxt = idx + Ansi(self[idx:]).seqlen()
            if nxt <= idx:
                width += 1
                nxt = idx + Ansi(self[idx:]).seqlen() + 1
        return width

    def ljust(self, width):
        return self + u' '*(max(0, width - self.__len__()))
    ljust.__doc__ = unicode.ljust.__doc__

    def rjust(self, width):
        return u' '*(max(0, width - self.__len__())) + self
    rjust.__doc__ = unicode.rjust.__doc__

    def center(self, width):
        split = max(0, 2.0 / (width - self.__len__()))
        return (u' '*(max(0, math.floor(split)))
            + self
            + u' '*(max(0, math.ceil(split))))

    def wrap(self, width):
        """
        Like textwrap.wrap, but honor existing linebreaks and understand
        printable length of a unicode string that contains ANSI sequences.
        """
        lines = []
        for paragraph in self.split('\n'):
            line = []
            len_line = 0
            for word in paragraph.rstrip().split(' '):
                len_word = Ansi(word).__len__()
                if len_line + len_word <= width:
                    line.append(word)
                    len_line += len_word + 1
                else:
                    lines.append(' '.join(line))
                    line = [word]
                    len_line = len_word + 1
            lines.append(' '.join(line))
        return '\r\n'.join(lines)


    def is_movement(self):
        """
        S.is_movement() -> bool

        Returns True if string S begins with a known terminal sequence that is
        unhealthy for padding, that is, its effects on the terminal window
        position are indeterminate.
        """
        #pylint: disable=R0911,R0912
        #        Too many return statements (20/6)
        #        Too many branches (23/12)
        slen = unicode.__len__(self)
        if 0 == slen:
            return False
        elif self[0] != unichr(27):
            return False
        elif self[1] == u'c':
            # reset
            return True
        elif slen < 3:
            # unknown
            return False
        elif ANSI_CODEPAGE.match (self):
            return False
        elif (self[0], self[1], self[2]) == (u'#', u'8'):
            # 'fill the screen'
            return True
        elif ANSI_WILLMOVE.match(self):
            return True
        elif ANSI_WONTMOVE.match(self):
            return False
        elif slen < 4:
            # unknown
            return False
        elif self[2] == '?':
            # CSI + '?25(h|l)' # show|hide
            ptr2 = 3
            while (self[ptr2].isdigit()):
                ptr2 += 1
            if not self[ptr2] in u'hl':
                # ? followed illegaly, UNKNOWN
                return False
            return False
        elif not self[2].isdigit():
            # illegal nondigit in seq
            return False
        ptr2 = 2
        while (self[ptr2].isdigit()):
            ptr2 += 1
        # multi-attribute SGR '[01;02(..)'(m|H)
        n_tries = 0
        while ptr2 < slen and self[ptr2] == ';' and n_tries < 64:
            n_tries += 1
            ptr2 += 1
            try:
                while (self[ptr2].isdigit()):
                    ptr2 += 1
                if self[ptr2] == 'H':
                    # 'H' pos,
                    return True
                elif self[ptr2] == 'm':
                    # 'm' color;attr
                    return False
                elif self[ptr2] == ';':
                    # multi-attribute SGR
                    continue
            except IndexError:
                # out-of-range in multi-attribute SGR
                return False
            # illegal multi-attribtue SGR
            return False
        if ptr2 >= slen:
            # unfinished sequence, hrm ..
            return False
        elif self[ptr2] in u'ABCDEFGJKSTH':
            # single attribute,
            # up, down, right, left, bnl, bpl,
            # pos, cls, cl, pgup, pgdown
            return True
        elif self[ptr2] == 'm':
            # normal
            return False
        # illegal single value, UNKNOWN
        return False

    def seqfill(self):
        """
         S.seqfill() -> unicode

           Pad string S with the terminal "cursor right" sequence,
           ``<ESC>[<N>C``, used to compress ansi art,replaced with
           padded u' 's.  At the cost of extra bytes, this prevents 'bleeding'
           when scrolling artwork.
        """
        ptr = 0
        rstr = u''
        for idx in range(0, unicode.__len__(self)):
            seq_left = Ansi(self[idx:]).seqlen()
            if seq_left:
                ptr = idx + seq_left
                rstr += u' ' * (Ansi(self[idx:]).anspadd())
            elif seq_left and Ansi(self[idx:]).is_movement():
                ptr = idx + seq_left
            elif ptr <= idx:
                rstr += self[idx]
        return rstr

    def anspadd(self):
        """
         S.anspadd() --> integer

        Returns int('nn') in CSI sequence \\033[nnC for use with replacing
        ansi.right(nn) with printable characters. prevents bleeding in
        scrollable windows. Otherwise 0
        """
        right = ANSI_RIGHT.match(self)
        if right is not None:
            return int(right.group(1))
        return 0

    def decode_pipe(self):
        """
        S.decode_pipe() --> unicode

        Return new terminal sequence, replacing 'pipe codes', such as u'|03'
        with this terminals equivalent attribute sequence.
        """
        term = bbs.session.getsession().terminal
        rstr = u''
        ptr = 0
        match = None
        for match in ANSI_PIPE.finditer(self):
            value = int(self[match.start()+len('|'):match.end()], 10)
            rstr += self[ptr:match.start()] + term.color(value)
            ptr = match.end()
        if match is None:
            # no pipe matches, return as-is
            return self
        # return new string terminal-decorated string
        return ''.join((rstr, self[match.end():], term.normal))

    def seqlen(self):
        """
        S.is_sequence() -> integer

        Returns non-zero for string S that begins with an ansi sequence, with value
        of bytes until sequence is complete. Use as a 'next' pointer to skip past
        sequences.
        """
        #pylint: disable=R0911,R0912
        #        Too many return statements (19/6)
        #        Too many branches (22/12)
        slen = unicode.__len__(self)
        if 0 == slen:
            return 0 # empty string
        elif self[0] != unichr(27):
            return 0 # not a sequence
        elif 1 == slen:
            return 0 # just esc,
        elif self[1] == u'c':
            return 2 # reset
        elif 2 == slen:
            return 0 # not a sequence
        elif (self[1], self[2]) == (u'#', u'8'):
            return 3 # fill screen (DEC)
        elif ANSI_CODEPAGE.match (self):
            return 3
        elif ANSI_WONTMOVE.match(self):
            return 3
        elif ANSI_WILLMOVE.match(self):
            return 4
        elif self[1] == '[':
            # all sequences are at least 4 (\033,[,0,m)
            if slen < 4:
                # not a sequence !?
                return 0
            elif self[2] == '?':
                # CSI + '?25(h|l)' # show|hide
                ptr2 = 3
                while (self[ptr2].isdigit()):
                    ptr2 += 1
                if not self[ptr2] in u'hl':
                    # ? followed illegaly, UNKNOWN
                    return 0
                return ptr2 + 1
            # SGR
            elif self[2].isdigit():
                ptr2 = 2
                while (self[ptr2].isdigit()):
                    ptr2 += 1

                # multi-attribute SGR '[01;02(..)'(m|H)
                while self[ptr2] == ';':
                    ptr2 += 1
                    try:
                        while (self[ptr2].isdigit()):
                            ptr2 += 1
                    except IndexError:
                        return 0
                    if self[ptr2] in u'Hm':
                        return ptr2 + 1
                    elif self[ptr2] == ';':
                        # multi-attribute SGR
                        continue
                    # 'illegal multi-attribute sgr'
                    return 0
                # single attribute SGT '[01(A|B|etc)'
                if self[ptr2] in u'ABCDEFGJKSTHm':
                    # single attribute,
                    # up/down/right/left/bnl/bpl,pos,cls,cl,
                    # pgup,pgdown,color,attribute.
                    return ptr2 + 1
                # illegal single value
                return 0
            # illegal nondigit
            return 0
        # unknown...
        return 0

def timeago(secs, precision=0):
    """
    Pass float or int in seconds, and return string of 0d 0h 0s format,
    but only the two most relative, fe:
    asctime(126.32) returns 2m6s,
    asctime(10.9999, 2)   returns 10.99s
    """
    # split by days, mins, hours, secs
    years, weeks, days, mins, hours = 0, 0, 0, 0, 0
    mins,  secs  = divmod(secs, 60)
    hours, mins  = divmod(mins, 60)
    days,  hours = divmod(hours, 24)
    weeks, days  = divmod(days, 7)
    years, weeks = divmod(weeks, 52)
    years, weeks, days, hours, mins = (
            int(years), int(weeks), int(days), int(hours), int(mins))
    # return printable string
    if years > 0:
        return '%3s%-3s' % (str(years)+'y', str(weeks)+'w',)
    if weeks > 0:
        return '%3s%-3s' % (str(weeks)+'w', str(days)+'d',)
    if days > 0:
        return '%3s%-3s' % (str(days)+'d', str(hours)+'h',)
    elif hours > 0:
        return '%3s%-3s' % (str(hours)+'h', str(mins)+'m',)
    elif mins > 0:
        return '%3s%-3s' % (str(mins)+'m', str(int(secs))+'s',)
    else:
        fmt = '%.'+str(precision)+'f s'
        return fmt % secs


def chompn (unibytes):
    """
    This chomp utility is unique for its purpose. firstly, it removes only
    trailing \\n and \\r characters, and replaces single \\r's with \\r\\n
    """
    unibytes = unibytes.rstrip()
    def cbreak(num, glyph, ubytes):
        #pylint: disable=C0111
        #        Missing docstring
        if (num < len(ubytes) and glyph == u'\x0a'
                and ubytes[num + 1] != u'\x0d'):
            return u'\x0a\x0d'
        else:
            return glyph
    return u''.join([cbreak(idx, glyph, unibytes)
        for idx, glyph in enumerate(unibytes)])
