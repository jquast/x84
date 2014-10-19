from __future__ import absolute_import

# standard
import threading
import logging
import socket
import array
import errno
import time
import os

# local
from x84.bbs.exception import Disconnected
from x84.bbs.userbase import (
    check_new_user,
    check_bye_user,
    check_anonymous_user,
    check_user_password,
    check_user_pubkey,
)

from x84.terminal import spawn_client_session, on_naws
from x84.client import BaseClient, BaseConnect
from x84.server import BaseServer

# 3rd-party
import paramiko
import paramiko.py3compat


class SshClient(BaseClient):
    """
    Represents a remote Ssh Client, instantiated from SshServer.
    """
    # pylint: disable=R0902,R0904
    #         Too many instance attributes
    #         Too many public methods

    kind = 'ssh'

    def __init__(self, sock, address_pair, on_naws=None):
        super(SshClient, self).__init__(sock, address_pair, on_naws)

        # Becomes the ssh transport
        self.transport = None

        # Becomes the ssh session channel
        self.channel = None

    def shutdown(self):
        """
        Shutdown and close socket.

        Called by event loop after client is marked by deactivate().
        """
        self.active = False
        if self.channel is not None:
            self.channel.shutdown(how=2)
            self.log.debug('{self.addrport}: channel shutdown '
                           '{self.__class__.__name__}'.format(self=self))

        if self.transport.is_active():
            self.transport.close()
            self.log.debug('{self.addrport}: transport shutdown '
                           '{self.__class__.__name__}'.format(self=self))

    def is_active(self):
        """
        Returns True if channel and transport is active.
        """
        if self.transport is None or self.channel is None:
            # connecting/negotiating,
            return self.active
        return self.transport.is_active()

    def send_ready(self):
        """
        Return True if any data is buffered for sending (screen output).
        """
        if self.channel is None:
            # channel has not yet been negotiated
            return False
        return self.send_buffer.__len__() and self.channel.send_ready()

    def _send(self, send_bytes):
        """
        Sends bytes ``send_bytes`` to ssh channel, returns number of bytes
        sent. Caller must re-buffer bytes not sent.

        throws Disconnected on error
        """
        try:
            return self.channel.send(send_bytes)
        except socket.error as err:
            if err[0] == errno.EDEADLK:
                self.log.debug('{self.addrport}: {err} (bandwidth exceed)'
                               .format(self=self, err=err))
                return 0
            raise Disconnected('{self.addrport}: {err}'
                               .format(self=self, err=err))

    def send(self):
        """
        Send any data buffered, returns number of bytes sent.

        Throws Disconnected on EOF.
        """
        if not self.send_ready():
            self.log.warn('send() called on empty buffer')
            return 0

        ready_bytes = bytes(''.join(self.send_buffer))
        self.send_buffer = array.array('c')

        sent = self._send(ready_bytes)
        if sent < len(ready_bytes):
            # re-buffer data that could not be pushed to socket;
            self.send_buffer.fromstring(ready_bytes[sent:])
        return sent

    def recv_ready(self):
        """
        Returns True if data is awaiting on the ssh channel.
        """
        if self.channel is None:
            # channel has not yet been negotiated
            return False
        return self.channel.recv_ready()

    def socket_recv(self):
        """
        Receive any data ready on socket.

        All bytes buffered to :py:attr`SshClient.recv_buffer`.

        Throws Disconnected on EOF.
        """
        recv = 0
        try:
            data = self.channel.recv(self.BLOCKSIZE_RECV)
            recv = len(data)
            if 0 == recv:
                raise Disconnected('Closed by client (EOF)')
        except socket.error as err:
            raise Disconnected('socket error: {err}'.format(err))
        self.bytes_received += recv
        self.last_input_time = time.time()
        self.recv_buffer.fromstring(data)


class ConnectSsh(BaseConnect):
    """
    ssh protocol connection handler.

    Takes care of the (initial) handshake, authentication, terminal,
    and session setup.
    """

    TIME_POLL = 0.05
    TIME_WAIT_STAGE = 60

    def __init__(self, client, server_host_key, on_naws=None):
        """
        client is a ssh.SshClient instance.
        server_host_key is paramiko.RSAKey instance.
        """
        self.server_host_key = server_host_key
        self.on_naws = on_naws
        super(ConnectSsh, self).__init__(client)

    def run(self):
        """
        Accept new Ssh connect in thread.
        """
        try:
            self.client.transport = paramiko.Transport(self.client.sock)
            self.client.transport.load_server_moduli()
            self.client.transport.add_server_key(self.server_host_key)
            ssh_session = SshSessionServer(client=self.client)

            def detected():
                return ssh_session.shell_requested.isSet()

            self.client.transport.start_server(server=ssh_session)

            st_time = time.time()
            while self._timeleft(st_time):
                self.client.channel = self.client.transport.accept(1)
                if self.client.channel is not None:
                    break
                if not self.client.transport.is_active():
                    self.log.debug('{client.addrport}: transport closed.'
                                   .format(client=self.client))
                    self.client.deactivate()
                    return
            else:
                self.log.debug('{client.addrport}: no channel requested'
                               .format(client=self.client))
                self.client.deactivate()
                return

            self.log.debug('{client.addrport}: waiting for shell request'
                           .format(client=self.client))

            while not detected() and self._timeleft(st_time):
                if not self.client.is_active():
                    self.client.deactivate()
                    return
                time.sleep(self.TIME_POLL)

            if detected():
                matrix_kwargs = {attr: getattr(ssh_session, attr)
                                 for attr in ('anonymous', 'new', 'username')}
                return spawn_client_session(client=self.client,
                                            matrix_kwargs=matrix_kwargs)

        except (paramiko.SSHException, socket.error) as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        except EOFError:
            self.log.debug('{client.addrport}: EOF from client'
                           .format(client=self.client))
        except Exception as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        else:
            self.log.debug('{client.addrport}: shell not requested'
                           .format(client=self.client))
        finally:
            self.stopped = True
        self.client.deactivate()

    def _timeleft(self, st_time):
        """
        Returns True when difference of current time and st_time is below
        TIME_WAIT_STAGE, and the ``stopped`` class attribute has not yet
        been set (such as during server shutdown).
        """
        return bool(not self.stopped and
                    time.time() - st_time < self.TIME_WAIT_STAGE)


class SshSessionServer(paramiko.ServerInterface):
    def __init__(self, client):
        self.shell_requested = threading.Event()
        self.log = logging.getLogger(__name__)
        self.client = client

        # to be checked by caller
        self.new = False
        self.anonymous = False
        self.username = None

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        self.log.debug('channel request denied, kind={0}'.format(kind))
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        """ Return success/fail for username and password. """
        self.username = username.strip()

        if self.check_account_noverify(username):
            self.log.debug('any password accepted for system-enabled '
                           'account, {0!r}'.format(username))
            return paramiko.AUTH_SUCCESSFUL
        if check_user_password(username, password):
            self.log.debug('password accepted for user {0!r}.'
                           .format(username))
            return paramiko.AUTH_SUCCESSFUL

        self.log.debug('password rejected for user {0!r}.'.format(username))
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, public_key):
        self.username = username.strip()
        if self.check_account_noverify(username):
            self.log.debug('pubkey accepted for system-enabled account, {0!r}'
                           .format(username))
            return paramiko.AUTH_SUCCESSFUL
        elif check_user_pubkey(username, public_key):
            self.log.debug('pubkey accepted for user {0!r}.'
                           .format(username))
            return paramiko.AUTH_SUCCESSFUL
        self.log.debug('pubkey denied for user {0!r}.'
                       .format(username))
        return paramiko.AUTH_FAILED

    def check_account_noverify(self, username):
        """ Return success/fail for system-enabled accounts.

        For some usernames, such as 'new' or 'anonymous', a correct
        password or public key is not required -- any will do. We return
        True if ``username`` is one of these configurable account names
        and if it is enabled.

        This method has two side effects, it may set the instance
        attribute ``new_user`` or ``anonymous`` to True if it is enabled
        by configuration and the username is of their matching handles.
        """
        if check_new_user(username):
            # if allowed, allow new@, etc. to apply for an account.
            self.new = True
            self.log.debug('accepted without authentication, {0!r}: '
                           'it is an alias for new user application.'
                           .format(username))
            return True

        elif check_bye_user(username):
            # not allowed to login using bye@, logoff@, etc.
            self.log.debug('denied user, {0!r}: it is an alias for logoff'
                           .format(username))
            return False

        elif check_anonymous_user(username):
            # if enabled, allow ssh anonymous@, root@, etc.
            self.log.debug('anonymous user, {0!r} accepted by configuration.'
                           .format(username))
            self.anonymous = True
            return True

        return False

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.shell_requested.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, *_):
        self.client.env['TERM'] = term
        self.client.env['LINES'] = str(height)
        self.client.env['COLUMNS'] = str(width)
        return True

    def check_channel_window_change_request(self, channel, width, height, *_):
        self.client.env['LINES'] = str(height)
        self.client.env['COLUMNS'] = str(width)
        if self.client.on_naws is not None:
            self.client.on_naws(self.client)
        return True

    def check_channel_env_request(self, channel, name, value):
        self.log.debug('env request: [{0}] = {1}'.format(name, value))
        self.client.env[name] = value
        return True

class SshServer(BaseServer):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """

    client_factory = SshClient
    client_factory_kwargs = dict(on_naws=on_naws)
    connect_factory = ConnectSsh

    @classmethod
    def connect_factory_kwargs(cls, instance):
        return dict(server_host_key=instance.host_key)

    # Dictionary of active clients, (file descriptor, SshClient,)
    clients = {}

    def __init__(self, config):
        """
        Create a new Ssh Server.
        """
        self.log = logging.getLogger(__name__)
        self.config = config
        self.address = config.get('ssh', 'addr')
        self.port = config.getint('ssh', 'port')

        if self.config.has_option('ssh', 'HostKey'):
            filename = config.get('ssh', 'HostKey')
        else:
            filename = os.path.join(
                os.path.expanduser((config.get('system', 'datapath'))),
                'ssh_host_rsa_key')

        if not os.path.exists(filename):
            self.host_key = self.generate_host_key(filename)
        else:
            self.host_key = paramiko.RSAKey(filename=filename)
            self.log.debug('Loaded host key {0}'.format(filename))

        # bind
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.address, self.port))
            self.server_socket.listen(self.LISTEN_BACKLOG)
        except socket.error as err:
            self.log.error('Unable to bind {self.address}:self.port, {err}'
                           .format(self=self, err=err))
            exit(1)
        self.log.info('ssh listening on {self.address}:{self.port}/tcp'
                      .format(self=self))

    def generate_host_key(self, filename):
        from paramiko import RSAKey

        bits = 4096
        if self.config.has_option('ssh', 'HostKeyBits'):
            bits = self.config.getint('ssh', 'HostKeyBits')

        # generate private key and save,
        self.log.info('Generating {bits}-bit RSA public/private keypair.'
                      .format(bits=bits))
        priv_key = RSAKey.generate(bits=bits)
        priv_key.write_private_key_file(filename, password=None)
        self.log.debug('{filename} saved.'.format(filename=filename))

        # save public key,
        pub = RSAKey(filename=filename, password=None)
        with open('{0}.pub'.format(filename,), 'w') as fp:
            fp.write("{0} {1}".format(pub.get_name(), pub.get_base64()))
        self.log.debug('{filename}.pub saved.'.format(filename=filename))
        return priv_key

    def client_fds(self):
        """
        Returns a list of client file descriptors to poll for read/write.
        """
        return [_client.channel.fileno() for _client in self.clients.values()
                if _client.channel is not None]

