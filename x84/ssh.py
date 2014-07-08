# standard
import os
import logging
import socket
import array
import time
import errno
import threading

# local
from terminal import spawn_client_session
from x84.bbs.exception import Disconnected

# 3rd-party
import paramiko


class SshServer(object):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """
    MAX_CONNECTIONS = 100
    LISTEN_BACKLOG = 5

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

        # generate/load host key
        filename = config.get('ssh', 'HostKey')
        if not os.path.exists(filename):
            self.host_key = self.generate_host_key()
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
        self.log.info('listening on {self.address}:{self.port}/tcp'
                      .format(self=self))

    def generate_host_key(self):
        from paramiko import RSAKey

        filename = self.config.get('ssh', 'HostKey')
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

    def client_count(self):
        """
        Returns the number of active connections.
        """
        return len(self.clients)

    def client_list(self):
        """
        Returns a list of connected clients.
        """
        return self.clients.values()

    def client_fds(self):
        """
        Returns a list of client file descriptors to poll for read/write.
        """
        return [_client.channel.fileno() for _client in self.clients.values()
                if _client.channel is not None]


class SshClient(object):
    """
    Represents a remote Ssh Client, instantiated from SshServer.
    """
    # pylint: disable=R0902,R0904
    #         Too many instance attributes
    #         Too many public methods
    BLOCKSIZE_RECV = 64
    SB_MAXLEN = 65534  # maximum length of subnegotiation string, allow
                       # a fairly large one for NEW_ENVIRON negotiation
    kind = 'ssh'

    def __init__(self, sock, address_pair, on_naws=None):
        """
        Arguments:
            sock: socket
            address_pair: tuple (ip address, port number)
        """
        self.log = logging.getLogger(__name__)
        self.sock = sock
        self.address_pair = address_pair
        self.on_naws = on_naws

        self.active = True
        self.env = dict([('TERM', 'unknown'),
                         ('LINES', 24),
                         ('COLUMNS', 80),
                         ('connection-type', self.kind),
                         ])
        self.send_buffer = array.array('c')
        self.recv_buffer = array.array('c')
        self.bytes_received = 0
        self.connect_time = time.time()
        self.last_input_time = time.time()

        # Becomes the ssh transport
        self.transport = None

        # Becomes the ssh session channel
        self.channel = None

    def send_str(self, bstr):
        """
        Buffer bytestring for client.
        """
        self.send_buffer.fromstring(bstr)

    def send_unicode(self, ucs, encoding='utf8'):
        """
        Buffer unicode string, encoded for client as 'encoding'.
        """
        ## Must be escaped 255 (IAC + IAC) to avoid IAC intepretation
        self.send_str(ucs.encode(encoding, 'replace')
                      .replace(chr(255), 2 * chr(255)))

    def deactivate(self):
        """
        Flag client for disconnection.
        """
        if self.active:
            self.active = False
            self.log.debug('{self.addrport}: deactivated'.format(self=self))

    def shutdown(self):
        """
        Shutdown and close socket.

        Called by event loop after client is marked by deactivate().
        """
        self.active = False
        if self.channel is not None:
            self.channel.shutdown(how=2)
        if self.transport.is_active():
            self.transport.close()
            self.log.debug('{self.addrport}: socket shutdown'.format(self=self))

    @property
    def addrport(self):
        """
        Returns IP address and port as string.
        """
        return '{0}:{1}'.format(*self.address_pair)

    def idle(self):
        """
        Returns time elapsed since DE last sent input.
        """
        return time.time() - self.last_input_time

    def duration(self):
        """
        Returns time elapsed since DE connected.
        """
        return time.time() - self.connect_time

    def input_ready(self):
        """
        Return True if any data is buffered for reading (keyboard input).
        """
        return bool(self.recv_buffer.__len__())

    def is_active(self):
        """
        Returns True if channel and transport is active.
        """
        if self.transport is None or self.channel is None:
            # connecting/negotiating,
            return self.active
        return self.transport.is_active()

    def get_input(self):
        """
        Get any input bytes received from the DE.

        The input_ready method returns True when bytes are available.
        """
        data = self.recv_buffer.tostring()
        self.recv_buffer = array.array('c')
        return data

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

    def close(self):
        self.shutdown()


class ConnectSsh (threading.Thread):
    TIME_POLL = 0.05
    TIME_WAIT_STAGE = 60

    def __init__(self, client, server_host_key, on_naws=None):
        """
        client is a ssh.SshClient instance.
        server_host_key is paramiko.RSAKey instance.
        """
        self.log = logging.getLogger(__name__)
        self.client = client
        self.server_host_key = server_host_key
        self.on_naws = on_naws
        threading.Thread.__init__(self)

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
            self.client.channel = (self.client.transport
                                   .accept(self.TIME_WAIT_STAGE))

            if self.client.channel is None:
                self.log.debug('{client.addrport}: no channel requested'
                               .format(client=self.client))
                self.client.deactivate()
                return

            self.log.debug('{client.addrport}: waiting for shell request'
                           .format(client=self.client))

            st_time = time.time()
            while not detected() and self._timeleft(st_time):
                if not self.client.is_active():
                    self.client.deactivate()
                    return
                time.sleep(self.TIME_POLL)

            if detected():
                return spawn_client_session(client=self.client)

        except paramiko.SSHException as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        except socket.error as err:
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
        self.client.deactivate()

    def _timeleft(self, st_time):
        """
        Returns True when difference of current time and st_time is below
        TIME_WAIT_STAGE.
        """
        return bool(time.time() - st_time < self.TIME_WAIT_STAGE)


class SshSessionServer(paramiko.ServerInterface):

    def __init__(self, client):
        self.shell_requested = threading.Event()
        self.log = logging.getLogger(__name__)
        self.client = client

        # to be checked by caller
        self.new_user = False
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

        if self._check_new_user(username):
            self.new_user = True
            self.log.debug('new user account, {0!r}'.format(username))
            return paramiko.AUTH_SUCCESSFUL

        elif self._check_bye_user(username):
            # not allowed to login using bye@, logoff@, etc.
            self.log.debug('denied byecmds name, {0!r}'.format(username))
            return paramiko.AUTH_FAILED

        elif self._check_anonymous_user(username):
            self.log.debug('{0!r} user accepted by server configuration.'
                           .format(username))
            self.anonymous = True
            return paramiko.AUTH_SUCCESSFUL

        elif self._check_user_password(username, password):
            self.log.debug('password accepted for user {0!r}.'
                           .format(username))
            return paramiko.AUTH_SUCCESSFUL

        self.log.debug('password rejected for user {0!r}.'.format(username))
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, public_key):
        self.username = username.strip()
        if self._check_user_pubkey(username, public_key):
            self.log.debug('pubkey accepted for user {0!r}.'
                           .format(username))
            return paramiko.AUTH_SUCCESSFUL
        self.log.debug('pubkey denied for user {0!r}.'
                       .format(username))
        return paramiko.AUTH_FAILED

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
        self.client.env[name] = value
        return True

    @staticmethod
    def _get_matches(matrix_ini_key):
        from x84.bbs import ini
        return ini.CFG.get('matrix', matrix_ini_key).split()

    @classmethod
    def _check_new_user(cls, username):
        """ Boolean return when username matches `newcmds' ini cfg. """
        matching = cls._get_matches('newcmds')
        return matching and username in matching

    @classmethod
    def _check_bye_user(cls, username):
        """ Boolean return when username matches `byecmds' in ini cfg. """
        matching = cls._get_matches('byecmds')
        return matching and username in matching

    @staticmethod
    def _check_anonymous_user(username):
        """ Boolean return when user is anonymous and is allowed. """
        from x84.bbs import ini
        enabled = ini.CFG.getboolean('matrix', 'enable_anonymous')
        return enabled and username == 'anonymous'

    @staticmethod
    def _check_user_password(username, password):
        """ Boolean return when username and password match user record. """
        from x84.bbs import find_user, get_user
        handle = find_user(username)
        if handle is None:
            return False
        user = get_user(handle)
        if user is None:
            return False
        return user.auth(password)

    @staticmethod
    def _check_user_pubkey(username, public_key):
        """ Boolean return when public_key matches user record. """
        from x84.bbs import find_user, get_user
        handle = find_user(username)
        if handle is None:
            return False
        user = get_user(handle)
        user_pubkey = user.get('pubkey', False)
        return user_pubkey and user_pubkey == public_key
