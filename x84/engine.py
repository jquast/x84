#!/usr/bin/env python
"""
Command-line launcher and main event loop for x/84
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
import logging

# local
__import__('encodings')  # provides alternate encodings

BANNED_IP_LIST = dict()
ATTEMPTED_LOGINS = dict()

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
    from x84.bbs.ini import CFG

    # retrieve enabled servers
    servers = get_servers(CFG)

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
    log = logging.getLogger('x84.engine')

    servers = []

    if CFG.has_section('telnet'):
        # start telnet server instance
        from x84.telnet import TelnetServer
        servers.append(TelnetServer(config=CFG))

    if CFG.has_section('ssh'):
        # start ssh server instance
        try:
            from x84.ssh import SshServer
            servers.append(SshServer(config=CFG))
        except ImportError as err:
            log.error(err)  # missing paramiko, Crypto ..

    if CFG.has_section('rlogin'):
        # start rlogin server instance
        from x84.rlogin import RLoginServer
        servers.append(RLoginServer(config=CFG))

    return servers


def find_server(servers, fd):
    for server in servers:
        if fd == server.server_socket.fileno():
            return server


def fail2ban_check(ip):
    """
    Return True if the connection from address ``ip`` should be accepted.

    fail2ban-like blacklists for blocking brute force attempts.
    just add [fail2ban] to your default.ini.

    the following options are available, but not required:

    ip_blacklist - space-separated list of IPs on permanent blacklist
    ip_whitelist - space-separated list of IPs to always allow
    max_attempted_logins - the maximum number of logins allowed for the
        given time window
    max_attempted_logins_window - the length (in seconds) of the window for
        which logins will be tracked (sliding scale)
    initial_ban_length - ban length (in seconds) when an IP is blacklisted
    ban_increment_length - amount of time (in seconds) to add to a ban on
        subsequent login attempts
    """
    import time
    import ConfigParser
    from x84.bbs.ini import CFG
    if not CFG.has_section('fail2ban'):
        return True
    ip = address_pair[0]
    when = int(time.time())
    # default options
    ip_blacklist = set([])
    ip_whitelist = set([])
    max_attempted_logins = 3
    max_attempted_logins_window = 30
    initial_ban_length = 360
    ban_increment_length = 360

    # pull config
    try:
        ip_blacklist = set(map(str.strip,
           CFG.get('fail2ban', 'ip_blacklist', '').split(' ')))
    except ConfigParser.NoOptionError:
        pass

    try:
        ip_whitelist = set(map(str.strip,
            CFG.get('fail2ban', 'ip_whitelist', '').split(' ')))
    except ConfigParser.NoOptionError:
        pass

    try:
        max_attempted_logins = CFG.getint(
            'fail2ban', 'max_attempted_logins')
    except ConfigParser.NoOptionError:
        pass

    try:
        max_attempted_logins_window = CFG.getint(
            'fail2ban', 'max_attempted_logins_window')
    except ConfigParser.NoOptionError:
        pass

    try:
        initial_ban_length = CFG.getint(
            'fail2ban', 'initial_ban_length')
    except ConfigParser.NoOptionError:
        pass

    try:
        ban_increment_length = CFG.getint(
            'fail2ban', 'ban_increment_length')
    except ConfigParser.NoOptionError:
        pass

    # check to see if IP is blacklisted
    if ip in ip_blacklist:
        log.debug('Blacklisted IP rejected: {ip}'.format(ip=ip))
        return False
    # check to see if IP is banned
    elif ip in BANNED_IP_LIST:
        # expired?
        if when > BANNED_IP_LIST[ip]:
            # expired ban; remove it
            del BANNED_IP_LIST[ip]
            ATTEMPTED_LOGINS[ip] = {
                'attempts': 1,
                'expiry': when + max_attempted_logins_window
                }
            log.debug('Banned IP expired: {ip}'
                    .format(ip=address_pair[0]))
        else:
            # increase the expiry and kick them out
            BANNED_IP_LIST[ip] += ban_increment_length
            log.debug('Banned IP rejected: {ip}'.format(ip=ip))
            return False
    # check num of attempts, ban if exceeded max
    elif ip in ATTEMPTED_LOGINS:
        if when > ATTEMPTED_LOGINS[ip]['expiry']:
            # window closed; start over
            record = ATTEMPTED_LOGINS[ip]
            record['attempts'] = 1
            record['expiry'] = when + max_attempted_logins_window
            ATTEMPTED_LOGINS[ip] = record
            log.debug('Attempt outside of expiry window')
        elif ATTEMPTED_LOGINS[ip]['attempts'] > max_attempted_logins:
            # max # of attempts reached
            del ATTEMPTED_LOGINS[ip]
            BANNED_IP_LIST[ip] = when + initial_ban_length
            log.warn('Exceeded maximum attempts; banning {ip}'
                     .format(ip=ip))
            return False
        else:
            # extend window
            record = ATTEMPTED_LOGINS[ip]
            record['attempts'] += 1
            record['expiry'] += max_attempted_logins_window
            ATTEMPTED_LOGINS[ip] = record
            log.debug('Window extended')
    # log attempted login
    elif ip not in ip_whitelist:
        log.debug('First attempted login for this window')
        ATTEMPTED_LOGINS[ip] = {
            'attempts': 1,
            'expiry': when + max_attempted_logins_window,
            }

    return True




def accept(log, server):
    """
    accept new connection from server.server_socket,
    instantiate a new instance of client_factory,
    registering it with dictionary server.clients,
    spawning an unmanaged thread using connect_factory.
    """
    import socket

    if None in (server.client_factory, server.connect_factory):
        raise NotImplementedError(
            "No accept for server class {server.__class__.__name__}"
            .format(server=server))

    if callable(server.client_factory_kwargs):
        client_factory_kwargs = server.client_factory_kwargs(server)
    else:
        client_factory_kwargs = server.client_factory_kwargs
    if callable(server.connect_factory_kwargs):
        connect_factory_kwargs = server.connect_factory_kwargs(server)
    else:
        connect_factory_kwargs = server.connect_factory_kwargs
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

        # fail2ban check fails, the connecting IP has been banned.
        if fail2ban_check(address_pair[0]) is False:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except socket.error:
                pass

            sock.close()
            return

        client = server.client_factory(
            sock,
            address_pair,
            **client_factory_kwargs
        )
        # spawn negotiation and process registration thread
        server.clients[client.sock.fileno()] = client
        thread = server.connect_factory(client, **connect_factory_kwargs)
        log.info('{client.kind} connection from {client.addrport} '
                 '*{thread.name}).'.format(client=client, thread=thread))
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
        if event in locks:
            # lock already held; check for and display owner, or
            # acquire a lock from a now-deceased session.
            for _sid, _tty in get_terminals():
                if _sid == locks[event][1] and _sid != tty.sid:
                    log.debug('[%s] %r not acquired, held by %s.',
                              tty.sid, (event, data), _sid)
                    break
            else:
                log.debug('[%s] %r discovered stale lock, previously '
                          'held by %s.', tty.sid, (event, data), locks[event][1])
                del locks[event]
        if event not in locks:
            locks[event] = (time.time(), tty.sid)
            tty.master_write.send((event, True,))
            if tap_events:
                log.debug('[%s] %r granted.', tty.sid, (event, data))
        else:
            # caller signals this kind of thread is short-lived, and any
            # existing lock older than 'stale' should be released.
            if (stale is not None
                    and time.time() - locks[event][0] > stale):
                tty.master_write.send((event, True,))
                locks[event] = (time.time(), tty.sid)
                log.warn('[%s] %r stale %fs.',
                         tty.sid, (event, data),
                         time.time() - locks[event][0])
            # signal busy with matching event, data=False
            else:
                tty.master_write.send((event, False,))
                log.debug('[%s] %r not acquired.', tty.sid, (event, data))

    elif method == 'release':
        if event not in locks:
            log.error('[%s] %r failed: no match', tty.sid, (event, data))
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
                data.msg = ('{data.handle}[{client.addrport}] {data.msg}'
                            .format(data=data, client=tty.client))
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
                        kill_session(tty.client, reason)
                        break

            # 'route': message passing directly from one session to another
            elif event == 'route':
                if tap_events:
                    log.debug('route %r', (event, data))
                tgt_sid, send_event, send_val = data[0], data[1], data[2:]
                for _sid, _tty in terminals:
                    if tgt_sid == _sid:
                        _tty.master_write.send((send_event, send_val))
                        break

            # 'global': message broadcasting to all sessions
            elif event == 'global':
                if tap_events:
                    log.debug('broadcast %r', (event, data))
                for _sid, _tty in terminals:
                    if sid != _sid:
                        _tty.master_write.send((event, data,))

            # 'set-timeout': set user-preferred timeout
            elif event == 'set-timeout':
                if tap_events:
                    log.debug('set-timeout %d', data)
                tty.timeout = data

            # 'db*': access DBProxy API for shared sqlitedict
            elif event.startswith('db'):
                thread = DBHandler(tty.master_write, event, data)
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
    import select
    import sys
    from x84.terminal import get_terminals, kill_session
    from x84.bbs.ini import CFG
    SELECT_POLL = 0.05
    WIN32 = sys.platform.lower().startswith('win32')
    if WIN32:
        # poll much more often for windows until we come up with something
        # better regarding checking for session output
        SELECT_POLL = 0.05

    # WIN32 has no session_fds, use empty set.
    session_fds = set()

    log = logging.getLogger('x84.engine')

    if not len(servers):
        raise ValueError("No servers configured for event loop! (ssh, telnet)")

    tap_events = CFG.getboolean('session', 'tap_events')
    locks = dict()

    # message polling setup
    if CFG.has_option('msg', 'poll_interval'):
        from x84 import msgpoll
        msgpoll.start_polling()

    if CFG.has_section('web') and CFG.has_option('web', 'modules'):
        try:
            __import__("web")
            __import__("OpenSSL")
            import webserve
            module_names = CFG.get('web', 'modules', '').split(',')
            if module_names:
                web_modules = set(map(str.strip, module_names))
                log.info('starting webmodules: {0!r}'.format(web_modules))
                webserve.start(web_modules)
        except ImportError as err:
            log.error("section [web] enabled but not enabled: {0}".format(err))

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

        server_fds = [server.server_socket.fileno() for server in servers]
        client_fds = [fd for fd in server.client_fds() for server in servers]
        check_r = server_fds + client_fds
        if not WIN32:
            session_fds = get_session_output_fds(servers)
            check_r += session_fds

        # We'd like to use timeout 'None', but the registration of
        # a new client in terminal.start_process surprises us with new
        # file descriptors for the session i/o. unless we loop for
        # additional `session_fds', a connecting client would block.
        ready_r, _, _ = select.select(check_r, [], [], SELECT_POLL)

        for fd in ready_r:
            # see if any new tcp connections were made
            server = find_server(servers, fd)
            if server is not None:
                accept(log, server)

        # receive new data from tcp clients.
        client_recv(servers, log)
        terms = get_terminals()

        # receive new data from session terminals
        if WIN32 or set(session_fds) & set(ready_r):
            try:
                session_recv(locks, terms, log, tap_events)
            except IOError, err:
                # if the ipc closes while we poll, warn and continue
                log.warn(err)

        # send tcp data to clients
        client_send(terms, log)

        # send session data, poll for user-timeout and disconnect them
        session_send(terms)


if __name__ == '__main__':
    import sys
    if sys.maxunicode == 65535:
        sys.stderr.write('Python not built with wide unicode support!\n')

    exit(main())
