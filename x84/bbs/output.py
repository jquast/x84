""" Terminal output package for x/84. """
import warnings
import inspect
import random
import glob
import os
import re

# local
from x84.bbs.ini import get_ini
from x84.bbs.session import getterminal, getsession

# 3rd-party
from sauce import SAUCE

#: A mapping of SyncTerm fonts/code pages to their sequence value, for use
#: as argument ``font_name`` of :func:`syncterm_setfont`.
#:
#: Where matching, their python-standard encoding value is used, (fe. 'cp437').
#: Otherwise, the lower-case named of the font is used.
#:
#: source:
#: http://cvs.synchro.net/cgi-bin/viewcvs.cgi/*checkout*/src/conio/cterm.txt
SYNCTERM_FONTMAP = (
    "cp437", "cp1251", "koi8_r", "iso8859_2", "iso8859_4", "cp866",
    "iso8859_9", "haik8", "iso8859_8", "koi8_u", "iso8859_15", "iso8859_4",
    "koi8_r_b", "iso8859_4", "iso8859_5", "ARMSCII_8", "iso8859_15",
    "cp850", "cp850", "cp885", "cp1251", "iso8859_7", "koi8-r_c",
    "iso8859_4", "iso8859_1", "cp866", "cp437", "cp866", "cp885",
    "cp866_u", "iso8859_1", "cp1131", "c64_upper", "c64_lower",
    "c128_upper", "c128_lower", "atari", "pot_noodle", "mo_soul",
    "microknight", "topaz",)

#: Translation map for embedded font hints in SAUCE records as documented at
#: http://www.acid.org/info/sauce/sauce.htm section FontName. Used by
#: :func:`showart` to automatically determine which codepage to be used
#: by utf8 terminals to provide an approximate translation.
SAUCE_FONT_MAP = {
    'Amiga MicroKnight': 'amiga',
    'Amiga MicroKnight+': 'amiga',
    'Amiga mOsOul': 'amiga',
    'Amiga P0T-NOoDLE': 'amiga',
    'Amiga Topaz 1': 'amiga',
    'Amiga Topaz 1+': 'amiga',
    'Amiga Topaz 2': 'amiga',
    'Amiga Topaz 2+': 'amiga',
    'Atari ATASCII': 'atari',
    'IBM EGA43': 'cp437',
    'IBM EGA': 'cp437',
    'IBM VGA25G': 'cp437',
    'IBM VGA50': 'cp437',
    'IBM VGA': 'cp437',
}

# IBM-PC code pages
for page in (
    '437', '720', '737', '775', '819', '850', '852', '855', '857', '858',
    '860', '861', '862', '863', '864', '865', '866', '869', '872',
):
    codec = 'cp%s' % (page,)
    SAUCE_FONT_MAP.update({
        'IBM EGA43 %s' % (page,): codec,
        'IBM EGA %s' % (page,): codec,
        'IBM VGA25g %s' % (page,): codec,
        'IBM VGA50 %s' % (page,): codec,
        'IBM VGA %s' % (page,): codec,
    })

#: simple regular expression for matching simple ansi colors,
#: for use by :func:`encode_pipe`.
RE_ANSI_COLOR = re.compile(r'\033\[(\d{2,3})m')


def syncterm_setfont(font_name, font_page=0):
    """
    Send SyncTerm's sequence for selecting a "font" codepage.

    :param str font_name: any value of :py:const:`SYNCTERM_FONTMAP`.
    :param int font_page:

    Reference::

        CSI [ p1 [ ; p2 ] ] sp D
        Font Selection
        Defaults: p1 = 0  p2 = 0
        "sp" indicates a single space character.
        Sets font p1 to be the one indicated by p2.  Currently only the primary
        font (Font zero) and secondary font (Font one) are supported.  p2 must
        be between 0 and 255.  Not all output types support font selection.
        Only X11 and SDL currently do.

    source:
    http://cvs.synchro.net/cgi-bin/viewcvs.cgi/*checkout*/src/conio/cterm.txt

    """
    # font_code is the index of font_name in SYNCTERM_FONTMAP, so that
    # syncterm_setfont('topaz') becomes value 40, and returns sequence
    # "\x1b[0;40 D'
    try:
        font_code = SYNCTERM_FONTMAP.index(font_name)
    except IndexError:
        raise ValueError("The specified font_name={0!r} is not any of the "
                         "available fonts specified in module {1}, table "
                         "SYNCTERM_FONTMAP. Available values: {2!r}".format(
                             font_name, __name__, SYNCTERM_FONTMAP))
    return u'\x1b[{0};{1} D'.format(font_page, font_code)


def echo(ucs):
    """
    Display unicode terminal sequence.

    :param str ucs: unicode sequence to write to terminal.
    """
    session = getsession()
    if not isinstance(ucs, unicode):
        warnings.warn('non-unicode: %r' % (ucs,), UnicodeWarning, 2)
        return session.write(ucs.decode('iso8859-1'))
    return session.write(ucs)


def timeago(secs, precision=0):
    """
    Return human-readable string of seconds elapsed.

    :param int secs: number of seconds "ago".
    :param int precision: optional decimal precision of returned seconds.

    Pass a duration of time and return human readable shorthand, fe::

        >>> asctime(126.32)
        ' 2m 6s',
        >>> asctime(70.9999, 2)
        ' 1m 10.99s'
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


def decode_pipe(ucs):
    """
    Return ucs containing 'pipe codes' with terminal color sequences.

    These are sometimes known as LORD codes, as they were used in the DOS Door
    game of the same name. Compliments :func:`encode_pipe`.

    :param str ucs: string containing 'pipe codes'.
    :rtype: str
    """
    # simple optimization, no '|' ? exit early!
    if u'|' not in ucs:
        return ucs
    term = getterminal()
    outp = u''
    ptr = 0
    match = None
    ANSI_PIPE = re.compile(r'\|(\d{2,3}|\|)')

    for match in ANSI_PIPE.finditer(ucs):
        val = match.group(1)
        # allow escaping using a second pipe
        if val == u'|':
            outp += ucs[ptr:match.start() + 1]
            ptr = match.end()
            continue
        # 0..7 -> 7
        while val.startswith('0'):
            val = val[1:]
        int_value = 0 if 0 == len(val) else int(val, 10)
        assert int_value >= 0 and int_value <= 256
        # colors 0-7 and 16-256 are as-is term.color()
        # special accommodations for 8-15, some termcaps are ok
        # with term.color(11), whereas others have trouble, help
        # out by using dim color and bold attribute instead.
        attr = u''
        if int_value == 7:
            attr = term.normal
        elif int_value < 7 or int_value >= 16:
            attr = term.normal + term.color(int_value)
        elif int_value <= 15:
            attr = term.normal + term.color(int_value - 8) + term.bold
        outp += ucs[ptr:match.start()] + attr
        ptr = match.end()

    outp = ucs if match is None else u''.join((outp, ucs[match.end():]))
    return u''.join((outp, term.normal))


def encode_pipe(ucs):
    """
    Given a string containing ECMA-48 sequence, replace with "pipe codes".

    These are sometimes known as LORD codes, as they were used in the DOS Door
    game of the same name. Compliments :func:`decode_pipe`.

    :param str ucs: string containing ECMA-48 sequences.
    :rtype: str
    """
    # (dead url ...)
    # http://wiki.mysticbbs.com/mci_codes
    #
    # TODO: Support all kinds of terminal color sequences,
    # such as kermit or avatar or some such, something non-emca,
    # upstream blessed project is looking for a SequenceIterator
    # class, https://github.com/jquast/blessed/issues/29
    outp = u''
    nxt = 0
    for idx in range(0, len(ucs)):
        if idx == nxt:
            # at sequence, point beyond it,
            match = RE_ANSI_COLOR.match(ucs[idx:])
            if match:
                nxt = idx + len(match.group(0))
                value = int(match.group(1)) - 30
                if value >= 0 and value <= 60:
                    outp += u'|%02d' % (value,)
        if nxt <= idx:
            # append non-sequence to outp,
            outp += ucs[idx]
            # point beyond next sequence, if any,
            # otherwise point to next character
            nxt = idx + 1
    return outp


def ropen(filename, mode='rb'):
    """ Open random file using wildcard (glob). """
    files = glob.glob(filename)
    return open(random.choice(files), mode) if len(files) else None


def showart(filepattern, encoding=None, auto_mode=True, center=False,
            poll_cancel=False, msg_cancel=None, force=False):
    """
    Yield unicode sequences for any given ANSI Art (of art_encoding).

    Effort is made to parse SAUCE data, translate input to unicode, and trim
    artwork too large to display.  If ``poll_cancel`` is not ``False``,
    represents time as float for each line to block for keypress -- if any is
    received, then iteration ends and ``msg_cancel`` is displayed as last line
    of art.

    If you provide no ``encoding``, the piece encoding will be based on either
    the encoding in the SAUCE record, the configured default or the default
    fallback ``CP437`` encoding.

    Alternate codecs are available if you provide the ``encoding`` argument.
    For example, if you want to show an Amiga style ASCII art file::

        >>> from x84.bbs import echo, showart
        >>> for line in showart('test.asc', 'topaz'):
        ...     echo(line)

    The ``auto_mode`` flag will, if set, only respect the selected encoding if
    the active session is UTF-8 capable.

    If ``center`` is set to ``True``, the piece will be centered respecting the
    current terminal's width.

    If ``force`` is set to true then the artwork will be displayed even if it's
    wider than the screen.

    """
    # pylint: disable=R0913,R0914
    #         Too many arguments
    #         Too many local variables
    term = getterminal()

    # When the given artfile pattern's folder is not absolute, nor relative to
    # our cwd, build a relative position of the folder by the calling module's
    # containing folder.  This only works for subdirectories (like 'art/').
    _folder = os.path.dirname(filepattern)
    if not (_folder.startswith(os.path.sep) or os.path.isdir(_folder)):
        # On occasion, after a general exception in a script, re-calling the
        # same script may cause yet another exception, HERE.  The 2nd call is
        # fine though; this only would effect a developer.
        #
        # Just try again.
        caller_module = inspect.stack()[1][1]
        rel_folder = os.path.dirname(caller_module)
        if _folder:
            rel_folder = os.path.join(rel_folder, _folder)
        if os.path.isdir(rel_folder):
            filepattern = os.path.join(
                rel_folder,
                os.path.basename(filepattern))

    # Open the piece
    try:
        filename = os.path.relpath(random.choice(glob.glob(filepattern)))
    except IndexError:
        filename = None

    if filename is None:
        yield u''.join((
            term.bold_red(u'-- '),
            u'no files matching {0}'.format(filepattern),
            term.bold_red(u' --'),
        ))
        return

    file_basename = os.path.basename(filename)

    # Parse the piece
    parsed = SAUCE(filename)

    # If no explicit encoding is given, we go through a couple of steps to
    # resolve the possible file encoding:
    if encoding is None:
        # 1. See if the SAUCE record has a font we know about, it's in the
        #    filler
        if parsed.record and parsed.filler_str in SAUCE_FONT_MAP:
            encoding = SAUCE_FONT_MAP[parsed.filler_str]

        # 2. Get the system default art encoding,
        #    or fall-back to cp437
        else:
            encoding = get_ini('system', 'art_utf8_codec') or 'cp437'

    # If auto_mode is enabled, we'll only use the input encoding on UTF-8
    # capable terminals, because our codecs do not know how to "transcode"
    # between the various encodings.
    if auto_mode:
        def _decode(what):
            # pylint: disable=C0111
            #         Missing function docstring (col 8)
            session = getsession()
            if session.encoding == 'utf8':
                return what.decode(encoding)
            elif session.encoding == 'cp437':
                return what.decode('cp437')
            else:
                return what

    # If auto_mode is disabled, we'll just respect whatever input encoding was
    # selected before
    else:
        _decode = lambda what: what.decode(encoding)

    # For wide terminals, center piece on screen using cursor movement
    # when center=True.
    padding = u''
    if center and term.width > 81:
        padding = term.move_x((term.width / 2) - 40)
    lines = _decode(parsed.data).splitlines()
    for idx, line in enumerate(lines):

        if poll_cancel is not False and term.inkey(poll_cancel):
            # Allow slow terminals to cancel by pressing a keystroke
            msg_cancel = msg_cancel or u''.join(
                (term.normal,
                 term.bold_black(u'-- '),
                 u'canceled {0} by input'.format(os.path.basename(filename)),
                 term.bold_black(u' --'),
                 ))
            yield u'\r\n' + term.center(msg_cancel).rstrip() + u'\r\n'
            return

        line_length = term.length(line.rstrip())

        if force is False and not padding and term.width < line_length:
            # if the artwork is too wide and force=False, simply stop displaying it.
            msg_too_wide = u''.join(
                (term.normal,
                 term.bold_black(u'-- '),
                 (u'canceled {0}, too wide:: {1}'
                  .format(file_basename, line_length)),
                 term.bold_black(u' --'),
                 ))
            yield (u'\r\n' +
                   term.center(msg_too_wide).rstrip() +
                   u'\r\n')
            return
        if idx == len(lines) - 1:
            # strip DOS end of file (^Z)
            line = line.rstrip('\x1a')
            if not line.strip():
                break
        yield padding + line + u'\r\n'
    yield term.normal


def from_cp437(text):
    """ Deprecated form of ``bytes.decode('cp437_art')``. """
    warnings.warn('from_cp437() is deprecated, use bytes.decode("cp437_art")')
    return text.decode('cp437_art')
