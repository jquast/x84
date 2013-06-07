"""
Output and Ansi art unicode helpers for x/84, https://github.com/jquast/x84
"""
import re
import math
import warnings
import textwrap

from x84.bbs.session import getterminal, getsession
from x84.bbs.wcwidth import wcswidth

ANSI_PIPE = re.compile(r'\|(\d{2,3})')
ANSI_COLOR = re.compile(r'\033\[(\d{2,3})m')
ANSI_RIGHT = re.compile(r'\033\[(\d{1,4})C')
ANSI_CODEPAGE = re.compile(r'\033[\(\)][AB012]')
ANSI_WILLMOVE = re.compile(r'\033\[[HJuABCDEF]')
ANSI_WONTMOVE = re.compile(r'\033\[[sm]')


class AnsiWrapper(textwrap.TextWrapper):
    # pylint: disable=C0111
    #         Missing docstring
    def _wrap_chunks(self, chunks):
        """
        ANSI-string safe varient of wrap_chunks,
        exception of movement sequences.
        """
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        chunks.reverse()
        while chunks:
            cur_line = []
            cur_len = 0
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            width = self.width - len(indent)
            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]
            while chunks:
                chunk_len = len(Ansi(chunks[-1]))
                if cur_len + chunk_len <= width:
                    cur_line.append(chunks.pop())
                    cur_len += chunk_len
                else:
                    break
            if chunks and len(Ansi(chunks[-1])) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)
            if (self.drop_whitespace
                    and cur_line
                    and cur_line[-1].strip() == ''):
                del cur_line[-1]
            if cur_line:
                lines.append(indent + u''.join(cur_line))
        return lines
AnsiWrapper.__doc__ = textwrap.TextWrapper.__doc__


def ansiwrap(ucs, width=70, **kwargs):
    """Wrap a single paragraph of Unicode Ansi sequences,
    returning a list of wrapped lines.
    """
    return AnsiWrapper(width=width, **kwargs).wrap(ucs)


def echo(ucs):
    """
    Display unicode terminal sequence.
    """
    session = getsession()
    if not isinstance(ucs, unicode):
        warnings.warn('non-unicode: %r' % (ucs,), UnicodeWarning, 2)
        return session.write(ucs.decode('iso8859-1'))
    return session.write(ucs)


def timeago(secs, precision=0):
    """
    timago(float[,int])

    Pass a duration of time and return human readable shorthand, fe.

    asctime(126.32) -> ' 2m 6s',
    asctime(70.9999, 2) -> ' 1m 10.99s'
    """
    # split by days, mins, hours, secs
    years = weeks = days = mins = hours = 0
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    years, weeks = divmod(weeks, 52)
    ((num1, num2), (label1, label2)) = (
        ((years, weeks), (u'y', u'w')) if years >= 1.0 else
        ((weeks, days), (u'w', u'd')) if weeks >= 1.0 else
        ((days, hours), (u'd', u'h')) if days >= 1.0 else
        ((hours, mins), (u'h', u'm')) if hours >= 1.0 else
        ((mins, secs), (u'm', u's')))
    return (u'%2d%s%2.*f%s' % (num1, label1, precision, num2, label2,))


class Ansi(unicode):
    """
    This unicode variation understands the effect of ansi sequences of
    printable length, as well as double-wide east asian characters on
    terminals, properly implementing .rjust, .ljust, .center, and .len.

    Other ANSI functions also provided as methods.
    """
    # pylint: disable=R0904,R0924
    #         Too many public methods (45/20)
    #         Badly implemented Container, implements __getitem__,
    #           __len__ but not __delitem__, __setitem__.

    # this is really bad; this is old kludge dating as far back as 2002 from a
    # prior period when ansi was implemented without blessings, shoehorned into
    # this unicode-derived class ..

    def __len__(self):
        """
        Return the printed length of a string that contains (some types) of
        ansi sequences. Although accounted for, strings containing sequences
        such as cls() will not give accurate returns. backspace, delete, and
        double-wide east-asian
        """
        # 'nxt' points to first *ch beyond current ansi sequence, if any.
        # 'width' is currently estimated display length.
        nxt, width = 0, 0

        # i regret the heavy re-instantiation of Ansi() ..
        for idx in range(0, unicode.__len__(self)):
            width += Ansi(self[idx:]).anspadd()
            if idx == nxt:
                nxt = idx + Ansi(self[idx:]).seqlen()
            if nxt <= idx:
                ucs = self[idx]
                if getsession().encoding == 'cp437':
                    wide = 1
                else:
                    # 'East Asian Fullwidth' and 'East Asian Wide' characters
                    # can take 2 cells, see
                    # http://www.unicode.org/reports/tr11/
                    # http://www.gossamer-threads.com/lists/python/bugs/972834
                    # we just use wcswidth, since that is what terminal
                    # client implementors seem to be using ..
                    wide = wcswidth(ucs)

                # TODO
                # my own NVT addition: allow -1 to be added to width when
                # 127 and 8 are used (BACKSPACE, DEL); as well as \x0f .!?
#                assert wide != -1 or ucs in (u'\b',
#                                            unichr(127),
#                                            unichr(15)), (
#                    'indeterminate length %r in %r' % (self[idx], self))
                width += wide if wide != -1 else 0
                nxt = idx + Ansi(self[idx:]).seqlen() + 1
        return width

    def ljust(self, width):
        return self + u' ' * (max(0, width - self.__len__()))
    ljust.__doc__ = unicode.ljust.__doc__

    def rjust(self, width):
        return u' ' * (max(0, width - self.__len__())) + self
    rjust.__doc__ = unicode.rjust.__doc__

    def center(self, width):
        split = max(0.0, float(width) - self.__len__()) / 2
        return (u' ' * (max(0, int(math.floor(split)))) + self
                + u' ' * (max(0, int(math.ceil(split)))))
    center.__doc__ = unicode.center.__doc__

    def wrap(self, width, indent=u''):
        """
        A.wrap(width) -> unicode

        Like textwrap.wrap, but honor existing linebreaks and understand
        printable length of a unicode string that contains ANSI sequences.

        Always returns single unicode string,
        rows are seperated by NVT \\r\\n newlines
        """
        lines = []
        for line in self.splitlines():
            if line.strip():
                for wrapped in ansiwrap(line, width, subsequent_indent=indent):
                    lines.append(wrapped)
            else:
                lines.append(u'')
        return '\r\n'.join(lines)

    def is_movement(self):
        """
        S.is_movement() -> bool

        Returns True if string S begins with a known terminal sequence that is
        unhealthy for padding, that is, its effects on the terminal window
        position are indeterminate.
        """
        # pylint: disable=R0911,R0912
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
        elif ANSI_CODEPAGE.match(self):
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
        elif self[2] in ('(', ')'):
            # CSI + '\([AB012]' # set G0/G1
            assert self[3] in (u'A', 'B', '0', '1', '2',)
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

    def seqfill(self, encode_pipe=False):
        """
         S.seqfill() -> unicode

           Pad string S, previously filled with the terminal
           "cursor right" sequence, ``<ESC>[<N>C``, with space character ' ',
           also used as 'erase'. Ansi art can also be compressed in this way,
           by replacing with padded u' 's, we can scroll such artwork
           bi-directionally or within pager windows without 'bleeding' at the
           cost of extra bytes.

           When encode_pipe is True, color sequences are replaced with
           user-editable pipe sequences following the guidelines of MCI
           codes, http://wiki.mysticbbs.com/mci_codes. When False (default),
           colors are stripped entirely.
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
                if encode_pipe:
                    match = ANSI_COLOR.match(self[idx:])
                    if match:
                        # http://wiki.mysticbbs.com/mci_codes
                        value = int(self[match.start():match.end() + 1]) - 30
                        if value >= 0 and value <= 60:
                            rstr += u'|%02d' % (value,)
            elif ptr <= idx:
                rstr += self[idx]
        return rstr

    def anspadd(self):
        """
         S.anspadd() -> integer

        Returns int('nn') in CSI sequence \\033[nnC for use with replacing
        ansi.right(nn) with printable characters. prevents bleeding in
        scrollable windows. Otherwise 0
        """
        right = ANSI_RIGHT.match(self)
        if right is not None:
            return int(right.group(1))
        return 0

    def encode_pipe(self):
        """
        S.encode_pipe() <==> S.seqfill(encode_pipe=True)
        """
        return self.seqfill(encode_pipe=True)

    def decode_pipe(self):
        """
        S.decode_pipe() -> unicode

        Return new terminal sequence, replacing 'pipe codes', such as u'|03'
        with this terminals equivalent attribute sequence.
        """
        term = getterminal()
        ucs = u''
        ptr = 0
        match = None
        for match in ANSI_PIPE.finditer(self):
            ucs_value = match.group(1)
            # allow escaping using a second pipe
            if match.start() and self[match.start() - 1] == '|':
                continue
            # 07 -> 7
            while ucs_value.startswith('0'):
                ucs_value = ucs_value[1:]
            int_value = 0 if 0 == len(ucs_value) else int(ucs_value, 10)
            assert int_value >= 0 and int_value <= 256
            # colors 0-7 and 16-256 are as-is term.color()
            # special accomidations for 8-15, some termcaps are ok
            # with term.color(11), whereas others have trouble, help
            # out by using dim color and bold attribute instead.
            attr = u''
            if int_value <= 7 or int_value >= 16:
                attr = term.normal + term.color(int_value)
            elif int_value <= 15:
                attr = term.normal + term.color(int_value - 8) + term.bold
            ucs += self[ptr:match.start()] + attr
            ptr = match.end()
        if match is None:
            ucs = self
        else:
            ucs += self[match.end():]
        ptr = 0
        return ''.join((ucs, term.normal))

    def seqlen(self):
        """
        S.is_sequence() -> integer

        Returns non-zero for string S that begins with an ansi sequence, with
        value of bytes until sequence is complete. Use as a 'next' pointer to
        skip past sequences.
        """
        # pylint: disable=R0911,R0912
        #        Too many return statements (19/6)
        #        Too many branches (22/12)
        slen = unicode.__len__(self)
        if 0 == slen:
            return 0  # empty string
        elif self[0] != unichr(27):
            return 0  # not a sequence
        elif 1 == slen:
            return 0  # just esc,
        elif self[1] == u'c':
            return 2  # reset
        elif 2 == slen:
            return 0  # not a sequence
        elif (self[1], self[2]) == (u'#', u'8'):
            return 3  # fill screen (DEC)
        elif ANSI_CODEPAGE.match(self) or ANSI_WONTMOVE.match(self):
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
                    if ptr2 == unicode.__len__(self):
                        return 0

                # multi-attribute SGR '[01;02(..)'(m|H)
                while self[ptr2] == ';':
                    ptr2 += 1
                    if ptr2 == unicode.__len__(self):
                        return 0
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
