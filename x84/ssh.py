""" SSH server for x84. """

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
from x84.sftp import X84SFTPServer

# 3rd-party
import paramiko
import paramiko.py3compat


class SshClient(BaseClient):

    """A remote Ssh Client, instantiated from SshServer. """

    def __init__(self, sock, address_pair, on_naws=None):
        super(SshClient, self).__init__(sock, address_pair, on_naws)

        # Becomes the ssh transport
        self.transport = None

        # Becomes the ssh session channel
        self.channel = None

        # the session kind may be transposed into 'sftp'
        # if such subsystem is enabled and connected.
        self.kind = 'ssh'

    def shutdown(self):
        """
        Shutdown and close socket.

        Called by event loop after client is marked by :meth:`deactivate`.
        """
        self.active = False
        if self.channel is not None:
            try:
                # """ only close the pipe when the user explicitly closes the
                # channel. otherwise they will get unpleasant surprises. (and
                # do it before checking self.closed, since the remote host may
                # have already closed the connection.)
                self.channel.close()
            except Exception as err:
                self.log.debug('{self.addrport}: channel close '
                               '{self.__class__.__name__}: {err}'
                               .format(self=self, err=err))
            try:
                # If ``how`` is 2, further sends and receives are disallowed.
                # This closes the stream in one or both directions.
                self.channel.shutdown(how=2)
            except EOFError:
                pass
            finally:
                self.log.debug('{self.addrport}: channel shutdown '
                               '{self.__class__.__name__}'.format(self=self))

        if self.transport is not None and self.transport.is_active():
            self.transport.close()
            self.log.debug('{self.addrport}: transport shutdown '
                           '{self.__class__.__name__}'.format(self=self))

    def is_active(self):
        """ Whether this connection is active (bool). """
        if self.transport is None or self.channel is None:
            # still connecting/negotiating, return our static
            # value (which is True, unless shutdown was called)
            return self.active
        return self.transport.is_active()

    def send_ready(self):
        """ Whether any data is buffered for delivery. """
        if self.channel is None:
            # channel has not yet been negotiated
            return False
        return self.send_buffer.__len__() and self.channel.send_ready()

    def _send(self, send_bytes):
        """
        Sends ``send_bytes`` to ssh channel, returning number of bytes sent.

        Caller must re-buffer bytes not sent.
        :raises Disconnected: on socket send error (client disconnect).
        """
        try:
            return self.channel.send(send_bytes)
        except EOFError:
            raise Disconnected('EOFError')
        except socket.error as err:
            if err[0] == errno.EDEADLK:
                self.log.debug('{self.addrport}: {err} (bandwidth exceed)'
                               .format(self=self, err=err))
                return 0
            raise Disconnected('socket error: {err}'.format(err=err))

    def send(self):
        """
        Send any data buffered and return number of bytes send.

        :raises Disconnected: client has disconnected (cannot write to socket).
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
        """ Whether data is awaiting on the ssh channel.  """
        if self.channel is None or self.kind == 'sftp':
            # very strange for SFTP, all i/o is handled by paramiko's event
            # loop and the various callback handlers of x84/sftp.py.  We always
            # return False.  If we enable this, we'll find "input" received
            # into matrix_sftp, which is raw protocol bytes that we should not
            # concern ourselves with.
            return False
        return self.channel.recv_ready()

    def socket_recv(self):
        """
        Receive data from socket, returns number of bytes received.

        :raises Disconnect: client has disconnected.
        :rtype: int
        """
        recv = 0
        try:
            data = self.channel.recv(self.BLOCKSIZE_RECV)
            recv = len(data)
            if 0 == recv:
                raise Disconnected('Closed by client (EOF)')
        except socket.error as err:
            raise Disconnected('socket error: {err}'.format(err=err))
        self.bytes_received += recv
        self.last_input_time = time.time()
        self.recv_buffer.fromstring(data)
        return recv


class ConnectSsh(BaseConnect):

    """
    SSH protocol on-connect handler (in thread).

    Takes care of the (initial) handshake, authentication,
    terminal, and session setup, ultimately spawning a
    process by :func:`spawn_client_session` on success.
    """

    #: time to periodically poll for negotiation completion.
    TIME_POLL = 0.05

    #: time to give up awaiting session negotiation.
    TIME_WAIT_STAGE = 30

    def __init__(self, client, server_host_key, on_naws=None):
        """
        Class constructor.

        :param ssh.SshClient client: an SshClient instance.
        :param paramiko.RSAKey server_host_key: an RSAKey instance.
        """
        self.server_host_key = server_host_key
        self.on_naws = on_naws
        super(ConnectSsh, self).__init__(client)

    def run(self):
        """ Accept new Ssh connect in thread. """
        try:
            self.client.transport = paramiko.Transport(self.client.sock)
            self.client.transport.load_server_moduli()
            self.client.transport.add_server_key(self.server_host_key)
            ssh_session = SshSessionServer(client=self.client)
            from x84.bbs import get_ini
            if get_ini(section='sftp', key='enabled', getter='getboolean'):
                self.client.transport.set_subsystem_handler(
                    'sftp', paramiko.SFTPServer, X84SFTPServer,
                    ssh_session=ssh_session)

            def detected():
                """ Whether shell or SFTP session has been detected. """
                return (ssh_session.shell_requested.isSet() or
                        ssh_session.sftp_requested.isSet())

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

            first_log = False
            while not detected() and self._timeleft(st_time):
                if not first_log:
                    self.log.debug('{client.addrport}: waiting for '
                                   'shell or subsystem request.'
                                   .format(client=self.client))
                    first_log = True

                if not self.client.is_active():
                    self.log.debug('{client.addrport}: transport closed '
                                   'while waiting for shell or subsystem '
                                   'request.'
                                   .format(client=self.client))
                    self.client.deactivate()
                    return
                time.sleep(self.TIME_POLL)

            if detected():
                matrix_kwargs = {attr: getattr(ssh_session, attr)
                                 for attr in ('anonymous', 'new', 'username',)}
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
        Whether time elapsed since ``st_time`` is below ``TIME_WAIT_STAGE``.

        Returns True when difference of current time and st_time is below
        TIME_WAIT_STAGE, and the ``stopped`` class attribute has not yet
        been set (such as during server shutdown).
        """
        return bool(not self.stopped and
                    time.time() - st_time < self.TIME_WAIT_STAGE)


class SshSessionServer(paramiko.ServerInterface):

    """
    SSH on-connect Session Server interface.

    Methods of this class are callbacks from Paramiko's primary thread,
    generally returning whether to accept or deny authentication and
    sub-system requests.
    """

    def __init__(self, client):
        self.shell_requested = threading.Event()
        self.sftp_requested = threading.Event()
        self.log = logging.getLogger(__name__)
        self.client = client

        # to be checked by caller
        self.new = False
        self.anonymous = False
        self.username = None
        self.sftp = False

    def check_channel_request(self, kind, chanid):
        # pylint: disable=W0613
        #         Unused argument 'chanid'
        if kind == 'session':
            self.log.debug('channel request granted, kind={0}'.format(kind))
            return paramiko.OPEN_SUCCEEDED
        self.log.debug('channel request denied, kind={0}'.format(kind))
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        """ Return success/fail for username and password. """
        self.username = username.strip()

        if self.check_account_noverify(username):
            self.log.info('any password accepted for system-enabled '
                          'account, {0!r}'.format(username))
            return paramiko.AUTH_SUCCESSFUL
        if check_user_password(username, password):
            self.log.info('password accepted for user {0!r}.'.format(username))
            return paramiko.AUTH_SUCCESSFUL

        self.log.info('password rejected for user {0!r}.'.format(username))
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, public_key):
        self.username = username.strip()
        if self.check_account_noverify(username):
            self.log.info('any pubkey accepted for system-enabled '
                          'account, {0!r}'.format(username))
            return paramiko.AUTH_SUCCESSFUL
        elif check_user_pubkey(username, public_key):
            self.log.info('pubkey accepted for user {0!r}.'.format(username))
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
        # pylint: disable=W0613
        #         Unused argument 'username'
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        # pylint: disable=W0613
        #         Unused argument 'channel'
        self.log.debug('ssh channel granted.')
        self.shell_requested.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        from x84.bbs import get_ini
        if name == 'sftp':
            if get_ini(section='sftp', key='enabled', getter='getboolean'):
                self.client.kind = 'sftp'
                self.sftp_requested.set()
                self.sftp = True

        return paramiko.ServerInterface.check_channel_subsystem_request(
            self, channel, name)

    def check_channel_pty_request(self, channel, term, width, height, *_):
        # pylint: disable=W0613
        #         Unused argument 'channel'
        self.client.env['TERM'] = term
        self.client.env['LINES'] = str(height)
        self.client.env['COLUMNS'] = str(width)
        return True

    def check_channel_window_change_request(self, channel, width, height, *_):
        # pylint: disable=W0613
        #         Unused argument 'channel'
        self.client.env['LINES'] = str(height)
        self.client.env['COLUMNS'] = str(width)
        if self.client.on_naws is not None:
            self.client.on_naws(self.client)
        return True

    def check_channel_env_request(self, channel, name, value):
        # pylint: disable=W0613
        #         Unused argument 'channel'
        self.log.debug('env request: [{0}] = {1}'.format(name, value))
        self.client.env[name] = value
        return True


class SshServer(BaseServer):

    """ SSH Server, tracking connecting clients for send/recv management. """

    client_factory = SshClient
    client_factory_kwargs = dict(on_naws=on_naws)
    connect_factory = ConnectSsh

    @classmethod
    def connect_factory_kwargs(cls, instance):
        return dict(server_host_key=instance.host_key)

    # Dictionary of active clients, (file descriptor, SshClient,)
    clients = {}

    def __init__(self, config):
        """ Class initializer. """
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
            socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        try:
            self.server_socket.bind((self.address, self.port))
            self.server_socket.listen(self.LISTEN_BACKLOG)
        except socket.error as err:
            self.log.error('Unable to bind {self.address}:{self.port}, {err}'
                           .format(self=self, err=err))
            exit(1)
        self.log.info('ssh listening on {self.address}:{self.port}/tcp'
                      .format(self=self))

    def generate_host_key(self, filename):
        """ Generate server host key to local filepath ``filename``. """
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
        """ Return list of client file descriptors to poll for read/write. """
        return [_client.channel.fileno() for _client in self.clients.values()
                if _client.channel is not None]

    def clients_ready(self, ready_fds=None):
        """
        Return a list of clients with data ready to be receive.

        The ``ready_fds`` parameter is ignored by the SSH Server.
        """
        return [client for client in self.clients.values()
                if client.recv_ready()]
