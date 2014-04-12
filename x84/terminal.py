"""
Terminal handler for x/84 bbs.  http://github.com/jquast/x84
"""
import threading
import logging
import socket
import codecs
import time
import re

from blessed import Terminal as BlessedTerminal

TERMINALS = dict()


class Terminal(BlessedTerminal):
    def __init__(self, kind, stream, rows, columns):
        self.rows = rows
        self.columns = columns
        BlessedTerminal.__init__(self, kind, stream)

    def inkey(self, timeout=None, esc_delay=0.35):
        try:
            return BlessedTerminal.inkey(self, timeout, esc_delay=0.35)
        except UnicodeDecodeError, err:
            log = logging.getLogger()
            log.warn('UnicodeDecodeError: {}'.format(err))
            return u'?'

    def set_keyboard_decoder(self, encoding):
        try:
            self._keyboard_decoder = codecs.getincrementaldecoder(encoding)()
            self._encoding = encoding
        except Exception, err:
            log = logging.getLogger()
            log.exception(err)

    def kbhit(self, timeout=0, _intr_continue=True):
        # _intr_continue has no meaning here, sigwinch or events do not
        # interrupt the event IPC.
        from x84.bbs import getsession
        val = getsession().read_event('input', timeout)
        if val is not None:
            getsession()._buffer['input'].append(val)
            return True
        return False

    def getch(self):
        from x84.bbs import getsession
        val = getsession().read_event('input')
        return self._keyboard_decoder.decode(val, final=False)

    def _height_and_width(self):
        from blessed.terminal import WINSZ
        return WINSZ(ws_row=self.rows, ws_col=self.columns,
                     ws_xpixel=None, ws_ypixel=None)

    @property
    def is_a_tty(self):
        return True


def init_term(out_queue, lock, env):
    """
    curses is initialized using the value of 'TERM' of dictionary env,
    as well as a starting window size of 'LINES' and 'COLUMNS'.

    A blessings-abstracted curses terminal is returned.
    """
    from x84.bbs import ini
    from x84.bbs.ipc import IPCStream
    log = logging.getLogger()
    ttype = env.get('TERM', 'unknown')
    if (ttype == 'ansi'
            and ini.CFG.get('system', 'termcap-ansi') != 'no'):
        # special workaround for systems with 'ansi-bbs' termcap,
        # translate 'ansi' -> 'ansi-bbs'
        # http://wiki.synchro.net/install:nix?s[]=termcap#terminal_capabilities
        env['TERM'] = ini.CFG.get('system', 'termcap-ansi')
        log.debug('TERM %s transliterated to %s' % ( ttype, env['TERM'],))
    elif (ttype == 'unknown'
            and ini.CFG.get('system', 'termcap-unknown') != 'no'):
        # instead of using 'unknown' as a termcap definition, try to use
        # the most broadly capable termcap possible, 'vt100', configurable with
        # default.ini
        env['TERM'] = ini.CFG.get('system', 'termcap-unknown')
        log.debug('TERM %s transliterated to %s' % ( ttype, env['TERM'],))
    else:
        log.debug('TERM is %s' % (ttype,))
    stream = IPCStream(out_queue, lock)
    return Terminal(env.get('TERM', 'unknown'), stream,
            int(env.get('LINES', '24')),
            int(env.get('COLUMNS', '80'),))


def mkipc_rlog(out_queue):
    """
    Remove any existing handlers of the current process, and
    re-address the root logging handler to an IPC output event queue
    """
    from x84.bbs.ipc import IPCLogHandler
    root = logging.getLogger()
    for _hdlr in root.handlers:
        root.removeHandler(_hdlr)
    hdlr = IPCLogHandler(out_queue)
    root.addHandler(hdlr)
    return hdlr


class TerminalProcess():
    """
    Class record for tracking global processes and their
    various attributes. These are stored using register() and unregister(),
    and retrieved using terminals().
    """
    # pylint: disable=R0903
    #         Too few public methods
    def __init__(self, client, iqueue, oqueue, lock):
        from x84.bbs.ini import CFG
        self.client = client
        self.iqueue = iqueue
        self.oqueue = oqueue
        self.lock = lock
        self.timeout = CFG.getint('system', 'timeout')

    @property
    def sid(self):
        """ Returns session id. """
        return self.client.addrport()


def register(tty):
    """
    Register a global instance of TerminalProcess
    """
    TERMINALS[tty.sid] = tty


def flush_queue(queue):
    """
    Seeks any remaining events in queue, used before closing
    to prevent zombie processes with IPC waiting to be picked up.
    """
    logger = logging.getLogger()
    try:
        while queue.poll():
            event, data = queue.recv()
            if event == 'logger':
                logger.handle(data)
    except (EOFError, IOError) as err:
        logger.debug(err)


def unregister(tty):
    """
    Unregister a Terminal, described by its telnet.TelnetClient,
    input and output Queues, and Lock.
    """
    logger = logging.getLogger()
    try:
        flush_queue(tty.oqueue)
        tty.oqueue.close()
        tty.iqueue.close()
    except (EOFError, IOError) as err:
        logger.exception(err)
    if tty.client.active:
        # signal tcp socket to close
        tty.client.deactivate()
    del TERMINALS[tty.sid]
    logger.debug('%s: unregistered', tty.client.addrport())


def terminals():
    """
    Returns a list of tuple (telnet.TelnetClient,
        input Queue, output Queue, Lock).
    """
    return TERMINALS.items()


# pylint: disable=R0913
#         Too many arguments (6/5)
def start_process(inp_queue, out_queue, sid, env, lock, binary=False):
    """
    A multiprocessing.Process target. Arguments:
        inp_queue and out_queue: multiprocessing.Queue
        sid: string describing session source (fe. IP address & Port)
        env: dictionary of client environment variables (requires 'TERM')
        binary: If client accepts BINARY, assume utf8 session encoding.
    """
    import x84.bbs.ini
    import x84.bbs.session
    # terminals of these types are forced to 'cp437' encoding,
    # we could also more safely assume iso8859-1, which is the
    # correct default encoding of those terminals, but we explicitly
    # send the 'set graphics character code' attribute for cp437.
    #
    # If they don't honor it, they don't get to see the art correctly.
    cp437_ttypes = ('unknown', 'ansi', 'ansi-bbs', 'vt100',)

    # root handler has dangerously forked file descriptors.
    # replace with ipc 'logger' events so that only the main
    # process is responsible for logging.
    hdlr = mkipc_rlog(out_queue)
    # initialize blessings terminal based on env's TERM.
    term = init_term(out_queue, lock, env)
    # negotiate encoding; terminals with BINARY mode are utf-8
    encoding = x84.bbs.ini.CFG.get('session', 'default_encoding')
    if env.get('TERM', 'unknown') in cp437_ttypes:
        encoding = 'cp437'
    elif env.get('TERM', 'unknown').startswith('vt'):
        encoding = 'cp437'
    elif binary:
        encoding = 'utf8'
    # spawn and begin a new session
    session = x84.bbs.session.Session(
        term, inp_queue, out_queue, sid, env, lock, encoding)
    # copy session ptr to logger handler for 'handle' emit logging
    hdlr.session = session
    # run session
    session.run()
    # signal engine to shutdown subprocess
    out_queue.send(('exit', None))


def on_naws(client):
    """
    On a NAWS event, check if client is yet registered in registry and send
    the input event queue a 'refresh' event. This is the same thing as ^L
    to the 'userland', but should indicate also that the window sizes are
    checked`.
    """
    for _sid, tty in terminals():
        if client == tty.client:
            columns = int(client.env['COLUMNS'])
            rows = int(client.env['LINES'])
            tty.iqueue.send(('refresh', ('resize', (columns, rows),)))
            return True


class ConnectTelnet (threading.Thread):
    """
    Accept new Telnet Connection and negotiate options.
    """
    # this all gets much better using "telnetlib3" tulip/Futures, this is
    # a pretty poor implementation, but necessary for correct "TERM" before
    # going through the trouble of spawning a new process -- that process
    # may only call curses.setupterm() once per process, so it is imperative
    # to make a "good call"; which is a combination of many several factors
    TIME_NEGOTIATE = 2.50  # wait 2500ms on-connect
    TIME_WAIT_STAGE = 3.50  # wait upto 3500ms foreach stage of negotiation :(
    TIME_WAIT_SILENT = 2.50  # wait 2500ms after silence
    TIME_POLL = 0.15
    TTYPE_UNDETECTED = 'unknown'
    WINSIZE_TRICK = (
        ('vt100', ('\x1b[6n'), re.compile(chr(27) + r"\[(\d+);(\d+)R")),
        ('sun', ('\x1b[18t'), re.compile(chr(27) + r"\[8;(\d+);(\d+)t"))
    )  # see: xresize.c from X11.org
    DA_REPLIES = (
        ('\x1b[?1;0c', 'vt100', ''),
        ('\x1b[?1;1c', 'vt100', 'STP'),
        ('\x1b[?1;3c', 'vt100', 'STP;AVO'),
        ('\x1b[?1;4c', 'vt100', 'GPO'),
        ('\x1b[?1;5c', 'vt100', 'STP;GPO'),
        ('\x1b[?1;6c', 'vt100', 'AVO;GPO'),
        ('\x1b[?1;7c', 'vt100', 'STP;AVO;GPO'),
        ('\x1b[?1;11c', 'vt100', 'PP;AVO'),
        ('\x1b[?1;15c', 'vt100', 'PP;GPO;AVO'),
        ('\x1b[?4;2c', 'vt132', 'AVO'),
        ('\x1b[?4;3c', 'vt132', 'AVO;STP'),
        ('\x1b[?4;6c', 'vt132', 'GPO;AVO'),
        ('\x1b[?4;7c', 'vt132', 'GPO;AVO;STP'),
        ('\x1b[?4;11c', 'vt132', 'PP;AVO'),
        ('\x1b[?4;15c', 'vt132', 'PP;GPO;AVO'),
        ('\x1b[?6c', 'vt102', ''),
        ('\x1b[?1;2c', 'vt102', 'AVO'),
        ('\x1b[?7c', 'vt131', ''),
        ('\x1b[?12;5c', 'vt125', ''),
        ('\x1b[?12;7c', 'vt125', 'AVO'),
        ('\x1b[?62;1;2;4;6;8;9;15c', 'vt220', ''),
        ('\x1b[?63;1;2;8;9c', 'vt320', ''),
        ('\x1b[?63;1;2;4;6;8;9;15c', 'vt320', ''),
    ) # see: report.c from vttest



    def __init__(self, client):
        """
        client is a telnet.TelnetClient instance.
        """
        self.client = client
        threading.Thread.__init__(self)

    def _spawn_session(self):
        """
        Spawn a subprocess, avoiding GIL and forcing all shared data over a
        Queue. Previous versions of x/84 and prsv were single process,
        thread-based, and shared variables.

        All IPC communication occurs through the bi-directional queues.  The
        server end (engine.py) polls the out_queue, and places results
        and input events into the inp_queue, while the client end (session.py),
        polls the inp_queue, and places output into out_queue.
        """
        logger = logging.getLogger()
        if not self.client.active:
            logger.debug('session aborted; socket was closed.')
            return
        from multiprocessing import Process, Pipe, Lock
        from x84.telnet import BINARY
        inp_recv, inp_send = Pipe(duplex=False)
        out_recv, out_send = Pipe(duplex=False)
        lock = Lock()
        is_binary = (self.client.check_local_option(BINARY)
                     and self.client.check_remote_option(BINARY))
        child_args = (inp_recv, out_send, self.client.addrport(),
                      self.client.env, lock, is_binary)
        logger.debug('starting session')
        proc = Process(target=start_process, args=child_args)
        proc.start()
        tty = TerminalProcess(self.client, inp_send, out_recv, lock)
        register(tty)

    def banner(self):
        """
        This method is called after the connection is initiated.

        This routine happens to communicate with a wide variety of network
        scanners when listening on the default port on a public IP address.
        """
        logger = logging.getLogger()
        mrk_bytes = self.client.bytes_received
        # According to Roger Espel Llima (espel@drakkar.ens.fr), you can
        #   have your server send a sequence of control characters:
        # (0xff 0xfb 0x01) (0xff 0xfb 0x03) (0xff 0xfd 0x0f3).
        #   Which translates to:
        # (IAC WILL ECHO) (IAC WILL SUPPRESS-GO-AHEAD)
        # (IAC DO SUPPRESS-GO-AHEAD).
        self.client.request_will_echo()
        self.client.request_will_sga()
        self.client.request_do_sga()
        # add DO & WILL BINARY, for utf8 input/output.
        self.client.request_do_binary()
        self.client.request_will_binary()
        self.client.request_do_ttype()
        # and do naws, please.
        self.client.request_do_naws()
        self.client.socket_send()  # push

        if not self.client.active:
            return
        # wait at least 1.25s for the client to speak. If it doesn't,
        # we try only TTYPE. If it fails to report that, we forget
        # the rest.
        logger.debug('pausing for negotiation')
        st_time = time.time()
        while ((0 == self.client.bytes_received
            or mrk_bytes == self.client.bytes_received)
               and time.time() - st_time < self.TIME_NEGOTIATE
               and self.client.active):
            self.client.send_str(chr(0))  # send NUL; keep scanners with us,
            self.client.socket_send()  # push
            time.sleep(self.TIME_POLL)
        mrk_bytes = self.client.bytes_received
        self._try_ttype()
        #if ((0 == self.client.bytes_received
        #          or mrk_bytes == self.client.bytes_received)
        #        or self.client.env.get('TERM', 'unknown')):
        #    # having not received a single byte, we opt out of the
        #    # negotiation program. Usually, the connecting client is
        #    # a scanner; the equivalent of:
        #    #  (printf "root\n"; sleep 5) | nc host > log.txt
        #    logger.info('Dumb terminal detected; no further negotiation.')
        #    return

        self._try_env()
        # this will set Term.kind if -still- undetected,
        # or otherwise overwrite it if it is detected different.
        # First, telnet TTYPE is explicitly requested. If no
        # reply is found, then a dec terminal attributes
        # request is made, and a vt* terminal type is set.

        # XXX Disabled, was not found to be very useful.
        # If this fails, or response is amiguous ('vt100'), try for
        # extended dec types. If not, just get them anyway.
        #self._try_device_attributes()

        # check for naws reply. This will set TERM to vt100
        # or sun if the terminal is --still-- undetected.
        # Otherwise sets LINES and COLUMNS env variables to response.
        self._check_naws()

        # this is totally useless, but informitive debugging information for
        # unknown unix clients ..
        # self._try_xtitle()
        # if not self.client.active:
        #    return

    def run(self):
        """
        Negotiate and inquire about terminal type, telnet options, window size,
        and tcp socket options before spawning a new session.
        """
        logger = logging.getLogger()
        from x84.bbs.exception import Disconnected
        try:
            self._set_socket_opts()
            self.banner()
            self._spawn_session()
        except socket.error as err:
            logger.debug('Connection closed: %s', err)
            self.client.deactivate()
        except Disconnected as err:
            logger.debug('Connection closed: %s', err)
            self.client.deactivate()

    def _timeleft(self, st_time):
        """
        Returns True when difference of current time and st_time is below
        TIME_WAIT_STAGE.
        """
        return bool(time.time() - st_time < self.TIME_WAIT_STAGE)

    def _set_socket_opts(self):
        """
        Set socket non-blocking and enable TCP KeepAlive.
        """
        self.client.sock.setblocking(0)
        self.client.sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    def _try_env(self):
        """
        Try to snarf out some environment variables from unix machines.
        """
        if not self.client.active:
            return
        logger = logging.getLogger()
        from x84.telnet import NEW_ENVIRON, UNKNOWN
        # hard to tell if we already sent this once .. we mimmijammed
        # our own test ..
        if(self.client.ENV_REQUESTED and self.client.ENV_REPLIED):
            logger.debug('environment enabled (unsolicted)')
            return
        logger.debug('request-do-env')
        self.client.request_do_env()
        self.client.socket_send()  # push
        st_time = time.time()
        while (self.client.check_remote_option(NEW_ENVIRON) is UNKNOWN
                and not self.client.ENV_REPLIED
                and self._timeleft(st_time)
               and self.client.active):
            time.sleep(self.TIME_POLL)
        if not self.client.active:
            return
        if self.client.check_remote_option(NEW_ENVIRON) is UNKNOWN:
            logger.debug('failed: NEW_ENVIRON')

    def _check_naws(self):
        """
        Negotiate about window size (NAWS) telnet option (on).
        """
        if not self.client.active:
            return
        logger = logging.getLogger()
        if (self.client.env.get('LINES', None) is not None
                and self.client.env.get('COLUMNS', None) is not None):
            logger.debug('window size: %sx%s (unsolicited)',
                         self.client.env.get('COLUMNS'),
                         self.client.env.get('LINES'),)
            return
        st_time = time.time()
        while (self.client.env.get('LINES', None) is None
                and self.client.env.get('COLUMNS', None) is None
                and self._timeleft(st_time)
                and self.client.active):
            time.sleep(self.TIME_POLL)
        if (self.client.env.get('LINES', None) is not None
                and self.client.env.get('COLUMNS', None) is not None):
            logger.info('window size: %sx%s (negotiated)',
                        self.client.env.get('COLUMNS'),
                        self.client.env.get('LINES'))
            return
        if not self.client.active:
            return
        logger.debug('failed: negotiate about window size')
        self._try_cornerquery()

    def _try_xtitle(self):
        """
        request xterm title and store as _xtitle 'env' variable,
        this is restored on goodbye/logoff..

        actually, going to use restore codes in addition, to, nice to know
        anyway. may help with terminal id?
        """
        # P s = 2 1 -> Report xterm window's title. Result is OSC l label ST
        # http://invisible-island.net/xterm/ctlseqs/ctlseqs.html#VT100%20Mode
        # http://www.xfree86.org/4.5.0/ctlseqs.html#VT100%20Mode
        logger = logging.getLogger()
        logger.debug('report-xterm-title')
        self.client.send_str(chr(27) + '[21t')
        self.client.socket_send()  # push
        # response is '\x1b]lbash\x1b\\'
        response_pattern = re.compile(''.join((
            re.escape(chr(27)),
            r"\]l(.*)",
            re.escape(chr(27)),
            re.escape('\\'),)))
        st_time = time.time()
        while (self.client.idle() < self.TIME_WAIT_SILENT
               and self._timeleft(st_time)
               and self.client.active):
            time.sleep(self.TIME_POLL)
        if not self.client.active:
            return
        inp = self.client.get_input()
        match = response_pattern.search(inp)
        if not match:
            logger.debug('failed: xterm-title')
            return
        self.client.env['_xtitle'] = match.group(1).decode(
            'utf8', 'replace')
        logger.info('window title: %s', self.client.env['_xtitle'])
        self.client.send_str(chr(27) + '[20t')
        self.client.socket_send()  # push
        # response is '\x1b]Lbash\x1b\\'
        response_pattern = re.compile(''.join((
            re.escape(chr(27)),
            r"\]L(.*)",
            re.escape(chr(27)),
            re.escape('\\'),)))
        st_time = time.time()
        while (self.client.idle() < self.TIME_WAIT_SILENT * 2
               and self._timeleft(st_time)
               and self.client.active):
            time.sleep(self.TIME_POLL)
        if not self.client.active:
            return
        inp = self.client.get_input()
        match = response_pattern.search(inp)
        if not match:
            logger.debug('failed: xterm-icon')
            return
        self.client.env['_xicon'] = match.group(1).decode(
            'utf8', 'replace')
        logger.info('window icon: %s', self.client.env['_xicon'])

    def _try_cornerquery(self):
        """
        This is akin to X11's 'resize', move the cursor to the corner of the
        terminal (999,999) and request the terminal to report their cursor
        position.
        """
        logger = logging.getLogger()
        # Try #2 ... this works for most any screen
        # send to client --> pos(999,999)
        # send to client --> report cursor position
        # read from client <-- window size
        # bonus: 'vt100' or 'sun' TERM type set, lol.
        logger.debug('store-cu')
        self.client.send_str('\x1b[s')
        for kind, query_seq, response_pattern in self.WINSIZE_TRICK:
            logger.debug('move-to corner & query for %s', kind)
            # crashes syncterm with 999; changed to 255.
            self.client.send_str('\x1b[255;255')
            self.client.send_str(query_seq)
            self.client.socket_send()  # push
            st_time = time.time()
            while (self.client.idle() < self.TIME_WAIT_SILENT
                   and self._timeleft(st_time)
                   and self.client.active):
                time.sleep(self.TIME_POLL)
            if not self.client.active:
                return
            inp = self.client.get_input()
            self.client.send_str('\x1b[r')
            logger.debug('cursor restored')
            self.client.socket_send()  # push
            match = response_pattern.search(inp)
            if match:
                height, width = match.groups()
                self.client.rows = int(height)
                self.client.columns = int(width)
                logger.info('window size: %dx%d (corner-query hack)',
                            self.client.columns, self.client.rows)
                if self.client.env['TERM'] == 'unknown':
                    logger.warn("env['TERM'] = %r by POS", kind)
                    self.client.env['TERM'] = kind
                self.client.env['LINES'] = height
                self.client.env['COLUMNS'] = width
                return

        logger.debug('failed: negotiate about window size')
        # set to 80x24 if not detected
        self.client.columns, self.client.rows = 80, 24
        logger.debug('window size: %dx%d (default)',
                     self.client.columns, self.client.rows)
        self.client.env['LINES'] = str(self.client.rows)
        self.client.env['COLUMNS'] = str(self.client.columns)

    def _try_ttype(self):
        """
        Negotiate terminal type (TTYPE) telnet option (on).
        """
        if not self.client.active:
            return
        logger = logging.getLogger()
        detected = lambda: self.client.env['TERM'] != 'unknown'
        if detected():
            logger.debug('terminal type: %s (unsolicited)' %
                         (self.client.env['TERM'],))
            return
        logger.debug('request-terminal-type')
        st_time = time.time()
        if not detected():
            self.client.request_ttype()
            self.client.socket_send()  # push
        while (not detected() and self._timeleft(st_time)
               and self.client.active):
            time.sleep(self.TIME_POLL)
        if detected():
            logger.debug('terminal type: %s (negotiated by ttype)' %
                         (self.client.env['TERM'],))
            return
        if not self.client.active:
            return
        logger.warn('%r TERM not determined by TTYPE.', self.client.addrport())

    def _try_device_attributes(self):
        """
        Try to identify the type of DEC terminal. reports.c of vttest
        includes all the valid responses!
        """
        if not self.client.active:
            return
        logger = logging.getLogger()
        logger.debug('request-device-attributes')
        query_seq = bytes('\x1b[0c')
        self.client.send_str(query_seq)
        self.client.socket_send()  # push
        st_time = time.time()
        while (self._timeleft(st_time) and self.client.active):
            time.sleep(self.TIME_POLL)
        if not self.client.active:
            return
        inp = self.client.get_input()
        matched = False
        for p in range(len(inp)):
            for pattern, ttype, attrs in self.DA_REPLIES:
                if inp[p:].startswith(pattern):
                    matched = (inp[p:p+len(pattern)], ttype, attrs)
                    break
            if matched:
                break
        if matched:
            sequence, ttype, attrs = matched
            if len(sequence) != len(inp):
                # if we received more bytes than just the sequence, we
                # don't really care to rewind and buffer the rest for
                # later interpretation.
                toss_left = inp[:inp.find(sequence)] 
                toss_right = inp[inp.find(sequence) + len(sequence):]
                logger.warn("threw out during da reply: %r, <DA>, %r.",
                        toss_left, toss_right)
                self.client.env['DA'] = matched
            if (self.client.env.get('TERM', 'unknown')
                    in ('unknown', 'vt100', 'sun')):
                    logger.debug("%r terminal type: %s by da",
                            self.client.addrport(), ttype)
                    self.client.env['TERM'] = ttype
                    # custom environment variable, we worked so hard to get it,
                    self.client.env['TERM_ATTRS'] = attrs  # why throw it away?
            else:
                logger.info('%r adheres to %s;%s',
                        self.client.addrport(), ttype, attrs)
                self.client.env['TERM_ALT'] = ttype
                self.client.env['TERM_ATTRS'] = attrs
        else:
            logger.warn('%r no DEC VT response.', self.client.addrport())
            return

