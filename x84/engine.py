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
    import warnings
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
    timeout = CFG.getint('system', 'timeout')
    timeout_ipc = CFG.getint('system', 'timeout_ipc')
    fileno_telnetd = telnetd.server_socket.fileno()
    locks = dict()

    def inactive():
        """
        Returns list of tuples (fileno, client) of telnet
        clients that have been deactivated
        """
        return [(fd, client) for (fd, client) in
                telnetd.clients.items() if not client.active]

    def lookup(client):
        """
        Given a telnet client, return a matching session
        of tuple (client, inp_queue, out_queue, lock).
        If no session matches a telnet client,
            (None, None, None, None) is returned.
        """
        for _client, inp_queue, out_queue, lock in terminals():
            if client == _client:
                return (client, inp_queue, out_queue, lock)
        return (None, None, None, None)

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
                _client, _iqueue, _oqueue, _lock = lookup(client)
                if _client is None:
                    # no session found, just de-activate this client
                    client.deactivate()
                else:
                    # signal exit to sub-process and shutdown
                    _iqueue.send(('exception', Disconnected(err)))
                    unregister(_client, _iqueue, _oqueue, _lock)

    def telnet_send(recv_list):
        """
        test all telnet clients for send(). If any are disconnected,
        signal exit to subprocess, unregister the session, and return
        recv_list pruned of their file descriptors.
        """
        for client, inp_queue, out_queue, lock in terminals():
            if client.send_ready():
                try:
                    client.socket_send()
                except Disconnected as err:
                    logger.debug('%s Disconnected: %s.',
                                 client.addrport(), err)
                    # client.sock.fileno() can raised 'bad file descriptor',
                    # so, to remove it from the recv_list, reverse match by
                    # instance saved with its FD as a key for telnetd.clients!
                    for _fd, _client in telnetd.clients.items():
                        if client == _client and _fd in recv_list:
                            recv_list.remove(_fd)
                            break
                    inp_queue.send(('exception', Disconnected(err),))
                    unregister(client, inp_queue, out_queue, lock)
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
            ConnectTelnet(client).start()
            logger.info('%s Connected.', client.addrport())
        except socket.error as err:
            logger.error('accept error %d:%s', err[0], err[1],)

    def session_send():
        """
        Test all sessions for idle timeout, and signal exit to subprocess,
        unregister the session.  Also test for data received by telnet
        client, and send to subprocess as 'input' event.
        """
        @timeout_alarm(timeout_ipc, False)
        def send_input(client, inp_queue, lock):
            inp = client.get_input()
            inp_queue.send(('input', inp))
            return True

        # accept session event i/o, such as output
        for client, inp_queue, out_queue, lock in terminals():
            # poll about and kick off idle users
            if client.idle() > timeout:
                err = 'timeout: %ds' % (client.idle())
                inp_queue.send(('exception', Disconnected(err)))
                continue
            elif client.input_ready():
                if not send_input(client, inp_queue, lock):
                    warnings.warn('%s input buffer exceeded',
                            client.addrport())

    def session_recv(fds):
        """
        receive data waiting for session; all data received from
        subprocess is in form (event, data), and is handled by ipc_recv.
        """
        def handle_lock(iqueue, event, data):
            """
            handle locking event on iqueue of (lock-key, (method, stale))
            """
            method, stale = data
            if method == 'acquire':
                if not event in locks:
                    locks[event] = time.time()
                    logger.debug('%r granted.', (event, data))
                    iqueue.send((event, True,))
                elif (stale is not None
                        and time.time() - locks[event] > stale):
                    logger.error('%r stale.', (event, data))
                    iqueue.send((event, True,))
                else:
                    logger.warn('%r failed.', (event, data))
                    iqueue.send((event, False,))
            elif method == 'release':
                if not event in locks:
                    logger.error('%r failed.', (event, data))
                else:
                    del locks[event]
                    logger.debug('%r removed.', (event, data))

        def read_ipc(client, iqueue, oqueue, lock):
            """
            handle all events of form (event, data)
            """
            disp_handle = lambda handle: ((handle + u' ')
                    if handle is not None and 0 != len(handle)
                    else u'')
            while oqueue.poll():
                try:
                    event, data = oqueue.recv()
                except (EOFError, IOError) as err:
                    # sub-process unexpectedly closed
                    logger.exception(err)
                    unregister(client, iqueue, oqueue, lock)
                    return
                if event == 'exit':
                    unregister(client, iqueue, oqueue, lock)
                    return
                elif event == 'logger':
                    # prefix message with 'ip:port/nick '
                    data.msg = '%s[%s] %s' % (
                            disp_handle(data.handle),
                            client.addrport(),
                            data.msg)
                    logger.handle(data)

                elif event == 'output':
                    client.send_unicode(ucs=data[0], encoding=data[1])

                elif event == 'remote-disconnect':
                    send_event, send_val = data[1], data[2:]
                    for _client, _iqueue, _oqueue, _lock in terminals():
                        if data[0] == _client.addrport():
                            _iqueue.send(('exception',
                                Disconnected('disconnected by %s' % (
                                    client.addrport(),)),))
                            unregister(_client, _iqueue, _oqueue, _lock)
                            break

                elif event == 'route':
                    logger.debug('route %r', (event, data))
                    for _client, _iqueue, _oqueue, _lock in terminals():
                        if data[0] == _client.addrport():
                            send_event, send_val = data[1], data[2:]
                            if not _lock.acquire(False):
                                logger.warn('%s block route',
                                        client.addrport())
                            else:
                                _iqueue.send((send_event, send_val))
                                _lock.release()
                            break

                elif event == 'global':
                    logger.debug('broadcast %r', (event, data))
                    for _client, _iqueue, _oqueue, _lock in terminals():
                        if client != _client:
                            if not _lock.acquire(False):
                                logger.warn('%s block broadcast',
                                        client.addrport())
                            else:
                                _iqueue.send((event, data,))
                                _lock.release()

                elif event.startswith('db'):
                    # db query-> database dictionary method,
                    # spawn thread; callback by matching ('db-*',) event.
                    thread = DBHandler(iqueue, event, data)
                    thread.start()

                elif event.startswith('lock'):
                    # fine-grained lock acquire and release
                    handle_lock(iqueue, event, data)

                else:
                    assert False, 'unhandled %r' % ((event, data),)

        for client, inp_queue, out_queue, lock in terminals():
            if out_queue.fileno() in fds:
                read_ipc(client, inp_queue, out_queue, lock)


    # main event loop
    while True:
        # shutdown, close & delete inactive sockets,
        for fileno, client in inactive()[:]:
            logger.debug('close %s', telnetd.clients[fileno].addrport(),)
            try:
                client.sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            client.sock.close()
            # signal the sub-process to close.
            for _client, _iqueue, _oqueue, _lock in terminals():
                if client == _client:
                    _iqueue.send(('exception', Disconnected('deactivated')))
            del telnetd.clients[fileno]

        # poll for: new connections,
        #           telnet client input,
        #           session IPC input,
        # pylint: disable=W0612
        #        Unused variable 'lock'
        client_fds = [fileno_telnetd] + telnetd.clients.keys()

        # send, pruning list of any clients d/c during activity
        client_fds = telnet_send(client_fds)
        session_fds = [oqueue.fileno()
                for client, iqueue, oqueue, lock in terminals()]

        # poll for recv,
        ready_read = list()
        try:
            ready_read.extend(
                    select.select(client_fds + session_fds, [], [], 0.1)[0])
        except select.error as err:
            logger.exception(err)

        if fileno_telnetd in ready_read:
            accept()

        # recv telnet,
        telnet_recv(ready_read)

        # recv session ev,
        session_recv(ready_read)

        # send session ev,
        session_send()

def timeout_alarm(timeout_time, default):
    # http://pguides.net/python-tutorial/python-timeout-a-function/
    import signal
    class TimeoutException(Exception):
        pass
    def timeout_function(f, *args):
        def f2(*args):
            def timeout_handler(signum, frame):
                raise TimeoutException()
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_time)
            try:
                retval = f(*args)
            except TimeoutException:
                return default
            finally:
                signal.signal(signal.SIGALRM, old_handler)
            signal.alarm(0)
            return retval
        return f2
    return timeout_function


if __name__ == '__main__':
    exit(main())
