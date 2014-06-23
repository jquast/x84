#!/usr/bin/env python
"""
Command-line launcher and main event loop for x/84
"""
# Please place _ALL_ Metadata in setup.py, and any that don't belong there,
# here.  Except for a few bits which don't belong there right here. (perhaps
# user-contributed art or scripts) -- Do not include metadata in any other
# part of x/84, its a damn pain in the ass to maintain so much meta.

__author__ = "Johannes Lundberg, Jeffrey Quast"
__url__ = u'https://github.com/jquast/x84/'
__copyright__ = "Copyright 2014"
__credits__ = [
    "Wijnand Modderman-Lenstra",
    "zipe",
    "spidy",
    "Mercyful Fate",
    "haliphax",
    "hellbeard",
]
__license__ = 'ISC'

def main():
    """
    x84 main entry point. The system begins and ends here.

    Command line arguments to engine.py:
      --config= location of alternate configuration file
      --logger= location of alternate logging.ini file
    """
    import x84.bbs.ini
    from x84.bbs.userbase import digestpw_init

    # load existing .ini files or create default ones.
    x84.bbs.ini.init(*parse_args())
    from x84.bbs.ini import CFG

    # initialize selected encryption scheme
    digestpw_init(CFG.get('system', 'password_digest'))

    # retrieve enabled servers
    servers = get_servers(CFG)

    try:
        # begin main event loop
        _loop(servers)
    except KeyboardInterrupt:
        # exit on ^C, killing any client sessions.
        from x84.terminal import kill_session
        for server in servers:
            for key, client in server.clients.items()[:]:
                kill_session(client, 'server shutdown')
                del server.clients[key]

def parse_args():
    import getopt
    import sys
    import os

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
        sys.exit(1)
    return (lookup_bbs, lookup_log)

def get_servers(CFG):
    """
    Given a configuration file, instantiate and return a list of enabled
    servers.
    """
    from x84.terminal import on_naws
    from x84.telnet import TelnetServer
    from x84.ssh import SshServer

    servers = []

    # start telnet server
    if CFG.has_section('telnet'):
        telnetd = TelnetServer(config=CFG, on_naws=on_naws)
        servers.append(telnetd)

    # start ssh server
    if CFG.has_section('ssh'):
        sshd = SshServer(config=CFG)
        servers.append(sshd)

    return servers

def find_server(servers, fd):
    from x84.telnet import TelnetServer
    from x84.ssh import SshServer
    for server in servers:
        if fd == server.server_socket.fileno():
            return server

def accept_server(server, log):
    """
    Given a server awaiting a new connection, call the accept() function with
    the appropriate arguments for client_factory, connect_factory, and any
    optional kwargs.
    """
    from x84.telnet import TelnetServer, TelnetClient, ConnectTelnet
    from x84.ssh import SshServer, SshClient, ConnectSsh
    if server.__class__ == TelnetServer:
        accept(log=log, server=server,
               client_factory=TelnetClient,
               connect_factory=ConnectTelnet,
               client_factory_kwargs={
                   'on_naws': server.on_naws})
    elif server.__class__ == SshServer:
        accept(log=log, server=server,
               client_factory=SshClient,
               connect_factory=ConnectSsh,
               connect_factory_kwargs={
                   'server_host_key': server.host_key})
    else:
        raise NotImplementedError(
            "No accept for server class {server.__class__.__name__}"
            .format(server=server))


def accept(log, server, client_factory, connect_factory,
           client_factory_kwargs=None, connect_factory_kwargs=None):
    """
    accept new connection from server.server_socket,
    instantiate a new instance of client_factory,
    registering it with dictionary server.clients,
    spawning an unmanaged thread using connect_factory.
    """
    import socket
    client_factory_kwargs = client_factory_kwargs or {}
    connect_factory_kwargs = connect_factory_kwargs or {}
    try:
        sock, address_pair = server.server_socket.accept()
        # busy signal
        if server.client_count() > server.MAX_CONNECTIONS:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            sock.close()
            log.error('refused new connect; maximum reached.')
            return
        client = client_factory(sock, address_pair, **client_factory_kwargs)
        server.clients[client.sock.fileno()] = client

        # spawn negotiation and process registration thread
        connect_factory(client, **connect_factory_kwargs).start()
        log.info('{0} Connected by {1}.'.format(client.addrport(),
                                                server.__class__.__name__))

    except socket.error as err:
        log.error('accept error %d:%s', err[0], err[1],)

def get_session_fds(servers):
    from x84.terminal import find_tty
    session_fds = []
    for server in servers:
        for client in server.clients.values():
            tty = find_tty(client)
            if tty is not None:
                session_fds.extend([tty.oqueue.fileno(), tty.iqueue.fileno()])
    return session_fds

def client_recv(servers, log):
    """
    Test all clients for recv_ready(). If any data is available, then
    socket_recv() is called, buffering the data for the session which
    is exhausted in session_send().
    """
    from x84.bbs.exception import Disconnected
    from x84.terminal import kill_session
    for server in servers:
        for client in server.clients.values():
            if client.recv_ready():
                try:
                    client.socket_recv()
                except Disconnected as err:
                    log.info('%s Disconnected: %s.', client.addrport(), err)
                    kill_session(client, 'disconnected on recv')

def client_send(terminals, log):
    """
    Test all clients for send_ready(). If any data is available, then
    tty.client.send() is called. This is data sent from the session to
    the tcp client.
    """
    from x84.bbs.exception import Disconnected
    from x84.terminal import kill_session
    # nothing to send until tty is registered.
    for sid, tty in terminals[:]:
        if tty.client.send_ready():
            try:
                tty.client.send()
            except Disconnected as err:
                log.info('%s Disconnected: %s.', sid, err)
                kill_session(tty.client, 'disconnected on send')

def session_send(terminals):
    """
    Test all tty clients for input_ready(), meaning tcp data has been
    buffered to be received by the tty session, and sent it to the tty
    input queue (tty.iqueue).

    Also, test all sessions for idle timeout, signaling exit to
    subprocess when reached
    """
    from x84.terminal import kill_session
    for sid, tty in terminals:
        if tty.client.input_ready():
            tty.iqueue.send(('input', tty.client.get_input()))

        # poll about and kick off idle users
        elif tty.timeout and tty.client.idle() > tty.timeout:
            kill_session(tty.client, 'timeout')

def handle_lock(locks, tty, event, data, tap_events, log):
    """
    handle locking event of (lock-key, (method, stale))
    """
    import time
    from x84.terminal import get_terminals
    method, stale = data
    if method == 'acquire':
        if event in locks:
            # lock already held; check for and display owner, or
            # acquire a lock from a now-deceased session.
            held = False
            for _sid, _tty in get_terminals():
                if _sid == locks[event][1] and _sid != tty.sid:
                    log.debug('[%s] %r not acquired, held by %s.',
                              tty.sid, (event, data), _sid)
                    held=_sid
                    break
            if held is not False:
                log.debug('[%s] %r discovered stale lock, previously '
                          'held by %s.', tty.sid, (event, data), held)
                del locks[event]
        if not event in locks:
            locks[event] = (time.time(), tty.sid)
            tty.iqueue.send((event, True,))
            if tap_events:
                log.debug('[%s] %r granted.', tty.sid, (event, data))
        else:
            # caller signals this kind of thread is short-lived, and any
            # existing lock older than 'stale' should be released.
            if (stale is not None
                    and time.time() - locks[event][0] > stale):
                tty.iqueue.send((event, True,))
                locks[event] = (time.time(), tty.sid)
                log.warn('[%s] %r stale %fs.',
                            tty.sid, (event, data),
                            time.time() - locks[event][0])
            # signal busy with matching event, data=False
            else:
                tty.iqueue.send((event, False,))
                log.debug('[%s] %r not acquired.', tty.sid, (event, data))

    elif method == 'release':
        if not event in locks:
            log.error('[%s] %r failed: no match',
                         tty.sid, (event, data))
        else:
            del locks[event]
            if tap_events:
                log.debug('[%s] %r removed.', tty.sid, (event, data))

def session_recv(locks, terminals, log, tap_events):
    """
    receive data waiting for session; all data received from
    subprocess is in form (event, data), and is handled by ipc_recv.

    if stale is not None, the number of seconds elapsed since lock was
    first held is consider stale after that period of time, and is acquire
    anyway.
    """
    # No actual Lock instances are held or released, just a simple dictionary
    # state/time tracking system.
    from x84.terminal import unregister_tty, kill_session
    from x84.db import DBHandler

    disp_handle = lambda handle: ((handle + u' ')
                                  if handle is not None
                                  and 0 != len(handle) else u'')
    disp_origin = lambda client: client.addrport().split(':', 1)[0]

    for sid, tty in terminals:
        if tty.oqueue.poll():
            try:
                event, data = tty.oqueue.recv()
            except (EOFError, IOError) as err:
                # sub-process unexpectedly closed
                log.exception(err)
                unregister_tty(tty)
                continue

            # 'exit' event, unregisters client
            if event == 'exit':
                kill_session(tty.client, 'client exit')
                continue

            # 'logger' event, propagated upward
            elif event == 'logger':
                # prefix message with 'ip:port/nick '
                data.msg = '%s[%s] %s' % (
                    disp_handle(data.handle),
                    disp_origin(tty.client),
                    data.msg)
                log.handle(data)

            # 'output' event, buffer for tcp socket
            elif event == 'output':
                tty.client.send_unicode(ucs=data[0], encoding=data[1])

            # 'remote-disconnect' event, hunt and destroy
            elif event == 'remote-disconnect':
                send_to = data[0]
                reason = 'remote-disconnect by %s' % (sid,)
                for _sid, _tty in terminals:
                    if send_to == _sid:
                        kill_session(client, reason)
                        break

            # 'route': message passing directly from one session to another
            elif event == 'route':
                if tap_events:
                    log.debug('route %r', (event, data))
                tgt_sid, send_event, send_val = data[0], data[1], data[2:]
                for _sid, _tty in terminals:
                    if tgt_sid == _sid:
                        _tty.iqueue.send((send_event, send_val))
                        break

            # 'global': message broadcasting to all sessions
            elif event == 'global':
                if tap_events:
                    log.debug('broadcast %r', (event, data))
                for _sid, _tty in terminals:
                    if sid != _sid:
                        _tty.iqueue.send((event, data,))

            # 'set-timeout': set user-preferred timeout
            elif event == 'set-timeout':
                if tap_events:
                    log.debug('set-timeout %d', data)
                tty.timeout = data

            # 'db*': access DBProxy API for shared sqlitedict
            elif event.startswith('db'):
                thread = DBHandler(tty.iqueue, event, data)
                thread.start()

            # 'lock': access fine-grained bbs-global locking
            elif event.startswith('lock'):
                handle_lock(locks, tty, event, data, tap_events, log)

            else:
                assert False, 'unhandled %r' % ((event, data),)

def _loop(servers):
    """
    Main event loop. Never returns.
    """
    # pylint: disable=R0912,R0914,R0915
    #         Too many local variables (24/15)
    import logging
    import os
    import select
    import socket
    from x84.terminal import get_terminals, kill_session
    from x84.bbs.ini import CFG
    from x84.bbs import session
    from multiprocessing import Queue
    from threading import Lock, Condition

    log = logging.getLogger(__name__)

    if not len(servers):
        raise ValueError("No servers configured for event loop! (ssh, telnet)")

    timeout_ipc = CFG.getint('system', 'timeout_ipc')
    tap_events = CFG.getboolean('session', 'tap_events')
    locks = dict()

    # bot coordination
    if CFG.has_section('bots'):
        session.BOTQUEUE = Queue()
        session.BOTLOCK = Lock()

    # web server
    web_modules = set()

    if CFG.has_section('web'):
        try:
            import web, OpenSSL
            from x84 import webserve
            web_modules = set([key.strip() for key in CFG.get('web', 'modules').split(',')])
            webserve.start(web_modules)
        except Exception, e:
            log.error('%r' % e)

    # setup message polling mechanism
    poll_interval = None
    last_poll = None

    if CFG.has_option('msg', 'poll_interval'):
        import time
        poll_interval = CFG.getint('msg', 'poll_interval')
        last_poll = int(time.time()) - poll_interval

    while True:
        # shutdown, close & delete inactive clients,
        for server in servers:
            for key, client in server.clients.items()[:]:
                if not client.is_active():
                    kill_session(client, 'socket shutdown')
                    del server.clients[key]

        server_fds = [server.server_socket.fileno() for server in servers]
        client_fds = [fd for fd in server.client_fds() for server in servers]
        session_fds = get_session_fds(servers)
        check_r = server_fds + client_fds + session_fds

        # We'd like to use timeout 'None', but the registration of
        # a new client in terminal.start_process surprises us with new
        # file descriptors for the session i/o. unless we loop for
        # additional `session_fds', a connecting client would block.
        ready_r, _, _ = select.select(check_r, [], [], 0.15)

        for fd in ready_r:
            # see if any new tcp connections were made
            server = find_server(servers, fd)
            if server is not None:
                accept_server(server, log)

        # receive new data from tcp clients.
        client_recv(servers, log)

        # fire up message polling process if enabled
        if poll_interval is not None:
            import time
            now = int(time.time())

            if now - last_poll >= poll_interval:
                from x84.msgpoll import do_poll
                do_poll()
                last_poll = now

        terms = get_terminals()

        # receive new data from session terminals
        if set(session_fds) & set(ready_r):
            session_recv(locks, terms, log, tap_events)

        # send tcp data to clients
        client_send(terms, log)

        # send session data, poll for user-timeout and disconnect them
        session_send(terms)


if __name__ == '__main__':
    import sys
    if sys.maxunicode == 65535:
        sys.stderr.write('Python not built with wide unicode support!\n')

    exit(main())
