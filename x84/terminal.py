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

    def padd(self, text):
        from blessed.sequences import Sequence
        return Sequence(text, self).padd()

    @property
    def is_a_tty(self):
        return True


def init_term(out_queue, lock, env):
    """
    curses is initialized using the value of 'TERM' of dictionary env,
    as well as a starting window size of 'LINES' and 'COLUMNS'.

    A blessings-abstracted curses terminal is returned.
    """
    from x84.bbs.ini import CFG
    from x84.bbs.ipc import IPCStream
    log = logging.getLogger()
    ttype = env.get('TERM', 'unknown')
    if (ttype == 'ansi'
            and CFG.getBool('system', 'termcap-ansi') != 'no'):
        # special workaround for systems with 'ansi-bbs' termcap,
        # translate 'ansi' -> 'ansi-bbs'
        # http://wiki.synchro.net/install:nix?s[]=termcap#terminal_capabilities
        env['TERM'] = CFG.get('system', 'termcap-ansi')
        log.debug('TERM %s transliterated to %s' % ( ttype, env['TERM'],))
    elif (ttype == 'unknown'
            and CFG.get('system', 'termcap-unknown') != 'no'):
        # instead of using 'unknown' as a termcap definition, try to use
        # the most broadly capable termcap possible, 'vt100', configurable with
        # default.ini
        env['TERM'] = CFG.get('system', 'termcap-unknown')
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
    various attributes. These are stored using register_tty()
    and unregister_tty(), and retrieved using terminals().
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
    log.debug('registered tty: %s', tty.sid)
    TERMINALS[tty.sid] = tty


def unregister_tty(tty):
    """
    Unregister a Terminal, described by its telnet.TelnetClient,
    input and output Queues, and Lock.
    """
    log = logging.getLogger(__name__)
    try:
        flush_queue(tty.oqueue)
        tty.oqueue.close()
        tty.iqueue.close()
    except (EOFError, IOError) as err:
        log.exception(err)
    if tty.client.active:
        # signal tcp socket to close
        tty.client.deactivate()
    del TERMINALS[tty.sid]
    log.debug('unregistered tty: %s', tty.sid)


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

    tty = find_tty(client)
    if tty is not None:
        tty.iqueue.send(('exception', Disconnected(reason),))
        unregister_tty(tty)


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
    from x84.bbs.ini import CFG
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
    encoding = CFG.get('session', 'default_encoding')
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
    to the 'userland', but should indicate also that a new window size is
    read in interfaces where they may be changed accordingly.
    """
    for _sid, tty in get_terminals():
        if client == tty.client:
            columns = int(client.env['COLUMNS'])
            rows = int(client.env['LINES'])
            tty.iqueue.send(('refresh', ('resize', (columns, rows),)))
            return True
