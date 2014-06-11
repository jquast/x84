# standard
from __future__ import print_function
import os
import logging
import socket
import array
import time
import errno
import threading

# local
from terminal import start_process, TerminalProcess, register_tty

# 3rd-party
import paramiko


class SshServer(object):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """
    MAX_CONNECTIONS = 100
    LISTEN_BACKLOG = 5

    ## Dictionary of active clients, (file descriptor, SshClient,)
    clients = {}

    ## Dictionary of environment variables received by negotiation
    env = {}

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
            self.log.debug('Loaded host key {filename}'
                           .format(filename=filename))

        # bind
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.address, self.port))
            self.server_socket.listen(self.LISTEN_BACKLOG)
        except socket.error as err:
            self.log.error('Unable to bind {0}: {1}'
                         .format((self.address, self.port), err))
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
        prv = RSAKey.generate(bits=bits)
        prv.write_private_key_file(filename, password=None)
        self.log.info('{filename} saved.'.format(filename=filename))

        # save public key,
        pub = RSAKey(filename=filename, password=None)
        with open('{0}.pub'.format(filename,), 'w') as fp:
            fp.write("{0} {1}".format(pub.get_name(), pub.get_base64()))
        self.log.info('{filename}.pub saved.'.format(filename=filename))
        return prv

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

    def __init__(self, sock, address_pair, on_naws=None):
        """
        Arguments:
            sock: socket
            address_pair: tuple (ip address, port number)
            on_naws: callback for window resizing by client
        """
        self.log = logging.getLogger(__name__)
        self.sock = sock
        self.address_pair = address_pair
        self.on_naws = on_naws # TODO
        self.active = True
        self.env = dict([('TERM', 'unknown'),
                         ('LINES', 24),
                         ('COLUMNS', 80)])
        self.send_buffer = array.array('c')
        self.recv_buffer = array.array('c')
        self.telnet_sb_buffer = array.array('c')
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
        if not self.active:
            self.log.debug('%s: already deactivated', self.addrport())
            return
        self.log.debug('%s: deactivated', self.addrport())
        self.active = False

    def shutdown(self):
        """
        Shutdown and close socket.

        Called by event loop after client is marked by deactivate().
        """
        if self.channel is not None:
            self.channel.shutdown(how=2)
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except socket.error as err:
            pass
        self.sock.close()
        self.deactivate()
        self.log.info('shutdown client: %s', self.addrport())

    def addrport(self):
        """
        Returns IP address and port of DE as string.
        """
        return '%s:%d' % (self.address_pair[0], self.address_pair[1])

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

    def send(self):
        """
        Called by TelnetServer.poll() when send data is ready.  Send any
        data buffered, trim self.send_buffer to bytes sent, and return number
        of bytes sent.  Throws Disconnected
        """
        if not self.send_ready():
            warnings.warn('send() called on empty buffer', RuntimeWarning, 2)
            return 0

        ready_bytes = bytes(''.join(self.send_buffer))
        self.send_buffer = array.array('c')

        def _send(send_bytes):
            """
            throws x84.bbs.exception.Disconnected on sock.send err
            """
            try:
                return self.channel.send(send_bytes)
            except socket.error as err:
                if err[0] == errno.EDEADLK:
                    warnings.warn('%s: %s (bandwidth exceed)' % (
                                self.addrport(), err[1],), RuntimeWarning, 2)
                    return 0
                raise Disconnected('send %d: %s' % (err[0], err[1],))

        sent = _send(ready_bytes)
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
        Called by TelnetServer.poll() when recv data is ready.  Read any
        data on socket, buffering all bytestrings to self.recv_buffer.

        If data is not received, or the connection is closed,
        x84.bbs.exception.Disconnected is raised.
        """
        recv = 0
        try:
            data = self.channel.recv(self.BLOCKSIZE_RECV)
            recv = len(data)
            if 0 == recv:
                raise Disconnected('Closed by client (EOF)')
        except socket.error as err:
            raise Disconnected('socket errno %d: %s' % (err[0], err[1],))
        self.bytes_received += recv
        self.last_input_time = time.time()
        self.recv_buffer.fromstring(data)

    def close(self):
        self.shutdown()


class ConnectSsh (threading.Thread):
    def __init__(self, client, server_host_key):
        """
        client is a ssh.SshClient instance.
        server_host_key is paramiko.RSAKey instance.
        """
        self.client = client
        self.server_host_key = server_host_key
        threading.Thread.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.info('ConnectSsh ...')

    def _spawn_session(self):
        """
        Spawn a subprocess, avoiding GIL and forcing all shared data over a
        Queue. Previous versions of x/84 and prsv were single process,
        thread-based, and shared variables.

        All IPC communication occurs through the bi-directional queues.  The
        server end (engine.py) polls the out_queue, and places results
        and input events into the inp_queue, while the client end (session.py),
        polls the inp_queue, and places output into out_queue.
        """
        if not self.client.active:
            self.log.debug('session aborted; socket was closed.')
            return
        from multiprocessing import Process, Pipe, Lock
        from x84.telnet import BINARY
        inp_recv, inp_send = Pipe(duplex=False)
        out_recv, out_send = Pipe(duplex=False)
        lock = Lock()
        is_binary = True
        child_args = (inp_recv, out_send, self.client.addrport(),
                      self.client.env, lock, is_binary)
        self.log.debug(self.__class__.__name__ + ' spawns process')
        proc = Process(target=start_process, args=child_args)
        proc.start()
        tty = TerminalProcess(self.client, inp_send, out_recv, lock)
        register_tty(tty)

    def run(self):
        """
        XXX
        """
        from x84.bbs.exception import Disconnected
        from x84.bbs.ini import CFG
        try:
            self.client.transport = paramiko.Transport(self.client.sock)
            self.client.transport.load_server_moduli()
            try:
                self.client.transport.load_server_moduli()
            except Exception, err:
                self.log.warn('load_server_moduli failed: %s' % (err,))

            self.client.transport.add_server_key(self.server_host_key)
            ssh_session = SshSessionServer(self.client)
            self.client.transport.start_server(server=ssh_session)
            self.client.channel = self.client.transport.accept(60)
            if self.client.channel is None:
                self.log.info('Connection closed: no channel.')
                self.client.deactivate()
                return
            self.log.debug('Waiting for client to request shell')
            stime = time.time()
            while time.time() - stime < 60:
                if ssh_session.shell_requested.isSet():
                    break
                if not self.client.is_active():
                    self.client.deactivate()
                    return
            self._spawn_session()
        except paramiko.SSHException as err:
            self.log.debug('Connection closed: %s', err)
            self.client.deactivate()
        except EOFError:
            self.log.debug('Connection closed: EOF from client')
            self.client.deactivate()
        except Exception as err:
            self.log.debug('Connection closed: %s', err)
            self.log.exception(err)
            self.client.deactivate()


class SshSessionServer(paramiko.ServerInterface):

    def __init__(self, client):
        self.shell_requested = threading.Event()
        self.log = logging.getLogger('SshSessionServer')
        self.client = client

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        self.log.debug('channel request denied: %s', kind)
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        self.log.debug('check_auth_password %r %r', username, password)
        # TODO, connect to userbase
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # TODO, connect to userbase
        self.log.debug('check_auth_publickey %r %r', username, key)
        return paramiko.AUTH_SUCCESSFUL

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
        return True
