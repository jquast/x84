#import multiprocessing
import traceback
import itertools
import logging
import struct
import math
import time
import sys
import os
import io
import re

import ini
import exception
import scripting

logger = logging.getLogger()
mySession = None

def getsession():
    """Return session, after a .run() method has been called on any 1 instance.
    """
    assert mySession is not None, \
        'a Session() instance must be initialized with .run() method'
    return mySession

class Session(object):
    """
    _script_stack is a list of script modules for tracking active script location
    during consecutive gosub() calls. When this script is exausted, the session
    ends. On instantiation, the value is set to the 'script' option of subsection
    'matrix' in the settings ini file. When run() is called, _script_stack begins
    execution.

    _buffer is a dict keyed by event names, containing lists of data buffered
    from the IPC pipe of the parrent process during calls to read_event() that
    were not immediately yielded. _buffer['input'] contains keypresses. a call to
    flush_event() discards all data waiting for an event. a call to read_event()
    returns a any any data waiting on the event queue within the specified
    timeout. if data is recieved on the IPC pipe that is not requested, it is
    buffered to _buffer.

    _source is a tuple that indicates the origin of the terminal in some form,
    such as (client.addr, client.port) for telnet connections.

    _tap_input represents a boolean of wether or not, when debug logging is
    enabled, to display user input.
    """
    _user = None
    _handle = None
    _activity = None
    _cwd = None
    _encoding = 'utf8'
    _record_tty = False
    _ttyrec_folder = 'ttyrecordings/'
    _fp_ttyrec = None
    _ttyrec_sec = -1
    _ttyrec_usec = -1
    _ttyrec_len_text = 0
    _last_input_time = 0.0
    _connect_time = 0.0
    _enable_keycodes = True
    _tap_mask = '*'
    # if the last timechunk and current timechunk to be written differ by less
    # than TTYREC_uCOMPRESS (microseconds), modify the last written timechunk
    # to include the current data as though no time had passed at all. in
    # theory this would lose timing precision, but it actually gains precision
    # at times by removing unnecessarily acruate timings that cause the playback
    # to become slower than it intended!
    TTYREC_uCOMPRESS = 1500
    # http://www.xfree86.org/current/ctlseqs.html#VT100%20Mode
    # CSI(8);(Y);(X)t #  -- resize the text area to
    #                       [height;width] in characters.
    TTYREC_HEADER = u'\033[8;%d;%dt'

    def __init__ (self, terminal=None, pipe=None, source=('undef', None), env=None):
        self.pipe = pipe
        self.terminal = terminal
        self.env = dict(('TERM', terminal.kind),) if env is None else env
        self._script_stack = [(ini.cfg.get('matrix','script'),)]
        self._script_stack = list(((ini.cfg.get('matrix','script'),),))
        self._tap_input = ini.cfg.get('session','tap_input', 'no') in ('yes', 'on')
        self._tap_output = ini.cfg.get('session','tap_output', 'no') in ('yes', 'on')
        self._ttylog_folder = ini.cfg.get('session', 'ttylog_folder')
        self._record_tty = ini.cfg.get('session', 'record_tty', 'yes') in ('yes','on')
        self._ttyrec_folder = ini.cfg.get('session', 'ttylog_folder')
        self._buffer = dict()
        self._source = source
        self._last_input_time = self._connect_time = time.time()

    @property
    def duration(self):
        """Return length of time since connection began (float)."""
        return time.time() -self._connect_time

    @property
    def connect_time(self):
        """Return time when connection began (float)."""
        return self._connect_time

    @property
    def last_input_time(self):
        """Return last time of keypress (epoch float)."""
        return self._last_input_time

    @property
    def idle(self):
        """Return length of time since last keypress occured (float)."""
        return time.time() - self._last_input_time


    @property
    def activity(self):
        """Current activity (arbitrarily set)."""
        return self._activity

    @activity.setter
    def activity(self, value):
        if self._activity != value:
            logger.debug ('%s activity=%s', self.handle, value)
            self._activity = value


    @property
    def handle(self):
        """User handle."""
        return self._handle

    @handle.setter
    def handle(self, value):
        # _handle only set by @user.setter
        raise TypeError, 'handle property read-only'


    @property
    def user(self):
        """User record object."""
        return self._user

    @user.setter
    def user(self, value):
        import userbase
        assert isinstance(value, userbase.User)
        logger.info ('user=%s', value.handle)
        self._user = value
        if value.handle != self._handle:
            if self.is_recording():
                # mv None.0 -> userName.0
                self.rename_recording (self.handle, value.handle)
            # set new handle
            self._handle = value.handle


    @property
    def origin(self):
        """A string describing the source of this connection."""
        return '%r' % (self.souce,)

    @property
    def source(self):
        """A tuple describing the session source, usually in
           the form of (sock.addr, sock.port,). """
        return self._source

    @source.setter
    def source(self, value):
        assert type(value) is tuple
        self._source = value


    @property
    def cwd(self):
        """Current working directory."""
        return (os.path.realpath(self._cwd) + os.path.sep
                if self._cwd is not None
                else os.path.curdur + os.path.sep)

    @cwd.setter
    def cwd(self, value):
        if self._cwd != value:
            logger.debug ('%s cwd=%s', self.handle, value)
            self._cwd = value


    @property
    def encoding(self):
        """Input and Output encoding."""
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        if value != self._encoding:
            logger.info ('%s encoding=%s', self.handle, value)
            self._encoding = value


    @property
    def enable_keycodes(self):
        """
        Should multibyte sequences be translated to keycodes for 'input' events?
        It may be desirable to disable this when doing pass-through, to a door, f.e.,
        """
        return self._enable_keycodes

    @enable_keycodes.setter
    def enable_keycodes(self, value):
        if value != self._enable_keycodes:
            logger.debug ('%s enable_keycodes=%s', self.handle, value)
            self._enable_keycodes = value


    @property
    def pid(self):
        """Process ID."""
        return os.getpid()


    def run(self):
        """
          The main script execution loop for a session handles the
          movement of the client users throughout userland via calls to
          runscript(). The client scripts, however, make use goto()
          which causes the ScriptChange exception to be raised and handled
          here, or by bypassing us through a gosub() function which too
          calls runscript(), via engine.getsession().runscript()
        """
        import copy
        global mySession
        assert mySession is None, 'run() cannot be called twice'
        mySession = self
        fallback_stack = self._script_stack
        self.cwd = ini.cfg.get('session', 'scriptpath')
        while len(self._script_stack) > 0:
            logger.debug ('%s: script_stack is %s',
                self.handle, self._script_stack)
            try:
                lastscript = self._script_stack[-1]
                value = self.runscript (*self._script_stack.pop())
                if not self._script_stack:
                    logger.error ('_script_stack = <fallback_stack: %r>', \
                        fallback_stack)
                    self._script_stack = fallback_stack
                    continue
            except exception.Goto, e:
                logger.debug ('Goto: %s' % (e,))
                self._script_stack = [e[0] + tuple(e[1:])]
                continue
            except exception.Disconnect, e:
                logger.info ('User disconnected: %s' % (e,))
                return
            except exception.ConnectionClosed, e:
                logger.info ('Connection Closed: %s' % (e,))
                return
            except exception.ConnectionTimeout, e:
                logger.info ('Connection Timed out: %s' % (e,))
                return
            except exception.ScriptError, e:
                logger.error ("ScriptError rasied: %s", e)
            except Exception, e:
                # Pokemon exception. question: can this python code
                # be made to look like an ascii poke-ball?
                t, v, tb= sys.exc_info()
                map (logger.error, (l.rstrip() \
                    for l in itertools.chain \
                      (traceback.format_tb(tb), \
                       (fe for fe in traceback.format_exception_only(t, v)))))
            if 0 != len(self._script_stack):
                # recover from a general exception or script error
                fault = self._script_stack.pop()
                logger.info ('%s after general exception with %s.', 'Resume' \
                    if 0 != len(self._script_stack) else 'Stop', fault)


    def write (self, data):
        """ Write unicode data through multiprocessing.Pipe() as
            unicode data, unless self.encoding is 'cp437'.

            We might as well name this variable 'PC-DOS' or 'SyncTerm'.

            We pretend to provide our parent terminal utf-8 data,
            but this is where the slippery cp437-undoing trick is
            done. We send utf-8, but its really intended for syncterm,
            and will not contain any unicode that would become multibyte
        """
        if 0 == len(data):
            return # warning: a terminal incapability such as .move(0,0)
                   # became an empty string.
        assert isinstance(data, unicode)
        if self.encoding == 'cp437':
            from bbs.cp437 import CP437
            # first, encode as iso8859-1, this will replace a lot
            # of characters, including artwork, as '?'
            text = data.encode('iso8859-1', 'replace')
            # then, iterate over all the unicode glyphs, mapping
            # back to their bytestring equivalents unless there isn't
            # a mapping, then use that position in text ('?').
            data = u''.join([unichr(CP437.index(glyph)) \
                if glyph in CP437 else unicode(text[n]) \
                for n, glyph in enumerate(data)])
        self.terminal.stream.write (data, is_cp437=(self.encoding == 'cp437'))

        if False == self._record_tty:
            return
        if not self.is_recording():
            self.start_recording ()
        self._ttyrec_write (data)
        if self._tap_output and logger.isEnabledFor(logging.DEBUG):
            logger.debug ('%s --> %r.', self.handle, data)

    def flush_event (self, event, timeout=-1):
        """Flush all data buffered for 'event'."""
        data = 1
        while (None, None) != (event, data):
            event, data = self.read_event([event], timeout=timeout)


    def _event_pop(self, event):
        """Return first-most item buffered for event (FIFO)."""
        store = self._buffer[event].pop ()
        return store


    def _buffer_event (self, event, data):
        """
           Push data into FIFO buffer keyed by event.  If event is a string named
           'input', translate data as bytestrings into items yielded from generator
           self.terminal.trans_input().
        """
        if event == 'ConnectionClosed':
            raise exception.ConnectionClosed (data)

        if not self._buffer.has_key(event):
            # create new buffer;
            self._buffer[event] = list()

        if event == 'input':
            self._buffer_input (data)
        elif event == 'refresh':
            if data[0] == 'resize':
                # inherit terminal dimensions values
                (self.terminal.columns, self.terminal.rows) = data[1]
            # store only most recent 'refresh' event
            self._buffer[event] = list((data,))
        else:
            self._buffer[event].insert (0, data)
            # XXX very large for database queries, lol..
            logger.debug ('%s event buffered, (%s,%s).', self.handle, event, data,)

    def _buffer_input (self, data):
        """
          Given multibyte keysequences, either pass into 'input' event
          buffer unmanipulated when self.enable_keycodes is True, otherwise
          decode as possible nvt, vt100, telnet, and curses input keysequences.

          The unfortunate side-effect is something might appear as an equivalent
          KEY_SEQUENCE that is better described as it was, '\r' and '\b', for
          example.
        """
        self._last_input_time = time.time()

        if self._tap_input and logger.isEnabledFor(logging.DEBUG):
            logger.debug ('%s <-- %r.', self.handle, data)
        if False == self.enable_keycodes:
            # send keyboard bytes in as-is, unmanipulated
            self._buffer['input'].insert (0, data)
            return
        # translate ^L to KEY_REFRESH in getch() stream, but
        # also send a ('refresh', ('input',)) event for signaling
        ctrl_l = list((('input', self.terminal.KEY_REFRESH),))
        # perform keycode translation voodoo with modified blessings/curses
        for keystroke in self.terminal.trans_input(data, self.encoding):
            if keystroke == chr(12): # ^L
                self._buffer['refresh'] = ctrl_l
                self._buffer['input'].insert (0, self.terminal.KEY_REFRESH)
            # place unicode into buffer, suprise, sometimes its an integer,
            # which is equivalent to a curses.KEY_SOMETHING, othertimes
            # its just unicode. TODO: something more duck type-ish
            self._buffer['input'].insert (0, keystroke)

    def send_event (self, event, data):
        """
           Send data to IPC pipe in form of (event, data).
           engine.py of the main process translates the following events into
           actions: 'output', send data to socket; 'global', duplicate data to all
           other IPC processes; and 'db-<schema>', a IPC database communication
           pipe used by dbproxy.py
        """
        self.pipe.send ((event, data))

    def read_event (self, events, timeout=None):
        """
           Poll for and return any buffered IPC data for events that have arrived
           in the form of (event, data). Always available is the 'input' event for
           keyboard input. A timeout of None waits indefinitely, otherwise
           (None, None) is returned when timeout has exceeded. when timeout of -1
           is used, this call is non-blocking.
        """
        (event, data) = (None, None)

        # return immediately any events that are already buffered
        for (event, data) in ((e, self._event_pop(e)) for e in events \
            if e in self._buffer and 0 != len(self._buffer[e])):
            return (event, data)

        t = time.time()
        timeleft = lambda t: \
            float('inf') if timeout is None \
            else timeout - (time.time() -t)
        waitfor = timeleft(t)
        while waitfor > 0:
            if self.pipe.poll (None if waitfor == float('inf') else waitfor):
                event, data = self.pipe.recv()
                if event == 'exception':
                    (t, v, tb) = data
                    map (logger.error, (l.rstrip() for l in tb))
                    logger.error ('local traceback follows')
                    raise t, v
                self._buffer_event (event, data)
                if event in events:
                    return (event, self._event_pop(event))
                else:
                    logger.debug ('not seeking event %s; pass.', (event,))
            # poll()
            if timeout == -1:
                return (None, None)
            waitfor = timeleft(t)
        return (None, None)


    def runscript(self, script, *args):
        """Execute script's .main() callable with optional *args."""
        import bbs
        self._script_stack.append ((script,) + args)
        logger.info ('%s runscript %s, %s.', self.handle, script, args,)
        try:
            self.script_name, self.script_filepath \
                = scripting.chkmodpath (script, self.cwd)
        except LookupError, e:
            raise exception.ScriptError, e

        current_path = os.path.dirname(self.script_filepath)
        if not current_path in sys.path:
            sys.path.insert (0, current_path)
            logger.debug ('%s inserted to sys.path: %s',
                    self.handle, current_path)

        logger.debug ('scripting.load(%s, %s)', self.cwd, self.script_name,)
        script = scripting.load(self.cwd, self.script_name)
        for idx in bbs.__all__:
            try:
                setattr(script, idx, getattr(bbs, idx))
            except AttributeError, err:
                logger.error (err)
        if not hasattr(script, 'main'):
            raise exception.ScriptError ("%s: main() not found." %
                    (self.script_name,))
        if not callable(script.main):
            raise exception.ScriptError ("%s: main not callable." %
                    (self.script_name,))
        prev_path = self.cwd \
            if self.cwd is not None else current_path
        self.cwd = current_path
        value = script.main(*args)
        self.cwd = prev_path

        # we were gosub()'d here and have returned value.
        toss = self._script_stack.pop()
        logger.debug ('%s popped from script_stack, return value=%s', toss, value)
        return value

    def close(self):
        if self.is_recording():
            self.stop_recording()

    def rename_recording(self, src, dst):
        """Rename rotate dst and rename src.0 to dst.0."""
        self.rotate_recordings (dst)
        os.rename (os.path.join(self._ttylog_folder, '%s.0'%(src,)),
            os.path.join(self._ttylog_folder, '%s.0'%(dst,)))

    def rotate_recordings(self, key):
        """Rotate any existing recordings for key."""
        pattern = re.compile('%s.\d.ttyrec' % (key,))
        # if .8 exists, move .8 to .9, obliterating .9
        # if .7 (...)
        for n in range(9):
            src = os.path.join(self._ttylog_folder, '%s.%d' % (key, 8-(n)))
            dst = os.path.join(self._ttylog_folder, '%s.%d' % (key, 8-(n -1)))
            if os.path.exists(src):
                os.rename (src, dst)
        dst = os.path.join(self._ttylog_folder, '%s.0' % (key,))
        assert not os.path.exists(dst), dst # very rare race condition without locking

    def is_recording(self):
        return self._fp_ttyrec is not None

    def stop_recording(self):
        assert self.is_recording()
        self._fp_ttyrec.close ()
        self._fp_ttyrec = None

    def start_recording(self, dst=None):
        """Begin recording to ttyrec file in recordings folder, keyed by dst."""
        assert self._fp_ttyrec is None
        dst = dst if dst is not None else '%s' % (self.handle,)

        # XXX global lock.acquire ('ttyrecordings')
        # rotate existing logfiles
        self.rotate_recordings (dst)

        # open ttyrec logfile
        filename = os.path.join(self._ttyrec_folder, '%s.0' % (dst,))
        if not os.path.exists(self._ttyrec_folder):
            logger.info('creating ttyrec folder, %s.', self._ttyrec_folder)
            os.makedirs (self._ttyrec_folder)

        self._fp_ttyrec = io.open(filename, 'wb+')
        # XXX global lock.release ('ttyrecordings')
        self._ttyrec_sec = -1
        self._recording = True

        # write header
        logger.info ('REC %s' % (filename,))
        (h, w) = self.terminal.height, self.terminal.width
        self._ttyrec_write (self.TTYREC_HEADER % (h, w,))

        # http://www.cl.cam.ac.uk/~mgk25/unicode.html#term
        # ESC %G activates UTF-8 with an unspecified implementation level from
        # ISO 2022 in a way that allows to go back to ISO 2022 again.
        #
        # ESC %@ goes back from UTF-8 to ISO 2022 in case UTF-8 had been entered
        # via ESC %G.
        #
        # ESC ) K or ESC ) U Sets character set G1 to codepage 437,
        # for example, classic linux vga console)
        self._ttyrec_write (u'\033%G')

    def _ttyrec_write(self, data):
        """ Is big brother watching you? """
        # write bytestring to ttyrec file packed as timed byte.
        # If the current timed byte is within 1,000us:
        #   rewind stream and re-write the 'length' portion,
        #   and append data to end of stream.
        # side-effects:
        #   self._ttyrec_sec, self._ttyrec_usec, self._ttyrec_len_data
        assert self._recording
        assert isinstance(data, unicode)
        text = data.encode('utf8')
        timeKey = self.duration

        # round down timeKey to nearest whole number,
        # use the remainder for microseconds, upconvert,
        # constructing a (seconds, microseconds) pair.
        sec = math.floor(timeKey)
        usec = (timeKey -sec) * 1e+6
        sec, usec = int(sec), int(usec)
        len_text = len(text)

        if sec != self._ttyrec_sec \
        or usec - self._ttyrec_usec > self.TTYREC_uCOMPRESS:
            # create new timechunk record:
            #  bytes (sec, usec, len(text), text.. )
            bp1 = struct.pack('<I', sec) \
                + struct.pack('<I', usec)
            bp2 = struct.pack('<I', len_text)
            # write
            self._fp_ttyrec.write (bp1 + bp2 + text)
            self._ttyrec_sec = sec
            self._ttyrec_usec = usec
            self._ttyrec_len_text = len_text
            self._fp_ttyrec.flush ()
            return

        # rewind to last length byte
        last_bp2 = struct.pack('<I', self._ttyrec_len_text)
        new_bp2 = struct.pack('<I', self._ttyrec_len_text +len_text)
        self._fp_ttyrec.seek ((self._ttyrec_len_text +len(last_bp2)) *-1, 2)

        # re-write length byte
        self._fp_ttyrec.write (new_bp2)

        # append after existing chunk record
        self._fp_ttyrec.seek (self._ttyrec_len_text, 1)
        self._fp_ttyrec.write (text)
        self._ttyrec_len_text = self._ttyrec_len_text + len_text
        self._fp_ttyrec.flush ()
        """ Yes. """

class IPCLogHandler(logging.Handler):
    """
    Log handler that sends the log up the 'event pipe' :-)
    """
    def __init__(self, pipe):
        logging.Handler.__init__(self)
        self.pipe = pipe
    def emit(self, record):
        """
        emit log record via IPC pipe
        """
        try:
            e_inf = record.exc_info
            if e_inf:
                # side-effect: sets record.exc_text
                dummy = self.format(record)
                record.exc_info = None
            self.pipe.send (('logger', record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError (record)

