""" Terminal handler for x/84 """
import contextlib
import logging
import codecs
import sys
from blessed import Terminal as BlessedTerminal

TERMINALS = dict()


class Terminal(BlessedTerminal):

    """ A thin wrapper over :class:`blessed.Terminal`. """

    _session = None

    def __init__(self, kind, stream, rows, columns):
        """ Class initializer. """
        self._rows = rows
        self._columns = columns
        BlessedTerminal.__init__(self, kind, stream)
        if sys.platform.lower().startswith('win32'):
            self._normal = '\x1b[m'

    @property
    def session(self):
        """ Session associated with this terminal. """
        if self._session is None:
            from x84.bbs.session import getsession
            self._session = getsession()
        return self._session

    def inkey(self, timeout=None, esc_delay=0.35, *_):
        # pylint: disable=C0111
        #         Missing docstring
        try:
            return BlessedTerminal.inkey(self, timeout, esc_delay=0.35)
        except UnicodeDecodeError as err:
            log = logging.getLogger(__name__)
            log.warn('UnicodeDecodeError: {0}'.format(err))
            return u'?'
    inkey.__doc__ = BlessedTerminal.inkey.__doc__

    def set_keyboard_decoder(self, encoding):
        """ Set or change incremental decoder for keyboard input. """
        log = logging.getLogger(__name__)
        try:
            self._keyboard_decoder = codecs.getincrementaldecoder(encoding)()
            self._encoding = encoding
            log.debug('keyboard encoding is {!r}'.format(encoding))
        except Exception as err:
            log.exception(err)

    def kbhit(self, timeout=0, *_):
        # pylint: disable=C0111
        #         Missing docstring
        # pull a value off the input buffer if available,
        val = self.session.read_event('input', timeout)

        # if available, place back into buffer and return True,
        if val is not None:
            self.session.buffer_input(val, pushback=True)
            return True

        # no value available within timeout.
        return False
    kbhit.__doc__ = BlessedTerminal.kbhit.__doc__

    def getch(self):
        # pylint: disable=C0111
        #         Missing docstring
        val = self.session.read_event('input')
        return self._keyboard_decoder.decode(val, final=False)
    getch.__doc__ = BlessedTerminal.getch.__doc__

    def _height_and_width(self):
        # pylint: disable=C0111
        #         Missing docstring
        from blessed.terminal import WINSZ
        return WINSZ(ws_row=self._rows, ws_col=self._columns,
                     ws_xpixel=None, ws_ypixel=None)
    _height_and_width.__doc__ = BlessedTerminal._height_and_width.__doc__

    @contextlib.contextmanager
    def raw(self):
        """ Dummy method yields nothing for blessed compatibility. """
        yield

    @contextlib.contextmanager
    def cbreak(self):
        """ Dummy method yields nothing for blessed compatibility. """
        yield

    @property
    def is_a_tty(self):
        """ Dummy property always returns True. """
        return True


def translate_ttype(ttype):
    """
    Return preferred terminal type given the session-negotiation ttype.

    This provides a kind of coercion; we know some terminals, such as
    SyncTerm report a terminal type of 'ansi' -- however, the author
    publishes a termcap database for 'ansi-bbs' which he instructs
    should be used!  So an ``[system]`` configuration item
    of ``termcap-ansi`` may be set to ``'ansi-bbs'`` to coerce
    such terminals for Syncterm-centric telnet servers -- though I
    would not recommend it.

    Furthermore, if the ttype is (literally) 'unknown', then a
    system-wide default terminal type may be returned, also by
    ``[system]`` configuration option ``termcap-unknown``.
    """
    from x84.bbs import get_ini
    log = logging.getLogger(__name__)

    termcap_unknown = get_ini('system', 'termcap-unknown') or 'ansi'
    termcap_ansi = get_ini('system', 'termcap-ansi') or 'ansi'

    if termcap_unknown != 'no' and ttype == 'unknown':
        log.debug("terminal-type {0!r} => {1!r}"
                  .format(ttype, termcap_unknown))
        return termcap_unknown

    elif (termcap_ansi != 'no' and ttype.lower().startswith('ansi')
          and ttype != termcap_ansi):
        log.debug("terminal-type {0!r} => {1!r}"
                  .format(ttype, termcap_ansi))
        return termcap_ansi

    return ttype


def determine_encoding(env):
    """ Determine and return preferred encoding given session env. """
    from x84.bbs import get_ini
    default_encoding = get_ini(
        section='session', key='default_encoding'
    ) or 'utf8'

    fallback_encoding = {
        'ansi': 'cp437',
        'ansi-bbs': 'cp437',
    }.get(env['TERM'], default_encoding)

    return env.get('encoding', fallback_encoding)


def init_term(writer, env):
    """
    Determine the final TERM and encoding and return a Terminal.

    curses is initialized using the value of 'TERM' of dictionary env,
    as well as a starting window size of 'LINES' and 'COLUMNS'. If the
    terminal-type is of 'ansi' or 'ansi-bbs', then the cp437 encoding
    is assumed; otherwise 'utf8'.

    A blessed-abstracted curses terminal is returned.
    """
    from x84.bbs.ipc import IPCStream
    from x84.bbs import get_ini
    log = logging.getLogger(__name__)
    env['TERM'] = translate_ttype(env.get('TERM', 'unknown'))
    env['encoding'] = determine_encoding(env)
    term = Terminal(kind=env['TERM'],
                    stream=IPCStream(writer=writer),
                    rows=int(env.get('LINES', '24')),
                    columns=int(env.get('COLUMNS', '80')))

    if term.kind is None:
        # the given environment's TERM failed curses initialization
        # because, more than likely, the TERM type was not found.
        termcap_unknown = get_ini('system', 'termcap-unknown') or 'ansi'
        log.debug('terminal-type {0} failed, using {1} instead.'
                  .format(env['TERM'], termcap_unknown))
        term = Terminal(kind=termcap_unknown,
                        stream=IPCStream(writer=writer),
                        rows=int(env.get('LINES', '24')),
                        columns=int(env.get('COLUMNS', '80')))

    log.info("terminal type is {0!r}".format(term.kind))
    return term


class TerminalProcess(object):

    """
    Class record for tracking "terminals".

    Probably of most interest, is that a ``TerminalProcess``
    is an abstract association with a multiprocessing.Process
    sub-process, and its i/o queues (``master_pipes``).

    This is not a really tty, or even a pseudo-tty (pty)!  No
    termios, fnctl, or any terminal driver i/o is performed, it
    is all virtual.

    An instance of this class is stored using :func:`register_tty`
    and removed by :func:`unregister_tty`, and discovered using
    :func:`get_terminals`.
    """

    def __init__(self, client, sid, master_pipes):
        """ Class constructor. """
        from x84.bbs import get_ini
        self.client = client
        self.sid = sid
        (self.master_write, self.master_read) = master_pipes
        self.timeout = get_ini('system', 'timeout') or 0


def flush_queue(queue):
    """
    Flush all data awaiting on the ipc queue.

    Seeks any remaining events in queue, used before closing
    to prevent zombie processes with IPC waiting to be picked up.
    """
    log = logging.getLogger(__name__)
    try:
        while queue.poll():
            event, data = queue.recv()
            if event == 'logger':
                log.handle(data)
    except (EOFError, IOError) as err:
        log.debug(err)


def register_tty(tty):
    """ Register a :class:`TerminalProcess` instance. """
    log = logging.getLogger(__name__)
    log.debug('[{tty.sid}] registered tty'.format(tty=tty))
    TERMINALS[tty.sid] = tty


def unregister_tty(tty):
    """ Unregister a :class:`TerminalProcess` instance. """
    try:
        flush_queue(tty.master_read)
        tty.master_read.close()
        tty.master_write.close()
    except (EOFError, IOError) as err:
        log = logging.getLogger(__name__)
        log.exception(err)
    if tty.client.active:
        # signal tcp socket to close
        tty.client.deactivate()
    del TERMINALS[tty.sid]


def get_terminals():
    """ Returns a list of all terminals as tuples (session-id, ttys). """
    return TERMINALS.items()


def find_tty(client):
    """ Given a client, return a matching tty, or None if not registered. """
    try:
        return next(tty for _, tty in get_terminals() if client == tty.client)
    except StopIteration:
        pass


def kill_session(client, reason='killed'):
    """ Given a client, shutdown its socket and signal subprocess exit. """
    from x84.bbs.exception import Disconnected
    client.shutdown()

    log = logging.getLogger(__name__)
    tty = find_tty(client)
    if tty is not None:
        try:
            tty.master_write.send(('exception', Disconnected(reason),))
        except (EOFError, IOError):
            pass
        log.info('[{tty.sid}] goodbye: {reason}'
                 .format(tty=tty, reason=reason))
        unregister_tty(tty)


def start_process(sid, env, CFG, child_pipes, kind, addrport,
                  matrix_args=None, matrix_kwargs=None):
    """
    A ``multiprocessing.Process`` target.

    :param str sid: string describing session source (IP address & port).
    :param dict env: dictionary of client environment variables
                     (must contain at least ``'TERM'``).
    :param ConfigParser.ConfigParser CFG: bbs configuration
    :param tuple child_pipes: tuple of ``(writer, reader)`` for engine IPC.
    :param str kind: what kind of connection as string, ``'telnet'``,
                     ``'ssh'``, etc.
    :param tuple addrport: ``(client-ip, client-port)`` as string and integer.
    :param tuple matrix_args: optional positional arguments to pass to matrix
                              script.
    :param dict matrix_kwargs: optional keyward arguments to pass to matrix
                               script.
    """
    # pylint: disable=R0913,R0914
    #         Too many arguments (8/5)
    #         Too many local variables (16/15)
    import x84.bbs.ini
    from x84.bbs.ipc import make_root_logger
    from x84.bbs.session import Session

    # CFG must be pickled and sent to child process; on windows systems,
    # fork() does not duplicate that it has been initialized, and requires
    # sending to child process
    x84.bbs.ini.CFG = CFG

    (writer, _) = child_pipes

    # remove any existing log handlers in child process and replace
    # with a new root log handler that sends to x84.bbs.engine over IPC.
    make_root_logger(writer)

    # instantiate and create a new terminal instance given the value
    # of env[TERM], negotiated by protocol. May modify the value of
    # env[TERM] by function translate_ttype
    terminal = init_term(writer=writer, env=env)

    try:
        # instantiate and run session
        kwargs = {
            'terminal': terminal,
            'sid': sid,
            'env': env,
            'child_pipes': child_pipes,
            'kind': kind,
            'addrport': addrport,
            'matrix_args': matrix_args or (),
            'matrix_kwargs': matrix_kwargs or {},
        }
        Session(**kwargs).run()
    finally:
        # signal exit to engine
        try:
            writer.send(('exit', None))
        except IOError as err:
            # ignore [Errno 232] The pipe is being closed,
            # only occurs on win32 platform after early exit
            if err.errno != 232:
                raise


def spawn_client_session(client, matrix_kwargs=None):
    """ Spawn sub-process for connecting client.

    Optional
    """
    from multiprocessing import Process, Pipe
    import x84.bbs.ini

    child_read, master_write = Pipe(duplex=False)
    master_read, child_write = Pipe(duplex=False)
    session_id = '{client.kind}-{client.addrport}'.format(client=client)

    # start sub-process, which will initialize the terminal and
    # begins the 'session' for the connecting client.
    Process(target=start_process, kwargs={
        'sid': session_id,
        'env': client.env,
        'CFG': x84.bbs.ini.CFG,
        'child_pipes': (child_write, child_read),
        'kind': client.kind,
        'addrport': client.addrport,
        'matrix_kwargs': matrix_kwargs,
    }).start()

    # and register its tty and master-side pipes for polling by x84.engine
    register_tty(TerminalProcess(client=client,
                                 sid=session_id,
                                 master_pipes=(master_write, master_read)))


def on_naws(client):
    """
    Callback for telnet NAWS negotiation.

    On a Telnet NAWS sub-negotiation, check if client is yet registered
    in registry, and if so, send a 'refresh' event down the event queue.

    This is ultimately handled by :meth:`x84.bbs.session.Session.buffer_event`.
    """
    for _, tty in get_terminals():
        if client == tty.client:
            columns = int(client.env['COLUMNS'])
            rows = int(client.env['LINES'])
            tty.master_write.send(('refresh', ('resize', (columns, rows),)))
            break
    return True
