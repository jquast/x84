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
BOTQUEUE = None
BOTLOCK = None


def getsession():
    """
    Return session, after a .run() method has been called on any 1 instance.
    """
    return SESSION


def getterminal():
    """
    Return blessed terminal instance of this session.
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
    TRIM_CP437 = bytes(chr(14) + chr(15))  # HACK
    _encoding = None
    _decoder = None
    _activity = None
    _user = None

    # save state for ttyrec compression
    _ttyrec_sec = -1
    _ttyrec_usec = -1
    _ttyrec_len_text = 0

    _script_module = None
    _fp_ttyrec = None

    #: node number
    _node = None

    def __init__(self, terminal, sid, env, child_pipes, kind, addrport):
        """ Instantiate a Session.

        Only one session may be instantiated per process.

        :param terminal: interactive terminal associated with this session.
        :type terminal: blessed.Terminal.
        :param sid: session identification string
        :type sid: str
        :param env: transport-negotiated environment variables
        :type env: dict
        :param child_pipes: tuple of (writer, reader)
        :type child_pipes: tuple
        :param kind: transport description string (ssh, telnet)
        :type kind: str
        :param addrport: transport ip address and port as string
        :type addrport: str
        """
        from x84.bbs import ini
        self.log = logging.getLogger(__name__)

        # pylint: disable=W0603
        #        Using the global statement
        global SESSION
        assert SESSION is None, ('Session may be instantiated only once '
                                 'per sub-process')
        SESSION = self

        # public attributes
        self.terminal = terminal
        self.sid = sid
        self.env = env
        self.writer, self.reader = child_pipes
        self.kind = kind
        self.addrport = addrport

        # private attributes
        self.init_script_stack()
        self.init_attributes()

        # initialize keyboard encoding
        terminal.set_keyboard_decoder(env.get('encoding', 'utf8'))

        # oh this makes me sad !
        if BOTQUEUE is not None:
            trusted_hosts = set(['127.0.0.1'])
            addr, _ = addrport.split(':', 1)
            if ini.CFG.has_section('telnet'):
                trusted_hosts.add(ini.CFG.get('telnet', 'addr'))
            if addr in trusted_hosts:
                import Queue
                try:
                    whoami = BOTQUEUE.get(True, 0.1)
                    robots = map(str.strip,
                                 ini.CFG.get('bots', 'names').split(','))

                    if whoami in robots:
                        from x84.bbs import User
                        self.user = User(whoami)
                        self._script_stack.pop()

                        if ini.CFG.has_option('bots', addr):
                            botscript = ini.CFG.get('bots', whoami)
                            self._script_stack.append((botscript,))
                        else:
                            self._script_stack.append(('bots',))
                except Queue.Empty:
                    pass

    def init_script_stack(self):
        from x84.bbs import ini
        script_kind = 'script_{self.kind}'.format(self=self)
        if ini.CFG.has_option('matrix', script_kind):
            matrix_script = ini.CFG.get('matrix', script_kind)
        else:
            matrix_script = ini.CFG.get('matrix', 'script')
        self._script_stack = [(matrix_script,)]

    def init_attributes(self):
        from x84.bbs import ini
        self._connect_time = time.time()
        self._last_input_time = time.time()

        # create event buffer
        self._buffer = dict()

    def to_dict(self):
        """
        Returns a dictionary containing information about this session object.
        """
        return {
            attr: getattr(self, attr)
            for attr in (
                'connect_time',
                'last_input_time',
                'idle',
                'activity',
                'handle',
                'user',
                'encoding',
                'pid',
                'node',
            )
        }

    @property
    def duration(self):
        """
        Seconds elapsed since connection began as float.
        """
        return time.time() - self.connect_time

    @property
    def connect_time(self):
        """
        Time of session start as float.
        """
        return self._connect_time

    @property
    def last_input_time(self):
        """
        Time of last keypress as epoch.
        """
        return self._last_input_time

    @property
    def idle(self):
        """
        Seconds elapsed since last keypress as float.
        """
        return time.time() - self.last_input_time

    @property
    def activity(self):
        """
        Current activity (arbitrarily set). This also updates xterm titles,
        and is globally broadcasted as a "current activity" in the Who's
        online script.
        """
        return self._activity or u'<uninitialized>'

    @activity.setter
    def activity(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        if self._activity != value:
            self.log.debug('activity=%s', value)
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
        return self._user or User()

    @user.setter
    def user(self, value):
        # pylint: disable=C0111
        #         Missing docstring
        self.log.info("user {!r} -> {!r}".format(self._user, value.handle))
        self._user = value

    @property
    def encoding(self):
        """
        Session encoding.
        """
        return self.env.get('encoding', 'utf8')

    @encoding.setter
    def encoding(self, value):
        """
        Setter for Session encoding.
        """
        if value != self.encoding:
            self.log.debug('session encoding {0} -> {1}'
                           .format(self.encoding, value))
            self.env['encoding'] = value
            getterminal().set_keyboard_decoder(value)

    @property
    def pid(self):
        """
        Returns Process ID.
        """
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

    @property
    def is_recording(self):
        """ Session is being recorded """
        return self._fp_ttyrec is not None

    @property
    def ttyrec_folder(self):
        """ Folder for tty recordings. """
        from x84.bbs import ini
        return ini.CFG.get('system', 'ttyrecpath')

    @property
    def tap_input(self):
        """ Keyboard input should be logged for debugging. """
        from x84.bbs import ini
        return ini.CFG.getboolean('session', 'tap_input')

    @property
    def tap_output(self):
        """ Screen output should be logged for debugging. """
        from x84.bbs import ini
        return ini.CFG.getboolean('session', 'tap_output')

    @property
    def tap_events(self):
        """ IPC Events should be logged for debugging. """
        from x84.bbs import ini
        return ini.CFG.getboolean('session', 'tap_events')

    @property
    def record_tty(self):
        """ Whether tty recordings should be saved. """
        from x84.bbs import ini
        return ini.CFG.getboolean('session', 'record_tty')

    @property
    def show_traceback(self):
        """ Whether traceback errors should be displayed to user. """
        from x84.bbs import ini
        return ini.CFG.getboolean('system', 'show_traceback')

    @property
    def script_path(self):
        """ Base filepath folder for all scripts. """
        from x84.bbs import ini
        val = ini.CFG.get('system', 'scriptpath')
        # ensure folder exists
        assert os.path.isdir(val), (
            'configuration section [system], value scriptpath: '
            'not a folder: {!r}'.format(val))
        return val

    @property
    def script_module(self):
        """ base module location of self.script_path """
        if self._script_module is None:
            # load default/__init__.py as 'default',
            folder_name = os.path.basename(self.script_path)

            # put it in sys.path for relative imports
            if self.script_path not in sys.path:
                sys.path.insert(0, self.script_path)
                self.log.debug("sys.path[0] <- {!r}".format(self.script_path))

            # discover import path to __init__.py, store result
            lookup = imp.find_module('__init__', [self.script_path])
            self._script_module = imp.load_module(folder_name, *lookup)
            self._script_module.__path__ = self.script_path
        return self._script_module

    def __error_recovery(self):
        """ Recover from general exception in script. """
        if 0 != len(self._script_stack):
            # recover from exception
            fault = self._script_stack.pop()
            stop, oper = True, u'STOP'
            if len(self._script_stack):
                stop, oper = False, u'RESUME'
            msg = (u'%s %safter general exception in %s.' % (
                oper, (
                    (self._script_stack[-1][0] + u' ')
                    if len(self._script_stack) else u' '),
                fault[0],))
            self.log.warn(msg)
            self.write(u'\r\n\r\n')
            if stop:
                self.write(self.terminal.red_reverse(u'stop'))
            else:
                self.write(self.terminal.bold_green(u'continue'))
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
        while len(self._script_stack):
            self.log.debug('script_stack: %r', self._script_stack)
            try:
                self.runscript(*self._script_stack.pop())
                continue

            except Goto, err:
                self.log.debug('Goto: %s', err)
                self._script_stack = [err[0] + tuple(err[1:])]
                continue

            except Disconnected, err:
                self.log.info('Disconnected: %s', err)
                self.close()
                return None

            except Exception, err:
                # Pokemon exception, log and Cc: telnet client, then resume.
                e_type, e_value, e_tb = sys.exc_info()
                if self.show_traceback:
                    self.write(self.terminal.normal + u'\r\n')

                terrs = list()
                for line in traceback.format_tb(e_tb):
                    for subln in line.split('\n'):
                        terrs.append(subln)

                terrs.extend(traceback.format_exception_only(e_type, e_value))
                for etxt in map(str.rstrip, terrs):
                    self.log.error(etxt)
                    if self.show_traceback:
                        self.write(etxt + u'\r\n')

            # recover from general exception
            self.__error_recovery()

        self.log.debug('End of script stack.')
        self.close()
        return None

    def write(self, ucs):
        """
        Write unicode data to telnet client. Take special care to encode
        as 'iso8859-1' actually intended for 'cp437'-encoded terminals.

        Has side effect of updating ttyrec file when recording.
        """
        from x84.bbs.cp437 import CP437
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
            # regardless, remove them (self.TRIM_CP437)
            text = ucs.encode(encoding, 'replace')
            ucs = u''.join([(unichr(CP437.index(glyph))
                             if glyph in CP437
                             and glyph not in self.TRIM_CP437
                             else unicode(
                                 text[idx].translate(None, self.TRIM_CP437),
                                 encoding, 'replace'))
                            for (idx, glyph) in enumerate(ucs)])
        else:
            encoding = self.encoding
        self.terminal.stream.write(ucs, encoding)

        if self.log.isEnabledFor(logging.DEBUG) and self.tap_output:
            self.log.debug('--> {!r}'.format(ucs))

        if self.record_tty:
            if not self.is_recording:
                self.start_recording()
            self._ttyrec_write(ucs)

    def flush_event(self, event):
        """
        Flush all return all data buffered for 'event'.
        """
        flushed = list()
        while True:
            data = self.read_event(event, -1)
            if data is None:
                if 0 != len(flushed):
                    self.log.debug('flushed from %s: %r', event, flushed)
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
                self.log.info('page from {0}.'.format(sender))
                if not self.runscript('chat', channel, sender):
                    self.log.info('rejected page from {0}.'.format(sender))
                # buffer refresh event for any asyncronous event UI's
                self.buffer_event('refresh', 'page-return')
                return True

        # respond to 'info-req' events by returning pickled session info
        if event == 'info-req':
            sid = data[0]
            self.send_event('route', (sid, 'info-ack', self.sid, self.info(),))
            return True

        # init new unmanaged & unlimited-sized buffer ;p
        if event not in self._buffer:
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

        if self.log.isEnabledFor(logging.DEBUG) and self.tap_input:
            self.log.debug('<-- {!r}'.format(data))

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
        self.writer.send((event, data))

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
            if self.reader.poll(poll):
                event, data = self.reader.recv()
                retval = self.buffer_event(event, data)
                if self.log.isEnabledFor(logging.DEBUG) and self.tap_events:
                    stack = inspect.stack()
                    caller_mod, caller_func = stack[2][1], stack[2][3]
                    self.log.debug('event %s %s by %s in %s.', event,
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
        self._script_stack.append((script_name,) + args)
        self.log.info("run script {0!r} args={1!r}.".format(script_name, args))

        # pylint: disable=W0142
        #        Used * or ** magic
        lookup = imp.find_module(script_name, [self.script_module.__path__])
        script = imp.load_module(script_name, *lookup)
        if not hasattr(script, 'main'):
            raise ScriptError("script {!r}: main() not found."
                              .format(script_name))
        if not callable(script.main):
            raise ScriptError("script {!r}: main not callable."
                              .format(script_name))
        value = script.main(*args)
        self._script_stack.pop()
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

    def stop_recording(self):
        """
        Cease recording to ttyrec file (close).
        """
        assert self.is_recording
        self._ttyrec_write(self.terminal.normal)
        self._ttyrec_write(u'\r\n\r\n')
        self._ttyrec_write(u'\r\n'.join(
            [u'%s: %s' % (key, val)
             for (key, val) in sorted(self.info().items())]),)
        self._ttyrec_write(u'\r\n')
        self._fp_ttyrec.close()
        self._fp_ttyrec = None

    def start_recording(self):
        """
        Begin recording to ttyrec file.
        """
        assert self._fp_ttyrec is None, ('already recording')
        digit = 0
        while True:
            fname = '{ts_stamp}{digit}-{sid}.ttyrec'.format(
                ts_stamp=time.strftime('%Y%m%d.%H%M'),
                digit=digit,
                sid=self.sid.split(':', 1)[0],)
            if not os.path.exists(fname):
                break
            digit += 1
        assert os.path.sep not in fname
        filename = os.path.join(self.ttyrec_folder, fname)
        if not os.path.exists(self.ttyrec_folder):
            self.log.info('Creating folder for ttyrecordings, {0}.'
                          .format(self.ttyrec_folder))
            os.makedirs(self.ttyrec_folder)
        self._fp_ttyrec = io.open(filename, 'wb+')
        self._ttyrec_sec = -1
        self._ttyrec_write_header()
        self.log.debug('tty recording to {0}'.format(filename))

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
