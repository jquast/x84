"""
Terminal handler for x/84 bbs.  http://github.com/jquast/x84
"""
import threading
import logging
import socket
import time
import re

TERMINALS = list()


def init_term(pipe, env):
    """
    curses is initialized using the value of 'TERM' of dictionary env,
    as well as a starting window size of 'LINES' and 'COLUMNS'.

    A blessings-abstracted curses terminal is returned.
    """
    from x84.bbs.ipc import IPCStream
    from x84.blessings import Terminal
    return Terminal(env.get('TERM', 'unknown'),
                    IPCStream(pipe),
                    int(env.get('LINES', '24')),
                    int(env.get('COLUMNS', '80')))


def mkipc_rlog(pipe):
    """
    Remove any existing handlers of the current process, and
    re-address the root logging handler to an IPC event pipe
    """
    from x84.bbs.ipc import IPCLogHandler
    root = logging.getLogger()
    for hdlr in root.handlers:
        root.removeHandler(hdlr)
    root.addHandler(IPCLogHandler(pipe))


def register(client, pipe, lock):
    """
    Register a Terminal, given instances of telnet.TelnetClient,
    Pipe, and Lock.
    """
    TERMINALS.append((client, pipe, lock,))


def flush_pipe(pipe):
    """
    Seeks any remaining events in pipe, used before closing
    to prevent zombie processes with IPC waiting to be picked up.
    """
    logger = logging.getLogger()
    warned = False
    while pipe.poll():
        if not warned:
            logger.warn('pipe assertion, leftover bit(s):')
            warned = True
        event, data = pipe.recv()
        if event == 'logger':
            logger.handle(data)
        else:
            logger.warn(repr((event, data,)))
    if warned:
        logger.warn('END pipe assertion')


def unregister(client, pipe, lock):
    """
    Unregister a Terminal, described by its telnet.TelnetClient,
    Pipe, and Lock.
    """
    logger = logging.getLogger()
    try:
        flush_pipe(pipe)
        pipe.close()
    except (EOFError, IOError) as exception:
        logger.exception(exception)
    client.deactivate()
    logger.debug('%s: unregistered', client.addrport())
    TERMINALS.remove((client, pipe, lock,))


def terminals():
    """
    Returns a list of tuple (telnet.TelnetClient, Pipe, Lock).
    """
    return TERMINALS[:]


def start_process(pipe, origin, env):
    """
    A multiprocessing.Process target. Arguments:
        pipe: multiprocessing.Pipe
        origin: string describing session source (fe. IP address & Port)
        env: dictionary of client environment variables (requires 'TERM')
    """
    from x84.bbs.session import Session

    # root handler has dangerously forked file descriptors.
    # replace with ipc 'logger' events so that only the main
    # process is responsible for logging.
    mkipc_rlog(pipe)

    # initialize blessings terminal based on env's TERM.
    term = init_term(pipe, env)

    # spawn and begin a new session
    session = Session(term, pipe, origin, env)
    session.run()
    flush_pipe(pipe)
    pipe.send(('exit', None))
    pipe.close()


def on_naws(client):
    """
    On a NAWS event, check if client is yet registered in registry and send the
    pipe a refresh event. This is the same thing as ^L to the 'userland', but
    should indicate also that the window sizes are checked`.
    """
    for cpl in terminals():
        if client == cpl[0]:
            o_client, o_pipe = cpl[0], cpl[1]
            columns = int(o_client.env['COLUMNS'])
            rows = int(o_client.env['LINES'])
            o_pipe.send(('refresh', ('resize', (columns, rows),)))
            return True


class ConnectTelnet (threading.Thread):
    """
    Accept new Telnet Connection and negotiate options.
    """
    DEBUG = False
    TIME_NEGOTIATE = 0.50
    TIME_WAIT = 1.25
    TIME_POLL = 0.05
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
        pipe. Previous versions of x/84 and prsv were single process,
        thread-based, and shared variables.

        All IPC communication occurs through the bi-directional pipe.  The
        server end (engine.py) polls the parent end of a pipe, while the client
        (session.py) polls the child.
        """
        logger = logging.getLogger()
        if not self.client.active:
            logger.debug('session aborted; socket was closed.')
            return
        import multiprocessing
        parent_conn, child_conn = multiprocessing.Pipe()
        lock = threading.Lock()
        child_args = (child_conn, self.client.addrport(), self.client.env,)
        logger.debug('starting session')
        proc = multiprocessing.Process(
            target=start_process, args=child_args)
        proc.start()
        register(self.client, parent_conn, lock)

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
        # disable line-wrapping http://www.termsys.demon.co.uk/vtansi.htm
        self.client.send_str(bytes(chr(27) + '[7l'))

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
        TIME_WAIT.
        """
        return bool(time.time() - st_time < self.TIME_WAIT)

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
        self._try_cornerquery()

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
            self.client.send_str('\x1b[999;999H')
            self.client.send_str(query_seq)
            self.client.socket_send()  # push
            st_time = time.time()
            while (self.client.idle() < self.TIME_WAIT
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
