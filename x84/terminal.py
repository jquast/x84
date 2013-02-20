"""
Terminal handler for x/84 bbs.  http://github.com/jquast/x84
"""
import threading
import logging
import socket
import time
import re

TERMINALS = list()

def init_term(out_queue, lock, env):
    """
    curses is initialized using the value of 'TERM' of dictionary env,
    as well as a starting window size of 'LINES' and 'COLUMNS'.

    A blessings-abstracted curses terminal is returned.
    """
    from x84.bbs import ini
    from x84.bbs.ipc import IPCStream
    from x84.blessings import Terminal as BTerminal
    if (env.get('TERM', 'unknown') == 'ansi'
            and ini.CFG.get('system', 'termcap-ansi', u'no') != 'no'):
        # special workaround for systems with 'ansi-bbs' termcap,
        # translate 'ansi' -> 'ansi-bbs'
        # http://wiki.synchro.net/install:nix?s[]=termcap#terminal_capabilities
        env['TERM'] = ini.CFG.get('system', 'termcap-ansi')
    return BTerminal(env.get('TERM', 'unknown'),
                    IPCStream(out_queue, lock),
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


def register(client, inp_queue, out_queue, lock):
    """
    Register a Terminal, given instances of telnet.TelnetClient,
    (inp, out) Queue, and Lock.
    """
    TERMINALS.append((client, inp_queue, out_queue, lock,))


def flush_queue(queue):
    """
    Seeks any remaining events in queue, used before closing
    to prevent zombie processes with IPC waiting to be picked up.
    """
    logger = logging.getLogger()
    while queue.poll():
        event, data = queue.recv()
        if event == 'logger':
            logger.handle(data)


def unregister(client, inp_queue, out_queue, lock):
    """
    Unregister a Terminal, described by its telnet.TelnetClient,
    input and output Queues, and Lock.
    """
    logger = logging.getLogger()
    try:
        flush_queue(out_queue)
        flush_queue(inp_queue)
    except (EOFError, IOError) as exception:
        logger.exception(exception)
    client.deactivate()
    logger.debug('%s: unregistered', client.addrport())
    TERMINALS.remove((client, inp_queue, out_queue, lock,))


def terminals():
    """
    Returns a list of tuple (telnet.TelnetClient,
        input Queue, output Queue, Lock).
    """
    return TERMINALS[:]


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
    for (_client, _iqueue, _oqueue, _lock) in terminals():
        if client == _client:
            columns = int(client.env['COLUMNS'])
            rows = int(client.env['LINES'])
            _iqueue.send(('refresh', ('resize', (columns, rows),)))
            return True


class ConnectTelnet (threading.Thread):
    """
    Accept new Telnet Connection and negotiate options.
    """
    TIME_NEGOTIATE = 1.00
    TIME_WAIT_SILENT = 0.60 # wait 60ms after silence
    TIME_WAIT_STAGE = 1.90  # wait 190ms foreach negotiation
    TIME_POLL = 0.0625
    TTYPE_UNDETECTED = 'unknown'
    WINSIZE_TRICK = (
        ('vt100', ('\x1b[6n'), re.compile(chr(27) + r"\[(\d+);(\d+)R")),
        ('sun', ('\x1b[18t'), re.compile(chr(27) + r"\[8;(\d+);(\d+)t"))
    )  # see: xresize.c from X11.org

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
        register(self.client, inp_send, out_recv, lock)

    def banner(self):
        """
        This method is called after the connection is initiated.
        self.client.active is checked periodically to return early.
        This prevents attempting to negotiate with network scanners, etc.
        """
        logger = logging.getLogger()
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
        if not self.client.active:
            return

        # wait for some bytes to be received, and if we get any bytes,
        # at least make sure to get some more, and then -- wait a bit!
        logger.debug('pausing for negotiation')
        st_time = time.time()
        mrk_bytes = self.client.bytes_received
        while ((0 == mrk_bytes or mrk_bytes == self.client.bytes_received)
               and time.time() - st_time < self.TIME_NEGOTIATE
               and self.client.active):
            time.sleep(self.TIME_POLL)
        if not self.client.active:
            return
        logger.debug('negotiating options')
        self._try_env()
        if not self.client.active:
            return
        # this will set Term.kind if -still- undetected,
        # or otherwise overwrite it if it is detected different,
        self._try_ttype()
        if not self.client.active:
            return

        # this will set TERM to vt100 or sun if --still-- undetected,
        # this will set .rows, .columns if not LINES and COLUMNS
        self._try_naws()
        if not self.client.active:
            return

        # this is totally useless, but informitive debugging information for
        # unknown unix clients ..
        #self._try_xtitle()
        #if not self.client.active:
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

    def _try_naws(self):
        """
        Negotiate about window size (NAWS) telnet option (on).
        """
        logger = logging.getLogger()
        if (self.client.env.get('LINES', None) is not None
                and self.client.env.get('COLUMNS', None) is not None):
            logger.debug('window size: %sx%s (unsolicited)',
                         self.client.env.get('COLUMNS'),
                         self.client.env.get('LINES'),)
            return
        self.client.request_do_naws()
        self.client.socket_send()  # push
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
        #self._try_cornerquery()

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
        while (self.client.idle() < self.TIME_WAIT_SILENT*2
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
        This is akin to X11's 'xresize', move the cursor to the corner of the
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
        logger = logging.getLogger()
        detected = lambda: self.client.env['TERM'] != 'unknown'
        if detected():
            logger.debug('terminal type: %s (unsolicited)' %
                         (self.client.env['TERM'],))
            return
        logger.debug('request-terminal-type')
        self.client.request_ttype()
        self.client.socket_send()  # push
        st_time = time.time()
        while (not detected() and self._timeleft(st_time)
               and self.client.active):
            time.sleep(self.TIME_POLL)
        if detected():
            logger.debug('terminal type: %s (negotiated)' %
                         (self.client.env['TERM'],))
            return
        if not self.client.active:
            return
        logger.warn('%r TERM undetermined.', self.client.addrport())
