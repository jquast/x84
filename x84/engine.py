#!/usr/bin/env python
"""
Command-line launcher and main event loop for x/84
"""
# Please place _ALL_ Metadata in setup.py, except for a few bits
# which don't belong there right here. Don't include metadata in
# any other part of x/84, its a pita to maintain.
__author__ = "Johannes Lundberg, Jeffrey Quast"
__url__ = u'https://github.com/jquast/x84/'
__copyright__ = "Copyright 2012"
__credits__ = ["Wijnand Modderman-Lenstra", "zipe", "spidy", "Mercyful Fate"]
__license__ = 'ISC'


def main():
    """
    x84 main entry point. The system begins and ends here.

    Command line arguments to engine.py:
      --config= location of alternate configuration file
      --logger= location of alternate logging.ini file
    """
    # pylint: disable=R0914
    #        Too many local variables (19/15)
    import getopt
    import sys
    import os

    from x84.terminal import on_naws
    import x84.bbs.ini
    from x84.telnet import TelnetServer

    lookup_bbs = ('/etc/x84/default.ini',
                  os.path.expanduser('~/.x84/default.ini'))
    lookup_log = ('/etc/x84/logging.ini',
                  os.path.expanduser('~/.x84/logging.ini'))
    try:
        opts, tail = getopt.getopt(sys.argv[1:], u'', (
            'config=', 'logger=', 'help'))
    except getopt.GetoptError as err:
        sys.stderr.write('%s\n' % (err,))
        return 1
    for opt, arg in opts:
        if opt in ('--config',):
            lookup_bbs = (arg,)
        elif opt in ('--logger',):
            lookup_log = (arg,)
        elif opt in ('--help',):
            sys.stderr.write('Usage: \n%s [--config <filepath>] '
                             '[--logger <filepath>]\n' % (
                                 os.path.basename(sys.argv[0],)))
            sys.exit(1)
    if len(tail):
        sys.stderr.write('Unrecognized program arguments: %s\n' % (tail,))

    # load/create .ini files
    x84.bbs.ini.init(lookup_bbs, lookup_log)

    # init userbase pw encryption
    import x84.bbs.userbase
    x84.bbs.userbase.digestpw_init(
        x84.bbs.ini.CFG.get('system', 'password_digest'))

    # start telnet server
    telnetd = TelnetServer((
        x84.bbs.ini.CFG.get('telnet', 'addr'),
        x84.bbs.ini.CFG.getint('telnet', 'port'),),
        on_naws)

    # begin main event loop
    _loop(telnetd)


def _loop(telnetd):
    """
    Main event loop. Never returns.
    """
    # pylint: disable=R0912,R0914,R0915
    #         Too many local variables (24/15)
    import logging
    import select
    import socket
    import time
    import sys

    from x84.bbs.exception import Disconnected
    from x84.terminal import terminals, ConnectTelnet, unregister
    from x84.bbs.ini import CFG
    from x84.telnet import TelnetClient
    from x84.db import DBHandler

    logger = logging.getLogger()

    if sys.maxunicode == 65535:
        logger.warn('Python not built with wide unicode support!')
    logger.info('listening %s/tcp', telnetd.port)
    timeout_ipc = CFG.getint('system', 'timeout_ipc')
    fileno_telnetd = telnetd.server_socket.fileno()
    locks = dict()

    def lookup(client):
        """
        Given a telnet client, return a matching session
        of tuple (client, inp_queue, out_queue, lock).
        If no session matches a telnet client,
            (None, None, None, None) is returned.
        """
        for _sid, tty in terminals():
            if client == tty.client:
                return tty
        return None

    def telnet_recv(fds):
        """
        test all telnet clients with file descriptors in list fds for
        recv(). If any are disconnected, signal exit to subprocess,
        unregister the session (if any).
        """
        # read in any telnet input
        for client in (clt for (fno, clt) in telnetd.clients.iteritems()
                       if fno in fds):
            try:
                client.socket_recv()
            except Disconnected as err:
                logger.info('%s Connection Closed: %s.',
                            client.addrport(), err)
                tty = lookup(client)
                if tty is None:
                    # no session found, just de-activate this client
                    client.deactivate()
                else:
                    # signal exit to sub-process and shutdown
                    send_event, send_data = 'exception', Disconnected(err)
                    tty.iqueue.send((send_event, send_data))
                    unregister(tty)

    def telnet_send(recv_list):
        """
        test all telnet clients for send(). If any are disconnected,
        signal exit to subprocess, unregister the session, and return
        recv_list pruned of their file descriptors.
        """
        for sid, tty in terminals():
            if tty.client.send_ready():
                try:
                    tty.client.socket_send()
                except Disconnected as err:
                    logger.debug('%s Disconnected: %s.', sid, err)
                    # client.sock.fileno() can raised 'bad file descriptor',
                    # so, to remove it from the recv_list, reverse match by
                    # instance saved with its FD as a key for telnetd.clients!
                    for _fd, _client in telnetd.clients.items():
                        if tty.client == _client:
                            if _fd in recv_list:
                                recv_list.remove(_fd)
                            break
                    send_event, send_data = 'exception', Disconnected(err)
                    tty.iqueue.send((send_event, send_data,))
                    unregister(tty)
        return recv_list

    def accept():
        """
        accept new connection from telnetd.server_socket, and
        instantiate a new TelnetClient, registering it with
        dictionary telnetd.clients, and spawning an unmanaged
        thread for negotiating TERM.
        """
        try:
            sock, address_pair = telnetd.server_socket.accept()
            # busy signal
            if telnetd.client_count() > telnetd.MAX_CONNECTIONS:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except socket.error:
                    pass
                sock.close()
                logger.error('refused new connect; maximum reached.')
                return
            client = TelnetClient(sock, address_pair, telnetd.on_naws)
            telnetd.clients[client.sock.fileno()] = client
            # spawn negotiation and process registration thread
            ConnectTelnet(client).start()
            logger.info('%s Connected.', client.addrport())
        except socket.error as err:
            logger.error('accept error %d:%s', err[0], err[1],)

    @timeout_alarm(timeout_ipc, False)   # REMOVEME
    def f_send_event(iqueue, event, data):
        """
        Send event to subprocess, signaling an alarm timeout if blocked.
        """
        iqueue.send((event, data))
        return True

    def send_input(client, iqueue):
        """
        Send tcp input to subprocess as 'input' event,
        signaling an alarm timeout and re-buffering input if blocked.

        The reasons for the input buffer to block are vaugue
        """
        inp = client.get_input()
        retval = f_send_event(iqueue, 'input', inp)
        # if timeout occured, re-buffer input
        if not retval:
            client.recv_buffer.fromstring(inp)
        return retval

    def session_send():
        """
        Test all sessions for idle timeout, and signal exit to subprocess,
        unregister the session.  Also test for data received by telnet
        client, and send to subprocess as 'input' event.
        """
        # accept session event i/o, such as output
        for sid, tty in terminals():
            # poll about and kick off idle users
            if tty.timeout and tty.client.idle() > tty.timeout:
                send_event = 'exception'
                send_data = Disconnected('timeout: %ds' % (tty.client.idle()))
                tty.iqueue.send((send_event, send_data))
                continue
            elif tty.client.input_ready():
                # input buffered on tcp socket, attempt to send to client
                # with a signal alarm timeout; raising a warning if exceeded.
                if not send_input(tty.client, tty.iqueue):
                    logger.warn('%s input buffer exceeded', sid)
                    tty.client.deactivate()

    def handle_lock(tty, event, data):
        """
        handle locking event of (lock-key, (method, stale))
        """
        method, stale = data
        if method == 'acquire':
            if event in locks:
                # lock already held; check for and display owner, or
                # acquire a lock from a now-deceased session.
                held=False
                for _sid, _tty in terminals():
                    if _sid == locks[event][1] and _sid != tty.sid:
                        logger.debug('[%s] %r not acquired, held by %s.',
                                tty.sid, (event, data), _sid)
                        held=_sid
                        break
                if held is not False:
                    logger.debug('[%s] %r discovered stale lock, previously '
                            'held by %s.', tty.sid, (event, data), held)
                    del locks[event]
            if not event in locks:
                locks[event] = (time.time(), tty.sid)
                tty.iqueue.send((event, True,))
                logger.debug('[%s] %r granted.',
                             tty.sid, (event, data))
            else:
                # caller signals this kind of thread is short-lived, and any
                # existing lock older than 'stale' should be released.
                if (stale is not None
                        and time.time() - locks[event][0] > stale):
                    tty.iqueue.send((event, True,))
                    locks[event] = (time.time(), tty.sid)
                    logger.warn('[%s] %r stale %fs.',
                                tty.sid, (event, data),
                                time.time() - locks[event][0])
                # signal busy with matching event, data=False
                else:
                    tty.iqueue.send((event, False,))
                    logger.debug('[%s] %r not acquired.',
                            tty.sid, (event, data))
        elif method == 'release':
            if not event in locks:
                logger.error('[%s] %r failed: no match',
                             tty.sid, (event, data))
            else:
                del locks[event]
                logger.debug('[%s] %r removed.',
                             tty.sid, (event, data))

    def session_recv(fds):
        """
        receive data waiting for session; all data received from
        subprocess is in form (event, data), and is handled by ipc_recv.

        if stale is not None, elapsed time lock was held to consider stale
        and acquire anyway. no actual locks are held or released, just a
        simple dictionary state/time tracking system.
        """

        disp_handle = lambda handle: ((handle + u' ')
                                      if handle is not None
                                      and 0 != len(handle) else u'')
        disp_origin = lambda client: client.addrport().split(':', 1)[0]

        for sid, tty in terminals():
            while tty.oqueue.fileno() in fds and tty.oqueue.poll():
                # receive data from pipe, unregister if any error,
                try:
                    event, data = tty.oqueue.recv()
                except (EOFError, IOError) as err:
                    # sub-process unexpectedly closed
                    logger.exception(err)
                    unregister(tty)
                    return
                # 'exit' event, unregisters client
                if event == 'exit':
                    unregister(tty)
                    return
                # 'logger' event, propogated upward
                elif event == 'logger':
                    # prefix message with 'ip:port/nick '
                    data.msg = '%s[%s] %s' % (
                        disp_handle(data.handle),
                        disp_origin(tty.client),
                        data.msg)
                    logger.handle(data)
                # 'output' event, buffer for tcp socket
                elif event == 'output':
                    tty.client.send_unicode(ucs=data[0], encoding=data[1])
                # 'remote-disconnect' event, hunt and destroy
                elif event == 'remote-disconnect':
                    send_to = data[0]
                    for _sid, _tty in terminals():
                        if send_to == _sid:
                            send_event = 'exception'
                            send_val = Disconnected(
                                'remote-disconnect by %s' % (sid,))
                            tty.iqueue.send((send_event, send_val))
                            unregister(tty)
                            break
                # 'route': message passing directly from one session to another
                elif event == 'route':
                    logger.debug('route %r', (event, data))
                    tgt_sid, send_event, send_val = data[0], data[1], data[2:]
                    for _sid, _tty in terminals():
                        if tgt_sid == _sid:
                            _tty.iqueue.send((send_event, send_val))
                            break
                # 'global': message broadcasting to all sessions
                elif event == 'global':
                    logger.debug('broadcast %r', (event, data))
                    for _sid, _tty in terminals():
                        if sid != _sid:
                            _tty.iqueue.send((event, data,))
                # 'set-timeout': set user-preferred timeout
                elif event == 'set-timeout':
                    logger.debug('set-timeout %d', data)
                    tty.timeout = data
                # 'db*': access DBProxy API for shared sqlitedict
                elif event.startswith('db'):
                    thread = DBHandler(tty.iqueue, event, data)
                    thread.start()
                # 'lock': access fine-grained bbs-global locking
                elif event.startswith('lock'):
                    handle_lock(tty, event, data)
                else:
                    assert False, 'unhandled %r' % ((event, data),)

    #
    # main event loop
    #
    while True:

        # shutdown, close & delete inactive sockets,
        for fileno, client in [(_fno, _client)
                               for (_fno, _client) in telnetd.clients.items()
                               if not _client.active]:
            logger.info('close %s', telnetd.clients[fileno].addrport(),)
            try:
                client.sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            client.sock.close()

            # signal exit to any matching session
            for _sid, tty in terminals():
                if client == tty.client:
                    send_event = 'exception'
                    send_data = Disconnected('deactivated')
                    tty.iqueue.send((send_event, send_data,))
                    break

            # unregister
            del telnetd.clients[fileno]

        # send tcp data, pruning list of any clients d/c during activity
        fds = telnet_send([fileno_telnetd] + telnetd.clients.keys())

        # extend fd list with all session Pipes
        fds.extend([tty.oqueue.fileno() for _sid, tty in terminals()])

        try:
            fds = select.select(fds, [], [], 0.1)[0]
        except select.error as err:
            logger.exception(err)
            fds = list()

        if fileno_telnetd in fds:
            accept()

        # recv telnet data,
        telnet_recv(fds)

        # recv and handle session events,
        session_recv(fds)

        # send any session input data, poll timeout
        session_send()


def timeout_alarm(timeout_time, default):
    """
    Call a function using signal handler, return False if it did not
    return within duration of ``timeout_time``.

    http://pguides.net/python-tutorial/python-timeout-a-function/
    """
    import signal

    class TimeoutException(Exception):
        """ Exception thrown when alarm is caught. """
        pass

    # pylint: disable=W0613
    #         Unused argument 'args'
    def timeout_function(func, *args):
        """ decorator """
        def func2(*args):
            """ function wrapper for decorator """
            def timeout_handler(_signum, _frame):
                """ Raises timeout exception. """
                raise TimeoutException()
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_time)
            try:
                retval = func(*args)
            except TimeoutException:
                return default
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return func2
    return timeout_function


if __name__ == '__main__':
    exit(main())
