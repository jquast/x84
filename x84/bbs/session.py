# -*- coding: utf-8 -*-
"""
Session engine for x/84, http://github.com/jquast/x84/
"""
import traceback
import logging
import inspect
import struct
import math
import time
import imp
import sys
import os
import io

SESSION = None

def getsession():
    """
    Return session, after a .run() method has been called on any 1 instance.
    """
    return SESSION


def getterminal():
    """
    Return blessings terminal instance of this session.
    """
    return getsession().terminal

def getnode():
    """
    Returns unique session identifier for this session as integer.
    """
    return getsession().node

class Session(object):
    """
    A BBS Session engine. Workflow begins in the ``run()`` method.
    """
    # pylint: disable=R0902,R0904,R0913
    #        Too many instance attributes
    #        Too many public methods
    #        Too many arguments
    TRIM_CP437 = bytes(chr(14) + chr(15)) # HACK
    _encoding = None
    _decoder = None

    def __init__(self, terminal, inp_queue, out_queue,
                 sid, env, lock, encoding='utf8'):
        """
        Instantiate a Session instanance, only one session
        may be instantiated per process. Arguments:
            terminal: blessings.Terminal,
            inp_queue: multiprocessing.Queue Parent writes, Child reads
            out_queue: multiprocessing.Queue Parent reads, Child writes
            sid: session id by engine: origin of telnet connection (ip:port),
            env: dict of environment variables, such as 'TERM', 'USER'.
        """
        from x84.bbs import ini
        # pylint: disable=W0603
        #        Using the global statement
        global SESSION
        assert SESSION is None, 'Session may be instantiated only once'
        SESSION = self
        self.iqueue = inp_queue
        self.oqueue = out_queue
        self.terminal = terminal
        self.sid = sid
        self.env = env
        self.encoding = encoding
        self.lock = lock
        self._user = None
        self._script_stack = [(ini.CFG.get('matrix', 'script'),)]
        self._tap_input = ini.CFG.getboolean('session', 'tap_input')
        self._tap_output = ini.CFG.getboolean('session', 'tap_output')
        self._tap_events = ini.CFG.getboolean('session', 'tap_events')
        self._ttyrec_folder = ini.CFG.get('system', 'ttyrecpath')
        self._record_tty = ini.CFG.getboolean('session', 'record_tty')
        self._show_traceback = ini.CFG.getboolean('system', 'show_traceback')
        self._script_path = ini.CFG.get('system', 'scriptpath')
        self._script_module = None
        self._fp_ttyrec = None
        self._ttyrec_fname = None
        self._node = None
        self._connect_time = time.time()
        self._last_input_time = time.time()
        self._activity = u'<uninitialized>'
        # event buffer
        self._buffer = dict()
        # save state for ttyrec compression
        self._ttyrec_sec = -1
        self._ttyrec_usec = -1
        self._ttyrec_len_text = 0

    @property
    def duration(self):
        """
        Return length of time since connection began (float).
        """
        return time.time() - self._connect_time

    @property
    def connect_time(self):
        """
        Return time when connection began (float).
        """
        return self._connect_time

    @property
    def last_input_time(self):
        """
        Return last time of keypress (epoch float).
        """
        return self._last_input_time

    @property
    def idle(self):
        """
        Return length of time since last keypress occured (float).
        """
        return time.time() - self._last_input_time

    @property
    def activity(self):
        """
        Current activity (arbitrarily set). This also updates xterm titles,
        and is globally broadcasted as a "current activity" in the Who's
        online script.
        """
        return self._activity

    @activity.setter
    def activity(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        if self._activity != value:
            logger = logging.getLogger()
            logger.debug('activity=%s', value)
            kind = self.env.get('TERM', 'unknown')
            set_title = self.user.get('set-title', (
                'xterm' in kind or 'rxvt' in kind
                or '_xtitle' in self.env))
            self._activity = value
            if set_title:
                self.write(u''.join((
                    unichr(27), u']2;%s' % (value,), unichr(7))))

    @property
    def handle(self):
        """
        Returns User handle.
        """
        return self.user.handle

    @property
    def user(self):
        """
        User record of session.
        """
        from x84.bbs.userbase import User
        if self._user is not None:
            return self._user
        return User()

    @user.setter
    def user(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self._user = value
        logger = logging.getLogger()
        logger.info("set user '%s'.", value.handle)

    @property
    def encoding(self):
        """
        Session terminal encoding; only 'utf8' and 'cp437' are supported.
        """
        return self._encoding

    @encoding.setter
    def encoding(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        if value != self._encoding:
            logger = logging.getLogger()
            logger.info('encoding is %s.', value)
            assert value in ('utf8', 'cp437')
            self._encoding = value
            getterminal().set_keyboard_decoder(self._encoding)

    @property
    def pid(self):
        """
        Returns Process ID.
        """
        # pylint: disable=R0201
        #        Method could be a function
        return os.getpid()

    @property
    def node(self):
        """
        Returns numeric constant for session, often required by 'doors'
        """
        if self._node is None:
            for node in range(1, 64):
                event = 'lock-%s/%d' % ('node', node)
                self.send_event(event, ('acquire', None))
                data = self.read_event(event)
                if data is True:
                    self._node = node
                    break
        return self._node

    def __error_recovery(self):
        """
        jojo's invention; recover from a general exception by using
        a script stack, and resuming last good script.
        """
        logger = logging.getLogger()
        if 0 != len(self._script_stack):
            # recover from exception
            fault = self._script_stack.pop()
            oper = 'RESUME' if len(self._script_stack) else 'STOP'
            stop = bool(0 == len(self._script_stack))
            msg = (u'%s %safter general exception in %s.' % (
                oper, (
                    (self._script_stack[-1][0] + u' ')
                    if len(self._script_stack) else u' '),
                fault[0],))
            logger.info(msg)
            self.write(u'\r\n\r\n')
            if stop:
                self.write(self.terminal.red_reverse('stop'))
            else:
                self.write(self.terminal.bold_green('continue'))
                self.write(u' ' + self.terminal.bold_cyan(
                    self._script_stack[-1][0]))
            self.write(u' after general exception in %s\r\n' % (
                self.terminal.bold_cyan(fault[0]),))
            # give time for exception to write down queue before
            # continuing or exiting, esp. exiting, otherwise
            # STOP message is not often fully received
            time.sleep(2)

    def run(self):
        """
        Begin main execution flow.

        Scripts manipulate control flow of scripts using goto and gosub.
        """
        from x84.bbs.exception import Goto, Disconnected
        logger = logging.getLogger()
        while len(self._script_stack):
            logger.debug('script_stack: %r', self._script_stack)
            try:
                self.runscript(*self._script_stack.pop())
                continue
            except Goto, err:
                logger.debug('Goto: %s', err)
                self._script_stack = [err[0] + tuple(err[1:])]
                continue
            except Disconnected, err:
                logger.info('Disconnected: %s', err)
                self.close()
                return None
            except Exception, err:
                # Pokemon exception, log and Cc: telnet client, then resume.
                e_type, e_value, e_tb = sys.exc_info()
                if self._show_traceback:
                    self.write(self.terminal.normal + u'\r\n')
                terrs = list()
                for line in traceback.format_tb(e_tb):
                    for subln in line.split('\n'):
                        terrs.append(subln)
                terrs.extend(traceback.format_exception_only(e_type, e_value))
                for etxt in terrs:
                    logger.error(etxt.rstrip())
                    if self._show_traceback:
                        self.write(etxt.rstrip() + u'\r\n')
            self.__error_recovery()
        logger.info('End of script stack.')
        self.close()
        return None

    def write(self, ucs):
        """
        Write unicode data to telnet client. Take special care to encode
        as 'iso8859-1' actually intended for 'cp437'-encoded terminals.

        Has side effect of updating ttyrec file when recording.
        """
        from x84.bbs.cp437 import CP437
        logger = logging.getLogger()
        if 0 == len(ucs):
            return
        assert isinstance(ucs, unicode)
        if self.encoding == 'cp437':
            encoding = 'iso8859-1'
            # out output terminal is cp437, so we need to take special care to
            # re-encode things as "iso8859-1" but really encoded for cp437.
            # For example, u'\u2591' becomes u'\xb0' (unichr(176)),
            # -- the original ansi shaded block for cp437 terminals.
            #
            # additionally, the 'shift-in' and 'shift-out' characters
            # display as '*' on SyncTerm, I think they stem from curses:
            # http://lkml.indiana.edu/hypermail/linux/kernel/0602.2/0868.html
            # regardless, remove them using str.translate()
            text = ucs.encode(encoding, 'replace')
            ucs = u''.join([(unichr(CP437.index(glyph))
                             if glyph in CP437
                             and not glyph in self.TRIM_CP437
                             else unicode(
                                 text[idx].translate(None, self.TRIM_CP437),
                                 encoding, 'replace'))
                            for (idx, glyph) in enumerate(ucs)])
        else:
            encoding = self.encoding
        self.terminal.stream.write(ucs, encoding)

        if self._tap_output and logger.isEnabledFor(logging.DEBUG):
            logger.debug('--> %r.', ucs)

        if self._record_tty:
            if not self.is_recording:
                self.start_recording()
            self._ttyrec_write(ucs)

    def flush_event(self, event):
        """
        Flush all return all data buffered for 'event'.
        """
        logger = logging.getLogger()
        flushed = list()
        while True:
            data = self.read_event(event, -1)
            if data is None:
                if 0 != len(flushed):
                    logger.debug('flushed from %s: %r', event, flushed)
                return flushed
            flushed.append(data)
        return flushed

    def info(self):
        """
        Returns dictionary of key, value pairs of session paramters.
        """
        return dict((
            ('TERM', self.env.get('TERM', u'unknown')),
            ('LINES', self.terminal.height,),
            ('COLUMNS', self.terminal.width,),
            ('sid', self.sid,),
            ('handle', self.user.handle,),
            ('script', (self._script_stack[-1][0]
                        if len(self._script_stack) else None)),
            ('ttyrec',
             self._fp_ttyrec.name if self._fp_ttyrec is not None else u'',),
            ('connect_time', self.connect_time),
            ('idle', self.idle),
            ('activity', self.activity),
            ('encoding', self.encoding),
            ('node', self._node),
        ))

    def buffer_event(self, event, data=None):
        """
        Push data into buffer keyed by event. Handle special events:
            'exception', 'global' AYT (are you there),
            'page', 'info-req', 'refresh', and 'input'.
        """
        logger = logging.getLogger()
        # exceptions aren't buffered; they are thrown!
        if event == 'exception':
            # pylint: disable=E0702
            #        Raising NoneType while only classes, (..) allowed
            raise data

        # respond to global 'AYT' requests
        if event == 'global' and data[0] == 'AYT':
            reply_to = data[1]
            self.send_event('route', (
                reply_to, 'ACK',
                self.sid, self.user.handle,))
            return True

        # accept 'page' as instant chat when 'mesg' is True, or sender is -1
        # -- intent is that sysop can always 'chat' a user ..
        if event == 'page' and self._script_stack[-1:][0][0] != 'chat':
            channel, sender = data
            if self.user.get('mesg', True) or sender == -1:
                logger.info('page from %s.' % (sender,))
                if not self.runscript('chat', channel, sender):
                    logger.info('rejected page from %s.' % (sender,))
                # buffer refresh event for any asyncronous event UI's
                self.buffer_event('refresh', 'page-return')
                return True

        # respond to 'info-req' events by returning pickled session info
        if event == 'info-req':
            sid = data[0]
            self.send_event('route', (sid, 'info-ack', self.sid, self.info(),))
            return True

        # init new unmanaged & unlimited-sized buffer ;p
        if not event in self._buffer:
            self._buffer[event] = list()

        # buffer input
        if event == 'input':
            self.buffer_input(data)
            return

        # buffer only 1 most recent 'refresh' event
        if event == 'refresh':
            if data[0] == 'resize':
                # inherit terminal dimensions values
                (self.terminal.columns, self.terminal.rows) = data[1]
            # store only most recent 'refresh' event
            self._buffer[event] = list((data,))
            return True

        # buffer all else
        self._buffer[event].insert(0, data)

        # global events are meant to be missed if unwanted, so
        # we keep only the 100 most recent.
        if event == 'global' and len(self._buffer[event]) > 150:
            self._buffer[event] = self._buffer[event][:100]

    def buffer_input(self, data):
        """
        Update idle time, buffering raw bytes received from telnet client
        via event queue
        """
        self._last_input_time = time.time()

        logger = logging.getLogger()
        if self._tap_input and logger.isEnabledFor(logging.DEBUG):
            logger.debug('<-- (%d): %r.', len(data), data)

        for keystroke in data:
            self._buffer['input'].insert(0, keystroke)
        return

    def send_event(self, event, data):
        """
           Send data to IPC output queue in form of (event, data).

           Supported events:
               'disconnect': Session wishes to disconnect.
               'logger': Data is logging record, used by IPCLogHandler.
               'output': Unicode data to write to client.
               'global': Broadcast event to other sessions.
               XX 'pos': Request cursor position.
               'db-<schema>': Request sqlite dict method result.
               'db=<schema>': Request sqlite dict method result as iterable.
               'lock-<name>': Fine-grained global bbs locking.
        """
        self.lock.acquire()
        self.oqueue.send((event, data))
        self.lock.release()

    def poll_event(self, event):
        """
        Non-blocking poll for session event, returns value, if any. None
        otherwise.
        """
        return self.read_event(event, -1)

    def read_event(self, event, timeout=None):
        """
        S.read_event (event, timeout=None) --> data

        Read any data for a single event.

        Blocking by default, or non-blocking when timeout is -1. When timeout
        is non-zero, specifies length of time to wait for event before
        returning. If timeout is not None (non-blocking), None is returned if
        no event has is waiting, or waiting after timeout has elapsed.
        """
        return self.read_events(events=(event,), timeout=timeout)[1]

    def read_events(self, events, timeout=None):
        """
           S.read_events (events, timeout=None) --> (event, data)

           Return the first matched IPC data for any event specified in tuple
           events, in the form of (event, data).
        """
        logger = logging.getLogger()
        (event, data) = (None, None)
        # return immediately any events that are already buffered
        for (event, data) in ((e, self._event_pop(e))
                              for e in events if e in self._buffer
                              and 0 != len(self._buffer[e])):
            return (event, data)
        stime = time.time()
        timeleft = lambda cmp_time: (
            float('inf') if timeout is None else
            timeout if timeout < 0 else
            timeout - (time.time() - cmp_time))
        waitfor = timeleft(stime)
        while waitfor > 0:
            poll = None if waitfor == float('inf') else waitfor
            if self.iqueue.poll(poll):
                event, data = self.iqueue.recv()
                retval = self.buffer_event(event, data)
                if (self._tap_events and logger.isEnabledFor(logging.DEBUG)):
                    stack = inspect.stack()
                    caller_mod, caller_func = stack[2][1], stack[2][3]
                    logger.debug('event %s %s by %s in %s.', event,
                                 'caught' if event in events else
                                 'handled' if retval is not None else
                                 'buffered', caller_func, caller_mod,)
                if event in events:
                    return (event, self._event_pop(event))
            elif timeout == -1:
                return (None, None)
            waitfor = timeleft(stime)
        return (None, None)

    def _event_pop(self, event):
        """
        S._event_pop (event) --> data

        Returns foremost item buffered for event. When event is ``input``,
        an artificial pause is used for decoding of MBS when received multipart
        """
        return self._buffer[event].pop()

    def runscript(self, script_name, *args):
        """
        Execute the main() callable of script identified by
        *script_name*, with optional args.
        """
        from x84.bbs.exception import ScriptError
        logger = logging.getLogger()
        self._script_stack.append((script_name,) + args)
        logger.info("run script '%s'%s.", script_name,
                    ', args %r' % (args,) if 0 != len(args) else '')

        def _load_script_module():
            """
            Load and return ini folder, `scriptpath` as a module (cached).
            """
            if self._script_module is None:
                # load default/__init__.py as 'default',
                base_script = os.path.basename(self._script_path)
                lookup = imp.find_module(script_name, [self._script_path])
                # pylint: disable=W0142
                #        Used * or ** magic
                self._script_module = imp.load_module(base_script, *lookup)
                self._script_module.__path__ = self._script_path
            return self._script_module
        # pylint: disable=W0142
        #        Used * or ** magic
        script_module = _load_script_module()
        lookup = imp.find_module(script_name, [script_module.__path__])
        script = imp.load_module(script_name, *lookup)
        if not hasattr(script, 'main'):
            raise ScriptError("%s: main() not found." % (script_name,))
        if not callable(script.main):
            raise ScriptError("%s: main not callable." % (script_name,))
        value = script.main(*args)
        toss = self._script_stack.pop()
        logger.info("script '%s' returned%s.", toss[0],
                    ' %r' % (value,) if value is not None else u'')
        return value

    def close(self):
        """
        Close session.
        """
        if self.is_recording:
            self.stop_recording()
        if self._node is not None:
            self.send_event(
                    event='lock-node/%d' % (self._node),
                    data=('release', None))

    @property
    def is_recording(self):
        """
        True when session is being recorded to ttyrec file
        """
        return self._fp_ttyrec is not None

    def stop_recording(self):
        """
        Cease recording to ttyrec file (close).
        """
        assert self.is_recording
        self._ttyrec_write(u''.join((
            self.terminal.normal, u'\r\n\r\n',
            u'\r\n'.join([u'%s: %s' % (key, val)
            for (key, val) in sorted(self.info().items())]),
            u'\r\n')))
        self._fp_ttyrec.close()
        self._fp_ttyrec = None

    def start_recording(self):
        """
        Begin recording to ttyrec file.
        """
        logger = logging.getLogger()
        assert self._fp_ttyrec is None, ('already recording')
        digit = 0
        while True:
            self._ttyrec_fname = '%s%d-%s.ttyrec' % (
                time.strftime('%Y%m%d.%H%M%S'), digit,
                self.sid.split(':', 1)[0],)
            if not os.path.exists(self._ttyrec_fname):
                break
            digit += 1
        assert os.path.sep not in self._ttyrec_fname
        filename = os.path.join(self._ttyrec_folder, self._ttyrec_fname)
        if not os.path.exists(self._ttyrec_folder):
            logger.info('creating ttyrec folder, %s.', self._ttyrec_folder)
            os.makedirs(self._ttyrec_folder)
        self._fp_ttyrec = io.open(filename, 'wb+')
        self._ttyrec_sec = -1
        self._ttyrec_write_header()
        logger.info('recording %s.' % (filename,))

    def _ttyrec_write_header(self):
        """
        Write ttyrec header that identifies termianl height & width, and escape
        sequence to indicate UTF-8 mode.
        """
        (height, width) = self.terminal.height, self.terminal.width
        self._ttyrec_write(unichr(27) + u'[8;%d;%dt' % (height, width,))
        # ESC %G activates UTF-8 with an unspecified implementation level from
        # ISO 2022 in a way that allows to go back to ISO 2022 again.
        self._ttyrec_write(unichr(27) + u'%G')

    def _ttyrec_write(self, ucs):
        """
        Update ttyrec stream with unicode bytes 'ucs'.
        """
        # write bytestring to ttyrec file packed as timed byte.
        # If the current timed byte is within TTYREC_UCOMPRESS
        # (default: 15,000 μsec), rewind stream and re-write the
        # 'length' portion, and append data to end of stream.
        # .. unfortuantely, this is not compatible with ttyplay -p,
        # so for the time being, it is disabled ..
        assert self._fp_ttyrec is not None, 'call start_recording() first'
        timekey = self.duration

        # Round down timekey to nearest whole number,
        # use the remainder for microseconds. Upconvert,
        # constructing a (seconds, microseconds) pair.
        sec = math.floor(timekey)
        usec = (timekey - sec) * 1e+6
        sec, usec = int(sec), int(usec)

        def write_chunk(tm_sec, tm_usec, textlen, u_text):
            """
            Write new timechunk record,
              bytes (sec, usec, len(text), text.. )
            """
            # build & write,
            bp1 = struct.pack('<I', tm_sec) + struct.pack('<I', tm_usec)
            bp2 = struct.pack('<I', textlen)
            self._fp_ttyrec.write(bp1 + bp2 + u_text)
            # save (time,len) state for compression
            self._ttyrec_sec = tm_sec
            self._ttyrec_usec = tm_usec
            self._ttyrec_len_text = textlen
            self._fp_ttyrec.flush()
        text = ucs.encode('utf8', 'replace')
        len_text = len(text)
        # TODO: padd every 1 or 10 seconds, so 'VCR' type apps
        # can FF/RW easier
        return write_chunk(sec, usec, len_text, text)
