#!/usr/bin/env python
"""
Command-line launcher and event loop for x/84, https://github.com/jquast/x84
"""
# Place ALL metadata in setup.py, except where not suitable, place here.
# For any contributions, feel free to tag __author__ etc. at top of such file.
__author__ = "Johannes Lundberg (jojo), Jeff Quast (dingo)"
__url__ = u'https://github.com/jquast/x84/'
__copyright__ = "Copyright 2014"
__credits__ = [
    # use 'scene' names unless preferred or unavailable.
    "zipe",
    "jojo",
    "maze",
    "dingo",
    "spidy",
    "beardy",
    "haliphax",
    "megagumbo",
    "hellbeard",
    "Mercyful Fate",
]
__license__ = 'ISC'

# std
import sys
import logging

# local
__import__('encodings')  # provides alternate encodings


def main():
    """
    x84 main entry point. The system begins and ends here.

    Command line arguments to engine.py:
      --config= location of alternate configuration file
      --logger= location of alternate logging.ini file
    """
    import x84.bbs.ini

    # load existing .ini files or create default ones.
    x84.bbs.ini.init(*parse_args())
    from x84.bbs import get_ini
    from x84.bbs.ini import CFG

    if sys.maxunicode == 65535:
        # apple is the only known bastardized variant that does this;
        # presumably for memory/speed savings (UCS-2 strings are faster
        # than UCS-4).  Python 3 dynamically allocates string types by
        # their widest content, so such things aren't necessary ...
        import warnings
        warnings.warn('This python is built without wide unicode support. '
                      'some internationalized languages will not be possible.')

    # retrieve list of managed servers
    servers = get_servers(CFG)

    # begin unmanaged servers
    if (CFG.has_section('web') and
            (not CFG.has_option('web', 'enabled')
             or CFG.getboolean('web', 'enabled'))):
        # start https server for one or more web modules.
        from x84 import webserve
        webserve.main()

    # 3.0: This should be a separate section all together
    #      with an enables = yes option.
    if get_ini(section='msg', key='network_tags'):
        # start background timer to poll for new messages
        # of message networks we may be a member of.
        from x84 import msgpoll
        msgpoll.main()

    try:
        # begin main event loop
        _loop(servers)
    except KeyboardInterrupt:
        # exit on ^C, killing any client sessions.
        from x84.terminal import kill_session
        for server in servers:
            for idx, thread in enumerate(server.threads[:]):
                if not thread.stopped:
                    thread.stopped = True
                server.threads.remove(thread)
            for key, client in server.clients.items()[:]:
                kill_session(client, 'server shutdown')
                del server.clients[key]
    return 0


def parse_args():
    import getopt
    import sys
    import os

    if sys.platform.lower().startswith('win32'):
        system_path = os.path.join('C:', 'x84')
    else:
        system_path = os.path.join(os.path.sep, 'etc', 'x84')

    lookup_bbs = (os.path.join(system_path, 'default.ini'),
                  os.path.expanduser(os.path.join('~', '.x84', 'default.ini')))

    lookup_log = (os.path.join(system_path, 'logging.ini'),
                  os.path.expanduser(os.path.join('~', '.x84', 'logging.ini')))

    try:
        opts, tail = getopt.getopt(sys.argv[1:], u'', (
            'config=', 'logger=', 'help'))
    except getopt.GetoptError as err:
        sys.stderr.write('{0}\n'.format(err))
        return 1
    for opt, arg in opts:
        if opt in ('--config',):
            lookup_bbs = (arg,)
        elif opt in ('--logger',):
            lookup_log = (arg,)
        elif opt in ('--help',):
            sys.stderr.write(
                'Usage: \n'
                '{0} [--config <filepath>] [--logger <filepath>]\n'
                .format(os.path.basename(sys.argv[0])))
            sys.exit(1)
    if len(tail):
        sys.stderr.write('Unrecognized program arguments: {0}\n'
                         .format(tail))
        sys.exit(1)
    return (lookup_bbs, lookup_log)


def get_servers(CFG):
    """
    Given a configuration file, instantiate and return a list of enabled
    servers.
    """
    servers = []

    if (CFG.has_section('telnet') and
            (not CFG.has_option('telnet', 'enabled')
             or CFG.getboolean('telnet', 'enabled'))):
        # start telnet server instance
        from x84.telnet import TelnetServer
        servers.append(TelnetServer(config=CFG))

    if (CFG.has_section('ssh') and
            not CFG.has_option('ssh', 'enabled')
            or CFG.getboolean('ssh', 'enabled')):
        # start ssh server instance
        #
        # may raise an ImportError for systems where pyOpenSSL and etc. could
        # not be installed (due to any issues with missing python-dev, libffi,
        # cc, etc.).  Allow it to raise naturally, the curious user should
        # either discover and resolve the root issue, or disable ssh if it
        # cannot be resolved.
        from x84.ssh import SshServer
        servers.append(SshServer(config=CFG))

    if (CFG.has_section('rlogin') and
            (not CFG.has_option('rlogin', 'enabled')
             or CFG.getboolean('rlogin', 'enabled'))):
        # start rlogin server instance
        from x84.rlogin import RLoginServer
        servers.append(RLoginServer(config=CFG))

    return servers


def find_server(servers, fd):
    for server in servers:
        if fd == server.server_socket.fileno():
            return server


def accept(log, server, check_ban):
    """
    Accept new connection from server, spawning an unmanaged thread.

    Connecting socket accepted is server.server_socket, instantiate a
    new instance of client_factory, with optional keyword arguments
    defined by server.client_factory_kwargs, registering it with
    dictionary server.clients, and spawning an unmanaged thread
    using connect_factory, with optional keyword arguments
    server.connect_factory_kwargs.
    """
    import socket

    if None in (server.client_factory, server.connect_factory):
        raise NotImplementedError(
            "No accept for server class {server.__class__.__name__}"
            .format(server=server))

    client_factory_kwargs = server.client_factory_kwargs
    if callable(server.client_factory_kwargs):
        client_factory_kwargs = server.client_factory_kwargs(server)

    connect_factory_kwargs = server.connect_factory_kwargs
    if callable(server.connect_factory_kwargs):
        connect_factory_kwargs = server.connect_factory_kwargs(server)

    try:
        sock, address_pair = server.server_socket.accept()

        # busy signal
        if server.client_count() > server.MAX_CONNECTIONS:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            sock.close()
            log.error('{addr}: refused, maximum connections reached.'
                      .format(addr=address_pair[0]))
            return

        # connecting IP is banned
        if check_ban(address_pair[0]) is False:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass
            sock.close()
            log.error('{addr}: refused, banned.'
                      .format(addr=address_pair[0]))
            return

        # instantiate a client of this type
        client = server.client_factory(sock, address_pair,
                                       **client_factory_kwargs)

        # spawn on-connect negotiation thread.  When successful,
        # a new sub-process is spawned and registered as a session tty.
        server.clients[client.sock.fileno()] = client
        thread = server.connect_factory(client, **connect_factory_kwargs)
        log.info('{client.kind} connection from {client.addrport} '
                 '(*{thread.name}).'.format(client=client, thread=thread))
        server.threads.append(thread)
        thread.start()

    except socket.error as err:
        log.error('accept error {0}:{1}'.format(*err))


def get_session_output_fds(servers):
    from x84.terminal import find_tty
    session_fds = []
    for server in servers:
        for client in server.clients.values():
            tty = find_tty(client)
            if tty is not None:
                session_fds.append(tty.master_read.fileno())
    return session_fds


def client_recv(servers, ready_fds, log):
    """
    Test all clients for recv_ready(). If any data is available, then
    socket_recv() is called, buffering the data for the session which
    is exhausted in session_send().
    """
    from x84.bbs.exception import Disconnected
    from x84.terminal import kill_session
    for server in servers:
        for client in server.clients_ready(ready_fds):
            try:
                client.socket_recv()
            except Disconnected as err:
                log.debug('{client.addrport}: disconnect on recv: {err}'
                          .format(client=client, err=err))
                kill_session(client, 'disconnected: {err}'.format(err=err))


def client_send(terminals, log):
    """
    Test all clients for send_ready(). If any data is available, then
    tty.client.send() is called. This is data sent from the session to
    the tcp client.
    """
    from x84.bbs.exception import Disconnected
    from x84.terminal import kill_session
    # nothing to send until tty is registered.
    for sid, tty in terminals:
        if tty.client.send_ready():
            try:
                tty.client.send()
            except Disconnected as err:
                log.debug('{client.addrport}: disconnect on send: {err}'
                          .format(client=tty.client, err=err))
                kill_session(tty.client, 'disconnected: {err}'.format(err=err))


def session_send(terminals):
    """
    Test all tty clients for input_ready(), meaning tcp data has been
    buffered to be received by the tty session, and sent it to the tty
    input queue (tty.master_write).

    Also, test all sessions for idle timeout, signaling exit to
    subprocess when reached
    """
    from x84.terminal import kill_session
    for sid, tty in terminals:
        if tty.client.input_ready():
            try:
                tty.master_write.send(('input', tty.client.get_input()))
            except IOError:
                # this may happen if a sub-process crashes, or more often,
                # because the subprocess has logged off, but the user kept
                # banging the keyboard before we have had the opportunity
                # to close their telnet socket.
                kill_session(tty.client, 'no tty for socket data')

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
        # this lock is already held,
        if event in locks:
            # check if lock held by an active session,
            holder = locks[event][1]
            for _sid, _tty in get_terminals():
                if _sid == holder and _sid != tty.sid:
                    # acquire the lock from a now-deceased session.
                    log.debug('[{tty.sid}] {event} not acquired, '
                              'held by active session: {holder}'
                              .format(tty=tty, event=event, holder=holder))
                    break
                elif _sid == holder and _sid == tty.sid:
                    # acquire the lock from ourselves!  We'll allow it
                    # (this is termed, "re-entrant locking").
                    log.debug('{tty.sid}] {event} is re-acquired!'
                              .format(tty=tty, event=event))
            else:
                # lock is held by a now-defunct session, re-acquired.
                log.debug('[{tty.sid}] {event} re-acquiring stale lock, '
                          'previously held by session no longer active: '
                          '{holder}'
                          .format(tty=tty, event=event, holder=holder))
                del locks[event]

        # lock is not held, or release by previous block
        if event not in locks:
            # acknowledge its requirement,
            locks[event] = (time.time(), tty.sid)
            tty.master_write.send((event, True,))
            if tap_events:
                log.debug('[{tty.sid}] {event} granted lock.'
                          .format(tty=tty, event=event))

        # lock cannot be acquired,
        else:
            holder = locks[event][1]
            elapsed = time.time() - locks[event][0]
            if (stale is not None and elapsed > stale):
                # caller has decreed that this lock may be acquired even if
                # it already held, if it has been held longer than length of
                # time `stale`.  This is simply to prevent a global freeze
                # when the programmer knows the holder may fail to release,
                # though this is not currently used in the demonstration
                # system.
                locks[event] = (time.time(), tty.sid)
                tty.master_write.send((event, True,))
                log.warn('[{tty.sid}] {event} re-acquiring stale lock, '
                         'previously held active session {holder} after '
                         '{elapsed}s elapsed (stale={stale})'
                         .format(tty=tty, event=event, holder=holder,
                                 elapsed=elapsed, stale=stale))

            # signal busy with matching event, data=False
            else:
                tty.master_write.send((event, False,))
                log.warn('[{tty.sid}] {event} lock rejected; already held '
                         'by active session {holder} for {elapsed} seconds '
                         '(stale={stale})'
                         .format(tty=tty, event=event, holder=holder,
                                 elapsed=elapsed, stale=stale))

    elif method == 'release':
        if event not in locks:
            log.error('[{tty.sid}] {event} lock failed to release, '
                      'not acquired.'.format(tty=tty, event=event))
        else:
            del locks[event]
            if tap_events:
                log.debug('[{tty.sid}] {event} released lock.'
                          .format(tty=tty, event=event))


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
    from x84.terminal import kill_session
    from x84.db import DBHandler

    for sid, tty in terminals:
        while tty.master_read.poll():
            try:
                event, data = tty.master_read.recv()
            except (EOFError, IOError) as err:
                # sub-process unexpectedly closed
                msg_err = 'master_read pipe: {err}'.format(err=err)
                log.exception(msg_err)
                kill_session(tty.client, msg_err)
                break
            except TypeError:
                msg_err = 'unpickling error'
                log.exception(msg_err)
                break

            # 'exit' event, unregisters client
            if event == 'exit':
                kill_session(tty.client, 'client exit')
                break

            # 'logger' event, prefix log message with handle and IP address
            elif event == 'logger':
                data.msg = ('{data.handle}[{tty.sid}] {data.msg}'
                            .format(data=data, tty=tty))
                log.handle(data)

            # 'output' event, buffer for tcp socket
            elif event == 'output':
                tty.client.send_unicode(ucs=data[0], encoding=data[1])

            # 'remote-disconnect' event, hunt and destroy
            elif event == 'remote-disconnect':
                send_to = data[0]
                reason = 'remote-disconnect by {sid.tty}'.format(sid=sid)
                for _sid, _tty in terminals:
                    if send_to == _sid:
                        kill_session(tty.client, reason)
                        break

            # 'route': message passing directly from one session to another
            elif event == 'route':
                if tap_events:
                    log.debug('route {0!r}'.format(data))
                tgt_sid, send_event, send_val = data[0], data[1], data[2:]
                for _sid, _tty in terminals:
                    if tgt_sid == _sid:
                        _tty.master_write.send((send_event, send_val))
                        break

            # 'global': message broadcasting to all sessions
            elif event == 'global':
                if tap_events:
                    log.debug('broadcast: {data!r}'.format(data=data))
                for _sid, _tty in terminals:
                    if sid != _sid:
                        _tty.master_write.send((event, data,))

            # 'set-timeout': set user-preferred timeout
            elif event == 'set-timeout':
                if tap_events:
                    log.debug('[{tty.sid}] set-timeout {data}'
                              .format(tty=tty, data=data))
                tty.timeout = data

            # 'db*': access DBProxy API for shared sqlitedict
            elif event.startswith('db'):
                thread = DBHandler(tty.master_write, event, data)
                thread.start()

            # 'lock': access fine-grained bbs-global locking
            elif event.startswith('lock'):
                handle_lock(locks, tty, event, data, tap_events, log)

            else:
                log.error('[{tty.sid}] unhandled event, data: '
                          '({event}, {data})'
                          .format(tty=tty, event=event, data=data))


def _loop(servers):
    """
    Main event loop. Never returns.
    """
    # pylint: disable=R0912,R0914,R0915
    #         Too many local variables (24/15)
    import select
    import sys
    from x84.terminal import get_terminals, kill_session
    from x84.bbs.ini import CFG
    from x84.fail2ban import get_fail2ban_function

    SELECT_POLL = 0.02  # polling time is 20ms

    # WIN32 has no session_fds (multiprocess queues are not polled using
    # select), use a persistently empty set; for WIN32, sessions are always
    # polled for data at every loop.
    WIN32 = sys.platform.lower().startswith('win32')
    session_fds = set()

    log = logging.getLogger(__name__)

    if not len(servers):
        raise ValueError("No servers configured for event loop! (ssh, telnet)")

    tap_events = CFG.getboolean('session', 'tap_events')
    check_ban = get_fail2ban_function()
    locks = dict()

    while True:
        # shutdown, close & delete inactive clients,
        for server in servers:
            # bbs sessions that are no longer active on the socket
            # level -- send them a 'kill signal'
            for key, client in server.clients.items()[:]:
                if not client.is_active():
                    kill_session(client, 'socket shutdown')
                    del server.clients[key]
            # on-connect negotiations that have completed or failed.
            # delete their thread instance from further evaluation
            for thread in [_thread for _thread in server.threads
                           if _thread.stopped][:]:
                server.threads.remove(thread)

        check_r = list()
        for server in servers:
            check_r.append(server.server_socket.fileno())
            check_r.extend(server.client_fds())
        if not WIN32:
            # WIN32's IPC is not done using sockets, so it
            # is not possible to use select.select() on them
            session_fds = get_session_output_fds(servers)
            check_r.extend(session_fds)

        # We'd like to use timeout 'None', but the registration of
        # a new client in terminal.start_process surprises us with new
        # file descriptors for the session i/o.  Unless we loop for
        # additional `session_fds', a connecting client would block.
        ready_r, _, _ = select.select(check_r, [], [], SELECT_POLL)

        for fd in ready_r:
            # see if any new tcp connections were made
            server = find_server(servers, fd)
            if server is not None:
                accept(log, server, check_ban)

        # receive new data from tcp clients.
        client_recv(servers, ready_r, log)
        terms = get_terminals()

        # receive new data from session terminals
        if WIN32 or set(session_fds) & set(ready_r):
            try:
                session_recv(locks, terms, log, tap_events)
            except IOError as err:
                # if the ipc closes while we poll, warn and continue
                log.warn(err)

        # send tcp data to clients
        client_send(terms, log)

        # send session data, poll for user-timeout and disconnect them
        session_send(terms)


if __name__ == '__main__':
    exit(main())
