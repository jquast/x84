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
    timeout = CFG.getint('system', 'timeout')
    fileno_telnetd = telnetd.server_socket.fileno()
    locks = dict()

    def inactive():
        """
        Returns list of tuples (fileno, client) of telnet
        clients that have been deactivated
        """
        return [(fno, clt) for (fno, clt) in
                telnetd.clients.items() if not clt.active]

    def lookup(client):
        """
        Given a telnet client, return a matching session
        of tuple (client, pipe, lock).  If no session matches
        a telnet client, (None, None, None) is returned.
        """
        for o_client, pipe, lock in terminals():
            if o_client == client:
                return (client, pipe, lock)
        return (None, None, None)

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
                o_client, pipe, lock = lookup(client)
                if o_client is not None:
                    pipe.send(('exception', Disconnected(err)))
                    unregister(client, pipe, lock)
                else:
                    client.deactivate()

    def telnet_send(recv_list):
        """
        test all telnet clients for send(). If any are disconnected,
        signal exit to subprocess, unregister the session, and return
        recv_list pruned of their file descriptors.
        """
        for client, pipe, lock in terminals():
            if client.send_ready():
                try:
                    client.socket_send()
                except Disconnected as err:
                    logger.debug('%s Disconnected: %s.',
                                 client.addrport(), err)
                    # client.sock.fileno() can raised 'bad file descriptor',
                    # so, to remove it from the recv_list, reverse match by
                    # instance saved with its FD as a key for telnetd.clients!
                    for o_fd, clt in telnetd.clients.items():
                        if client == clt and o_fd in recv_list:
                            recv_list.remove(o_fd)
                            break
                    pipe.send(('exception', Disconnected(err),))
                    unregister(client, pipe, lock)
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
            if telnetd.client_count() > telnetd.MAX_CONNECTIONS:
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
        # accept session event i/o, such as output
        for client, pipe, lock in terminals():
            # poll about and kick off idle users
            if client.idle() > timeout:
                err = 'Timeout: %ds' % (client.idle())
                pipe.send(('exception', Disconnected(err)))
                unregister(client, pipe, lock)
                continue

            # send input to subprocess,
            if client.input_ready() and lock.acquire(False):
                inp = client.get_input()
                pipe.send(('input', inp,))
                lock.release()

    def session_recv(fds):
        """
        receive data waiting for session pipe filenos in fds.
        all data received from subprocess is in form (event, data),
        and is handled by ipc_recv.
        """
        def handle_lock(pipe, event, data):
            """
            handle locking event on pipe of (lock-key, (method, stale))
            """
            method, stale = data
            if method == 'acquire':
                if not event in locks:
                    locks[event] = time.time()
                    logger.debug('%r granted.', (event, data))
                    pipe.send((event, True,))
                elif (stale is not None
                        and time.time() - locks[event] > stale):
                    logger.error('%r stale.', (event, data))
                    pipe.send((event, True,))
                else:
                    logger.warn('%r failed.', (event, data))
                    pipe.send((event, False,))
            elif method == 'release':
                if not event in locks:
                    logger.error('%r failed.', (event, data))
                else:
                    del locks[event]
                    logger.debug('%r removed.', (event, data))

        def read_ipc(client, pipe, lock):
            """
            handle all events of form (event, data)
            """
            has_data = lambda pipe: bool(len(select.select(
                [pipe.fileno()], [], [], 0)[0]))
            disp_handle = lambda handle: ((handle + u' ')
                    if handle is not None and 0 != len(handle)
                    else u'')
            while True:
                try:
                    event, data = pipe.recv()
                except (EOFError, IOError) as err:
                    # issue with pipe; sub-process unexpectedly closed
                    logger.exception(err)
                    pipe.send(('exception', Disconnected('%s' % (err,)),))
                    unregister(client, pipe, lock)
                    return

                if event == 'exit':
                    unregister(client, pipe, lock)
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
                    for o_client, o_pipe, o_lock in terminals():
                        if o_client.addrport() == data[0]:
                            send_event, send_val = data[1], data[2:]
                            pipe.send(('exception',
                                Disconnected('disconnected by %s' % (
                                    client.addrport(),)),))
                            unregister(client, pipe, lock)
                            break

                elif event == 'route':
                    logger.debug('route %r', (event, data))
                    for o_client, o_pipe, o_lock in terminals():
                        if o_client.addrport() == data[0]:
                            send_event, send_val = data[1], data[2:]
                            if not o_lock.acquire(False):
                                logger.warn('%s is blocking route',
                                        client.addrport())
                            else:
                                o_pipe.send((send_event, send_val))
                                o_lock.release()
                            break

                elif event == 'global':
                    logger.debug('broadcast %r', (event, data))
                    for o_client, o_pipe, o_lock in terminals():
                        if o_client != client:
                            if not o_lock.acquire(False):
                                logger.warn('%s is blocking broadcast',
                                        client.addrport())
                            else:
                                o_pipe.send((event, data,))
                                o_lock.release()

                elif event.startswith('db'):
                    # db query-> database dictionary method,
                    # spawn thread; callback by matching ('db-*',) event.
                    thread = DBHandler(pipe, event, data)
                    thread.start()

                elif event.startswith('lock'):
                    # fine-grained lock acquire and release
                    handle_lock(pipe, event, data)

                else:
                    assert False, 'unhandled %r' % ((event, data),)

                try:
                    if not has_data(pipe):
                        return
                except IOError:
                    return
        for client, pipe, lock in terminals():
            if pipe.fileno() in fds:
                read_ipc(client, pipe, lock)

    # main event loop
    while True:
        # close & delete inactive sockets,
        for fileno, client in inactive()[:]:
            logger.debug('close %s', telnetd.clients[fileno].addrport(),)
            client.sock.close()
            del telnetd.clients[fileno]

        # poll for: new connections,
        #           telnet client input,
        #           session IPC input,
        # pylint: disable=W0612
        #        Unused variable 'lock'
        client_fds = set([fileno_telnetd] + telnetd.clients.keys() +
                        [pipe.fileno() for client, pipe, lock in terminals()])

        # send, pruning list of any clients d/c during activity
        client_fds = telnet_send(client_fds)

        # poll for recv,
        ready_read = list()
        try:
            ready_read.extend(select.select(client_fds, [], [], 1)[0])
        except select.error as err:
            logger.exception(err)

        if fileno_telnetd in ready_read:
            accept()

        # recv telnet,
        telnet_recv(ready_read)
        # send session ev,
        session_send()
        # recv session ev,
        session_recv(ready_read)

if __name__ == '__main__':
    exit(main())
