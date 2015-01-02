"""
Terminal handler for x/84 bbs.  http://github.com/jquast/x84
"""
import logging
import codecs
import sys
from blessed import Terminal as BlessedTerminal

TERMINALS = dict()


class Terminal(BlessedTerminal):
    _session = None

    def __init__(self, kind, stream, rows, columns):
        self.rows = rows
        self.columns = columns
        BlessedTerminal.__init__(self, kind, stream)
        if sys.platform.lower().startswith('win32'):
            self._normal = '\x1b[m'

    @property
    def session(self):
        if self._session is None:
            from x84.bbs.session import getsession
            self._session = getsession()
        return self._session

    def inkey(self, timeout=None, esc_delay=0.35):
        try:
            return BlessedTerminal.inkey(self, timeout, esc_delay=0.35)
        except UnicodeDecodeError, err:
            log = logging.getLogger(__name__)
            log.warn('UnicodeDecodeError: {}'.format(err))
            return u'?'
    inkey.__doc__ = BlessedTerminal.inkey.__doc__

    def set_keyboard_decoder(self, encoding):
        log = logging.getLogger(__name__)
        try:
            self._keyboard_decoder = codecs.getincrementaldecoder(encoding)()
            self._encoding = encoding
            log.debug('keyboard encoding is {!r}'.format(encoding))
        except Exception, err:
            log.exception(err)

    def kbhit(self, timeout=0, *_):
        # pull a value off the input buffer if available,
        val = self.session.read_event('input', timeout)

        # if available, place back into buffer and return True,
        if val is not None:
            self.session._buffer['input'].append(val)
            return True

        # no value available within timeout.
        return False
    kbhit.__doc__ = BlessedTerminal.kbhit.__doc__

    def getch(self):
        val = self.session.read_event('input')
        return self._keyboard_decoder.decode(val, final=False)
    getch.__doc__ = BlessedTerminal.getch.__doc__

    def _height_and_width(self):
        from blessed.terminal import WINSZ
        return WINSZ(ws_row=self.rows, ws_col=self.columns,
                     ws_xpixel=None, ws_ypixel=None)
    _height_and_width.__doc__ = BlessedTerminal._height_and_width.__doc__

    def padd(self, text):
        from blessed.sequences import Sequence
        return Sequence(text, self).padd()

    @property
    def is_a_tty(self):
        return True


def translate_ttype(ttype):
    from x84.bbs.ini import CFG
    log = logging.getLogger(__name__)

    termcap_unknown = CFG.get('system', 'termcap-unknown')
    termcap_ansi = CFG.get('system', 'termcap-ansi')

    if termcap_unknown != 'no' and ttype == 'unknown':
        log.debug("terminal-type {0!r} => {1!r}"
                  .format(ttype, termcap_unknown))
        return termcap_unknown

    elif termcap_ansi != 'no' and ttype.lower().startswith('ansi'):
        log.debug("terminal-type {0!r} => {1!r}"
                  .format(ttype, termcap_ansi))
        return termcap_ansi

    log.info("terminal type is {0!r}".format(ttype))
    return ttype


def determine_encoding(env):
    """
    Determine and return preferred encoding given session env.
    """
    from x84.bbs import get_ini
    default_encoding = get_ini(section='session',
                               key='default_encoding'
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
    env['TERM'] = translate_ttype(env.get('TERM', 'unknown'))
    env['encoding'] = determine_encoding(env)
    return Terminal(kind=env['TERM'],
                    stream=IPCStream(writer=writer),
                    rows=int(env.get('LINES', '24')),
                    columns=int(env.get('COLUMNS', '80')))


class TerminalProcess(object):

    """
    Class record for tracking global processes and their
    various attributes. These are stored using register_tty()
    and unregister_tty(), and retrieved using terminals().
    """

    def __init__(self, client, sid, master_pipes):
        from x84.bbs.ini import CFG
        self.client = client
        self.sid = sid
        (self.master_write, self.master_read) = master_pipes
        self.timeout = CFG.getint('system', 'timeout')


def flush_queue(queue):
    """
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
    """
    Register a global instance of TerminalProcess
    """
    log = logging.getLogger(__name__)
    log.debug('[{tty.sid}] registered tty'.format(tty=tty))
    TERMINALS[tty.sid] = tty


def unregister_tty(tty):
    """
    Unregister a Terminal, described by its Client,
    input and output Queues, and Lock.
    """
    try:
        flush_queue(tty.master_read)
        tty.master_read.close()
        tty.master_write.close()
    except (EOFError, IOError) as err:
        log.exception(err)
    if tty.client.active:
        # signal tcp socket to close
        tty.client.deactivate()
    del TERMINALS[tty.sid]


def get_terminals():
    """
    Returns a list of tuples (session-id, ttys).
    """
    return TERMINALS.items()


def find_tty(client):
    """
    Given a client, return a matching tty, or None if not registered.
    """
    try:
        return next(tty for _, tty in get_terminals() if client == tty.client)
    except StopIteration:
        pass


def kill_session(client, reason='killed'):
    """
    Given a client, shutdown its socket and signal subprocess exit.
    """
    from x84.bbs.exception import Disconnected
    from x84.terminal import unregister_tty
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
    A multiprocessing.Process target. Arguments:
        sid: string describing session source (fe. IP address & Port)
        env: dictionary of client environment variables (requires 'TERM')
        CFG: ConfigParser instance of bbs configuration
        child_pipes: tuple of (writer, reader) for the engine IPC.
        kind: what kind of connection? 'telnet', 'ssh', etc.,
        addrport: tuple of (client-ip, client-port)
        matrix_args: optional positional arguments to pass to matrix script.
        matrix_kwargs: optional keyward arguments to pass to matrix script.
    """
    import x84.bbs.ini
    from x84.bbs.ipc import make_root_logger
    from x84.bbs.session import Session

    # CFG must be pickled and sent to child process; on windows systems,
    # fork() does not duplicate that it has been initialized, and requires
    # sending to child process
    x84.bbs.ini.CFG = CFG

    (writer, reader) = child_pipes

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
        except IOError, err:
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
    On a NAWS event, check if client is yet registered in registry and send
    the input event queue a 'refresh' event.

    This is the same thing as ^L to the 'userland', but should indicate also
    that a new window size is read in interfaces where they may be changed
    accordingly.
    """
    for _sid, tty in get_terminals():
        if client == tty.client:
            columns = int(client.env['COLUMNS'])
            rows = int(client.env['LINES'])
            tty.master_write.send(('refresh', ('resize', (columns, rows),)))
            break
    return True
