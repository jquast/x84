"""
(c) 2012 Erik Rose
MIT Licensed
https://github.com/erikrose/blessings
"""
import curses.has_key
import contextlib
import platform
import logging
import termios
import struct
import fcntl
import sys


try:
    #pylint: disable=W0611
    #         Unused import IOUnsupportedOperation
    from io import UnsupportedOperation as IOUnsupportedOperation
except ImportError:
    class IOUnsupportedOperation(Exception):
        """
        dummy exception to take of Python 3's ``io.UnsupportedOperation`` in
        Python 2.
        """


__all__ = ['Terminal']


if ('3', '0', '0') <= platform.python_version_tuple() < ('3', '2', '2+'):
    # Good till 3.2.10
    # Python 3.x < 3.2.3 has a bug in which tparm() erroneously takes a string.
    raise ImportError('Blessings needs Python 3.2.3 or greater for Python 3 '
                      'support due to http://bugs.python.org/issue10570.')


class Terminal(object):
    """An abstraction around terminal capabilities

    Unlike curses, this doesn't require clearing the screen before doing
    anything, and it's friendlier to use. It keeps the endless calls to
    ``tigetstr()`` and ``tparm()`` out of your code, and it acts intelligently
    when somebody pipes your output to a non-terminal.

    Instance attributes:

      ``stream``
        The stream the terminal outputs to. It's convenient to pass the stream
        around with the terminal; it's almost always needed when the terminal
        is and saves sticking lots of extra args on client functions in
        practice.
    """
    def __init__(self, kind=None, stream=None, rows=24, columns=79):
        """Initialize the terminal.

        If ``stream`` is not a tty, I will default to returning an empty
        Unicode string for all capability values, so things like piping your
        output to a file won't strew escape sequences all over the place. The
        ``ls`` command sets a precedent for this: it defaults to columnar
        output when being sent to a tty and one-item-per-line when not.

        :arg kind: A terminal string as taken by ``setupterm()``. Defaults to
            the value of the ``TERM`` environment variable.
        :arg stream: A file-like object representing the terminal. Defaults to
            the original value of stdout, like ``curses.initscr()`` does.
        """
        self.kind = kind if kind is not None else 'unknown'
        if stream is None:
            stream = sys.__stdout__
        self.stream = stream
        self.rows = rows
        self.columns = columns
        curses.setupterm(kind, stream.fileno())

        # curses capability names are inherited (for comparison)
        for attr in (a for a in dir(curses) if a.startswith('KEY_')):
            setattr(self, attr, getattr(curses, attr))

        #pylint: disable=W0212,E1101
        # Access to a protected member _capability_names of a client class
        # Function 'has_key' has no '_capability_names' member
        self._keymap = dict([(curses.tigetstr(cap).decode('utf-8'), keycode)
                             for (keycode, cap) in
                             curses.has_key._capability_names.iteritems()
                             if curses.tigetstr(cap) is not None])

        # not complete, but pretty close ..
        self._keymap.update([(sequence, key) for (sequence, key) in (
            (curses.tigetstr('khome'), self.KEY_HOME),
            (curses.tigetstr('kend'), self.KEY_END),
            (curses.tigetstr('kcuu1'), self.KEY_UP),
            (curses.tigetstr('kcud1'), self.KEY_DOWN),
            (curses.tigetstr('cuf1'), self.KEY_RIGHT),
            (curses.tigetstr('kcub1'), self.KEY_LEFT),
            (curses.tigetstr('knp'), self.KEY_NPAGE),
            (curses.tigetstr('kpp'), self.KEY_PPAGE),
            (curses.tigetstr('kent'), self.KEY_ENTER),
            (curses.tigetstr('kbs'), self.KEY_BACKSPACE),
            (curses.tigetstr('kdch1'), self.KEY_BACKSPACE))
            if sequence is not None and 0 != len(sequence)])

        # add to this various NVT sequences
        self._keymap.update([
            (unichr(10), self.KEY_ENTER),
            (unichr(13), self.KEY_ENTER),
            (unichr(8), self.KEY_BACKSPACE),
            (unichr(127), self.KEY_BACKSPACE),
            (unichr(27) + u"OA", self.KEY_UP),
            (unichr(27) + u"OB", self.KEY_DOWN),
            (unichr(27) + u"OC", self.KEY_RIGHT),
            (unichr(27) + u"OD", self.KEY_LEFT),
            (unichr(27) + u"[A", self.KEY_UP),
            (unichr(27) + u"[B", self.KEY_DOWN),
            (unichr(27) + u"[C", self.KEY_RIGHT),
            (unichr(27) + u"[D", self.KEY_LEFT),
            (unichr(27) + u"A", self.KEY_UP),
            (unichr(27) + u"B", self.KEY_DOWN),
            (unichr(27) + u"C", self.KEY_RIGHT),
            (unichr(27) + u"D", self.KEY_LEFT),
            (unichr(27) + u"?x", self.KEY_UP),
            (unichr(27) + u"?r", self.KEY_DOWN),
            (unichr(27) + u"?v", self.KEY_RIGHT),
            (unichr(27) + u"?t", self.KEY_LEFT),
            (unichr(27) + u"[H", self.KEY_HOME),
            (unichr(27) + u"[F", self.KEY_END)])

    # Sugary names for commonly-used capabilities, intended to help avoid trips
    # to the terminfo man page and comments in your code:
    _sugar = dict(
        # Don't use "on" or "bright" as an underscore-separated chunk in any of
        # these (e.g. on_cology or rock_on) so we don't interfere with
        # __getattr__.
        save='sc',
        restore='rc',

        clear_eol='el',
        clear_bol='el1',
        clear_eos='ed',
        # 'clear' clears the whole screen.
        position='cup',  # deprecated
        enter_fullscreen='smcup',
        exit_fullscreen='rmcup',
        move='cup',
        move_x='hpa',
        move_y='vpa',
        move_left='cub1',
        move_right='cuf1',
        move_up='cuu1',
        move_down='cud1',

        hide_cursor='civis',
        normal_cursor='cnorm',

        reset_colors='op',  # oc doesn't work on my OS X terminal.

        normal='sgr0',
        reverse='rev',
        # 'bold' is just 'bold'. Similarly...
        # blink
        # dim
        # flash
        italic='sitm',
        no_italic='ritm',
        shadow='sshm',
        no_shadow='rshm',
        standout='smso',
        no_standout='rmso',
        subscript='ssubm',
        no_subscript='rsubm',
        superscript='ssupm',
        no_superscript='rsupm',
        underline='smul',
        no_underline='rmul')

    def __getattr__(self, attr):
        """Return parametrized terminal capabilities, like bold.

        For example, you can say ``term.bold`` to get the string that turns on
        bold formatting and ``term.normal`` to get the string that turns it off
        again. Or you can take a shortcut: ``term.bold('hi')`` bolds its
        argument and sets everything to normal afterward. You can even combine
        things: ``term.bold_underline_red_on_bright_green('yowzers!')``.

        For a parametrized capability like ``cup``, pass the parameters too:
        ``some_term.cup(line, column)``.

        ``man terminfo`` for a complete list of capabilities.

        Return values are always Unicode.

        """
        # Cache capability codes.
        resolution = self._resolve_formatter(attr)
        setattr(self, attr, resolution)
        return resolution

    def keyname(self, keycode):
        """
        Return any matching keycode name for a given keycode.
        """
        for key in (attr for attr in dir(self)
                    if attr.startswith('KEY_')
                    and keycode == getattr(self, attr)):
            return key
        return str(None)

    @property
    def height(self):
        """The height of the terminal in characters
        """
        return self._height_and_width()[0]

    @property
    def width(self):
        """The width of the terminal in characters

        See ``height()`` for some corner cases.

        """
        return self._height_and_width()[1]

    def _height_and_width(self):
        """Return a tuple of (terminal height, terminal width)."""
        if self.stream == sys.__stdout__:
            try:
                return struct.unpack(
                    'hhhh', fcntl.ioctl(sys.__stdout__, termios.TIOCGWINSZ,
                                        chr(0) * 8))[0:2]
            except IOError:
                pass
        return (self.rows, self.columns)

    @contextlib.contextmanager
    def location(self, xloc=None, yloc=None):
        """Return a context manager for temporarily moving the cursor.

        Move the cursor to a certain position on entry, let you print stuff
        there, then return the cursor to its original position::

            term = Terminal()
            with term.location(2, 5):
                print 'Hello, world!'
                for x in xrange(10):
                    print 'I can do it %i times!' % x

        Specify ``x`` to move to a certain column, ``y`` to move to a certain
        row, both, or neither. If you specify neither, only the saving and
        restoration of cursor position will happen. This can be useful if you
        simply want to restore your place after doing some manual cursor
        movement.

        """
        # Save position and move to the requested column, row, or both:
        self.stream.write(self.save)
        if xloc is not None and yloc is not None:
            self.stream.write(self.move(yloc, xloc))
        elif xloc is not None:
            self.stream.write(self.move_x(xloc))
        elif yloc is not None:
            self.stream.write(self.move_y(yloc))
        yield

        # Restore original cursor position:
        self.stream.write(self.restore)

    @contextlib.contextmanager
    def fullscreen(self):
        """
        Return a context manager that enters fullscreen mode while inside it
        and restores normal mode on leaving.
        """
        self.stream.write(self.enter_fullscreen)
        yield
        self.stream.write(self.exit_fullscreen)

    @contextlib.contextmanager
    def hidden_cursor(self):
        """
        Return a context manager that hides the cursor while inside it and
        makes it visible on leaving.
        """
        self.stream.write(self.hide_cursor)
        yield
        self.stream.write(self.normal_cursor)

    @property
    def color(self):
        """Return a capability that sets the foreground color.

        The capability is unparametrized until called and passed a number
        (0-15), at which point it returns another string which represents a
        specific color change. This second string can further be called to
        color a piece of text and set everything back to normal afterward.

        :arg num: The number, 0-15, of the color

        """
        return ParametrizingString(self._foreground_color, self.normal)

    @property
    def on_color(self):
        """Return a capability that sets the background color.

        See ``color()``.

        """
        return ParametrizingString(self._background_color, self.normal)

    @property
    def number_of_colors(self):
        """Return the number of colors the terminal supports.

        Common values are 0, 8, 16, 88, and 256.

        Though the underlying capability returns -1 when there is no color
        support, we return 0. This lets you test more Pythonically::

            if term.number_of_colors:
                ...

        We also return 0 if the terminal won't tell us how many colors it
        supports, which I think is rare.
        """
        #pylint: disable=R0201
        #        Method could be a function
        # This is actually the only remotely useful numeric capability. We
        # don't name it after the underlying capability, because we deviate
        # slightly from its behavior, and we might someday wish to give direct
        # access to it.
        colors = curses.tigetnum('colors')
        # Returns -1 if no color support, -2 if no such cap.
        return colors if colors >= 0 else 0

    def _resolve_formatter(self, attr):
        """
        Resolve a sugary or plain capability name, color, or compound
        formatting function name into a callable capability.
        """
        if attr in COLORS:
            return self._resolve_color(attr)
        elif attr in COMPOUNDABLES:
            # Bold, underline, or something that takes no parameters
            return self._formatting_string(self._resolve_capability(attr))
        else:
            formatters = split_into_formatters(attr)
            if all(f in COMPOUNDABLES for f in formatters):
                # It's a compound formatter, like "bold_green_on_red". Future
                # optimization: combine all formatting into a single escape
                # sequence.
                return self._formatting_string(
                    u''.join(self._resolve_formatter(s) for s in formatters))
            else:
                return ParametrizingString(self._resolve_capability(attr))

    def _resolve_capability(self, atom):
        """
        Return a terminal code for a capname or a sugary name, or an empty
        Unicode.

        The return value is always Unicode, because otherwise it is clumsy
        (especially in Python 3) to concatenate with real (Unicode) strings.

        """
        code = curses.tigetstr(self._sugar.get(atom, atom))
        if code:
            # We can encode escape sequences as UTF-8 because they never
            # contain chars > 127, and UTF-8 never changes anything within that
            # range..
            return code.decode('utf-8')
        return u''

    def trans_input(self, data, encoding='utf8'):
        """
        Yield either a unicode byte or a curses key constant as integer.
        If data is a bytestring, it is converted to unicode using encoding.
        """
        logger = logging.getLogger()
        if isinstance(data, str):
            logger.debug('decode: %r', data)
            data = data.decode(encoding, 'replace')
        logger.debug('decoded: %r', data)

        def scan_keymap(text):
            """
            Return sequence and keycode if text begins with any known sequence.
            """
            for (keyseq, keycode) in self._keymap.iteritems():
                if text.startswith(keyseq):
                    return (keyseq, keycode)
            return (None, None)  # no match

        while len(data):
            if ('\r', '\x00') == (data[0],
                                  data[1] if 1 != len(data) else None):
                # skip beyond nul (nvt telnet)
                yield self.KEY_ENTER
                data = data[2:]
                continue
            if ('\r', '\n') == (data[0], data[1] if 1 != len(data) else None):
                # skip beyond \n (putty, SyncTerm)
                yield self.KEY_ENTER
                data = data[2:]
                continue
            keyseq, keycode = scan_keymap(data)
            # keymap KEY_ sequence
            if (keyseq, keycode) != (None, None):
                yield keycode
                data = data[len(keyseq):]
            else:
                yield data[0]
                data = data[1:]

    def _resolve_color(self, color):
        """
        Resolve a color like red or on_bright_green into a callable capability.
        """
        color_cap = (self._background_color if 'on_' in color else
                     self._foreground_color)
        # curses constants go up to only 7, so add an offset to get at the
        # bright colors at 8-15:
        offset = 8 if 'bright_' in color else 0
        base_color = color.rsplit('_', 1)[-1]
        return self._formatting_string(
            color_cap(getattr(curses, 'COLOR_' + base_color.upper()) + offset))

    @property
    def _foreground_color(self):
        """ Return ANSI or non-ANSI foreground attribute."""
        return self.setaf or self.setf

    @property
    def _background_color(self):
        """ Return ANSI or non-ANSI background attribute."""
        return self.setab or self.setb

    def _formatting_string(self, formatting):
        """
        Return a new ``FormattingString`` which implicitly receives my notion
        of "normal".
        """
        return FormattingString(formatting, self.normal)


def derivative_colors(colors):
    """Return the names of valid color variants, given the base colors."""
    return set([('on_' + c) for c in colors] +
               [('bright_' + c) for c in colors] +
               [('on_bright_' + c) for c in colors])


COLORS = set(['black', 'red', 'green', 'yellow', 'blue',
              'magenta', 'cyan', 'white'])
COLORS.update(derivative_colors(COLORS))
COMPOUNDABLES = (COLORS |
                 set(['bold', 'underline', 'reverse', 'blink', 'dim', 'italic',
                      'shadow', 'standout', 'subscript', 'superscript']))


class ParametrizingString(unicode):
    """
    A Unicode string which can be called to parametrize it as a terminal
    capability.
    """
    #pylint: disable=R0904,R0924
    #        Too many public methods (40/20)
    #        Badly implemented Container, implements __getitem__, __len__
    #          but not __delitem__, __setitem__
    def __new__(cls, formatting, normal=None):
        """Instantiate.

        :arg normal: If non-None, indicates that, once parametrized, this can
            be used as a ``FormattingString``. The value is used as the
            "normal" capability.

        """
        #pylint: disable=W0212
        #        Access to a protected member _normal of a client class
        new = unicode.__new__(cls, formatting)
        new._normal = normal
        return new

    def __call__(self, *args):
        try:
            # Re-encode the cap, because tparm() takes a bytestring in Python
            # 3. However, appear to be a plain Unicode string otherwise so
            # concats work.
            lookup = self.encode('utf-8')
            parametrized = curses.tparm(lookup, *args).decode('utf-8')
            return (parametrized if self._normal is None else
                    FormattingString(parametrized, self._normal))
        except curses.error:
            # Catch "must call (at least) setupterm() first" errors, as when
            # running simply `nosetests` (without progressive) on nose-
            # progressive. Perhaps the terminal has gone away between calling
            # tigetstr and calling tparm.
            return u''
        except TypeError:
            # If the first non-int (i.e. incorrect) arg was a string, suggest
            # something intelligent:
            if len(args) == 1 and isinstance(args[0], basestring):
                raise TypeError(
                    'A native or nonexistent capability template received '
                    '%r when it was expecting ints. You probably misspelled a '
                    'formatting call like bright_red_on_white(...).' % args)
            else:
                # Somebody passed a non-string; I don't feel confident
                # guessing what they were trying to do.
                raise


class FormattingString(unicode):
    """
    A Unicode string which can be called upon a piece of text to wrap it in
    formatting.
    """
    #pylint: disable=R0904,R0924
    #        Too many public methods (40/20)
    #        Badly implemented Container, implements __getitem__, __len__
    #          but not __delitem__, __setitem__

    def __new__(cls, formatting, normal):
        #pylint: disable=W0212
        #        Access to a protected member _normal of a client class
        new = unicode.__new__(cls, formatting)
        new._normal = normal
        return new

    def __call__(self, text):
        """Return a new string that is ``text`` formatted with my contents.

        At the beginning of the string, I prepend the formatting that is my
        contents. At the end, I append the "normal" sequence to set everything
        back to defaults. The return value is always a Unicode.

        """
        return self + text + self._normal


class NullCallableString(unicode):
    """
    A dummy class to stand in for ``FormattingString`` and
    ``ParametrizingString``.

    A callable bytestring that returns an empty Unicode when called with an int
    and the arg otherwise. We use this when there is no tty and so all
    capabilities are blank.

    """
    #pylint: disable=R0904,R0924
    #        Too many public methods (40/20)
    #        Badly implemented Container, implements __getitem__, __len__
    #          but not __delitem__, __setitem__

    def __new__(cls):
        new = unicode.__new__(cls, u'')
        return new

    def __call__(self, arg):
        if isinstance(arg, int):
            return u''
        return arg


def split_into_formatters(compound):
    """Split a possibly compound format string into segments.

    >>> split_into_formatters('bold_underline_bright_blue_on_red')
    ['bold', 'underline', 'bright_blue', 'on_red']

    """
    merged_segs = []
    # These occur only as prefixes, so they can always be merged:
    mergeable_prefixes = ['on', 'bright', 'on_bright']
    for spx in compound.split('_'):
        if merged_segs and merged_segs[-1] in mergeable_prefixes:
            merged_segs[-1] += '_' + spx
        else:
            merged_segs.append(spx)
    return merged_segs
