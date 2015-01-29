"""
rlogin server for x84.

This only exists to demonstrate alternative client protocols rather than
only ssh or telnet.  rlogin is a very insecure and not recommended!
"""
# http://www.ietf.org/rfc/rfc1282.txt

import logging
import select
import socket
import array
import errno
import time

# local
from x84.bbs.userbase import (
    check_new_user,
    check_bye_user,
    check_anonymous_user
)
from x84.bbs.exception import Disconnected
from x84.client import BaseClient, BaseConnect
from x84.server import BaseServer
from x84.terminal import spawn_client_session


class RLoginClient(BaseClient):

    """ rlogin protocol client handler. """

    kind = 'rlogin'

    def __init__(self, sock, address_pair, on_naws=None):
        super(RLoginClient, self).__init__(sock, address_pair, on_naws)

        # Urgent send buffer (MSG_OOB)
        self.usend_buffer = array.array('c')

    def recv_ready(self):
        """ Whether data is awaiting on the telnet socket. """
        return (self.is_active() and bool(
            select.select([self.sock.fileno()], [], [], 0)[0]))

    def send(self):
        """
        Send any data buffered and return number of bytes send.

        :raises Disconnected: client has disconnected (cannot write to socket).
        """
        if len(self.usend_buffer) > 0:
            ready_bytes = bytes(''.join(self.usend_buffer))
            self.usend_buffer = array.array('c')

            def _send_urgent(send_bytes):
                """ Sent urgent (out of band) TCP packet. """
                try:
                    return self.sock.send(send_bytes, socket.MSG_OOB)
                except socket.error as err:
                    if err.errno in (errno.EDEADLK, errno.EAGAIN):
                        self.log.debug('{self.addrport}: {err} '
                                       '(bandwidth exceed)'
                                       .format(self=self, err=err))
                        return 0
                    raise Disconnected('send: {0}'.format(err))

            sent = _send_urgent(ready_bytes)
            if sent < len(ready_bytes):
                self.usend_buffer.fromstring(ready_bytes[sent:])

        else:
            super(RLoginClient, self).send()

    def send_ready(self):
        """ Whether any data is buffered for delivery. """
        return bool(len(self.send_buffer) + len(self.usend_buffer))

    def send_urgent_str(self, bstr):
        """ Buffer urgent (OOB) message to client from bytestring. """
        self.usend_buffer.fromstring(bstr)


class ConnectRLogin(BaseConnect):

    """
    rlogin protocol connection handler.

    Takes care of the (initial) handshake, terminal and session setup.
    """

    #: maximum time elapsed allowed for on-connect negotiation
    TIME_NEGOTIATE = 5.0

    #: poll interval for on-connect negotiation
    TIME_POLL = 0.10

    def run(self):
        """
        Perform rfc1282 (rlogin) connection establishment.

        Determine rlogin on-connect data, rlogin may only
        negotiate session user name and terminal type.
        """
        try:
            self._set_socket_opts()

            self.banner()

            # Receive on-connect data-value pairs, may raise ValueError.
            data = self.get_connect_data()

            # parse into dict,
            parsed = self.parse_connect_data(data)
            for key, value in parsed.items():
                if value:
                    self.log.debug('{client.addrport}: {key}={value}'
                                   .format(client=self.client,
                                           key=key, value=value))

            # and apply to session-local self.client.env.
            self.apply_environment(parsed)

            # The server returns a zero byte to indicate that it has received
            # these strings and is now in data transfer mode.
            if self.client.is_active():
                self.client.send_str(bytes('\x00'))

                # The remote server indicates to the client that it can accept
                # window size change information by requesting a window size
                # message (as out of band data) just after connection
                # establishment and user identification exchange.  The client
                # should reply to this request with the current window size.
                #
                # Disabled: neither SyncTERM or BSD rlogin honors this, and
                # we haven't got any code to parse it. Its in the RFC but ..
                self.client.send_urgent_str(bytes('\x80'))

            matrix_kwargs = {}
            username = parsed.get('server-user-name', 'new')
            if check_new_user(username):
                # new@ login may be allowed
                matrix_kwargs['new'] = True
            if check_bye_user(username):
                # rlogin as 'bye', 'logoff', etc. not allowed
                raise ValueError('Bye user {0!r} used by rlogin'
                                 .format(username))
            if check_anonymous_user(username):
                # anonymous@ login may be allowed
                matrix_kwargs['anonymous'] = True

            if self.client.is_active():
                return spawn_client_session(client=self.client,
                                            matrix_kwargs=matrix_kwargs)
        except socket.error as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        except EOFError:
            self.log.debug('{client.addrport}: EOF from client'
                           .format(client=self.client))
        except Exception as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        finally:
            self.stopped = True
        self.client.deactivate()

    def get_connect_data(self):
        """
        Receive four null-terminated strings transmitted by client on-connect.

        :return: bytes received, containing at least 4 NUL-terminated strings.
        :rtype: str
        :raises ValueError: on-connect data timeout or bandwidth exceeded.
        """
        established_msg = ('{client.addrport}: rlogin connection established'
                           .format(client=self.client))
        data = array.array('c')

        #: maximum size of negotiation string
        MAXLEN = 4096

        err = None
        st_time = time.time()
        while True:
            # allow time to pass for more data,
            time.sleep(self.TIME_POLL)

            if self.client.recv_ready():
                self.client.socket_recv()

            if self.client.input_ready():
                # data to be received,
                # read in data.
                data.fromstring(self.client.get_input())

            n_nul = data.count('\x00')
            if n_nul >= 3:
                self.client.env['RLOGIN_CLIENT_NAME'] = {
                    3: 'SyncTERM',
                    4: 'BSD',
                }.get(n_nul, 'unknown:{0})'.format(n_nul))
                if self.client.env['RLOGIN_CLIENT_NAME'] == 'SyncTERM':
                    self.client.env['encoding'] = 'cp437'

                self.log.debug('{msg} ({env[RLOGIN_CLIENT_NAME]})'
                               .format(msg=established_msg,
                                       env=self.client.env))
                return data.tostring()

            elif time.time() - st_time >= self.TIME_NEGOTIATE:
                # too much time has elapsed, give up.
                err = 'rlogin on-connect timeout'

            elif len(data) >= MAXLEN:
                # client has sent an abusive number of bytes, disconnect.
                err = 'rlogin bandwidth exceeded'

            if err:
                raise ValueError(err)

    def apply_environment(self, parsed):
        """
        Cherry-pick rlogin values into client environment variables.

        :param dict parsed: values identified by class method
                            ``parse_connect_data()``
        :rtype: None
        """
        # Only terminal-type environment variable is propagated from client, we
        # can also discern their USER by 'client-user-name', which we would
        # expect to be analogous to telnet environment value USER.
        self.client.env['TERM'] = parsed.get('terminal-type', 'vt220')
        if 'client-user-name' in parsed:
            self.client.env['USER'] = parsed.get('client-user-name')

    def parse_connect_data(self, data):
        """
        Parse and return raw data received by client on-connect.

        :param str data: bytes received by class method get_connect_data().
        :return: dictionary containing pertinent key/values
        :rtype: dict
        """
        parsed = dict()
        try:
            # Upon connection establishment, the client sends four
            # null-terminated strings to the server.  The first is an empty
            # string (i.e., it consists solely of a single zero byte), followed
            # by three non-null strings: the client username, the server
            # username, and the terminal type and speed.  More explicitly:
            #
            #        <null>
            #        client-user-name<null>
            #        server-user-name<null>
            #        terminal-type/speed<null>
            segs = data.split('\x00')

            # SyncTerm leaves a null-terminating byte.
            if len(segs) == 5 and segs[4] == '':
                segs.pop(4)

            for segname in ('null',
                            'client-user-name',
                            'server-user-name',
                            'terminal-type/speed'):
                if len(segs):
                    parsed[segname] = segs.pop(0)

            parsed['terminal-type'], parsed['terminal-speed'] = (
                parsed.pop('terminal-type/speed', 'unknown/0')
                .split('/', 2))
        except ValueError as err:
            self.log.exception("ValueError in parse_connect_data: {err}"
                               .format(err=err))

        return parsed

    def _set_sock_opts(self):
        """ Set the socket in non-blocking mode. """
        self.client.sock.setblocking(0)
        self.client.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)


class RLoginServer(BaseServer):

    """ RLogin/RSH protocol server. """

    client_factory = RLoginClient
    connect_factory = ConnectRLogin

    def __init__(self, config):
        """ Class initializer. """
        self.log = logging.getLogger(__name__)
        self.config = config
        self.addr = config.get('rlogin', 'addr')
        self.port = 513
        if config.has_option('rlogin', 'port'):
            # rlogin is coded for port 513, though you could specify an
            # alternative port if you really wished.
            self.port = config.getint('rlogin', 'port')

        # bind
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET,
                                      socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.addr, self.port))
            self.server_socket.listen(self.LISTEN_BACKLOG)
        except socket.error as err:
            self.log.error('unable to bind {self.addr}:{self.port}: {err}'
                           .format(self=self, err=err))
            exit(1)

        self.log.info('rlogin listening on {self.addr}:{self.port}/tcp'
                      .format(self=self))

    def client_fds(self):
        """ Return list of rlogin client file descriptors. """
        fds = [client.fileno() for client in self.clients.values()]
        # pylint: disable=bad-builtin
        #         You're drunk, pylint
        return filter(None, fds)
