'''
Base classes for clients and connections.
'''

import array
import errno
import logging
import socket
import threading
import time
import warnings

# local
from x84.bbs.exception import Disconnected
from .terminal import spawn_client_session


class BaseClient(object):

    '''
    Base class for remote client implementations, instantiated from the
    corresponding server class.
    '''

    #: Override in subclass: a general string identifier for the
    #: connecting protocol (for example, 'telnet', 'ssh', 'rlogin')
    kind = None

    #: maximum unit of data received for each call to socket_recv()
    BLOCKSIZE_RECV = 64

    #: terminal type identifier when not yet negotiated
    TTYPE_UNDETECTED = 'unknown'

    def __init__(self, sock, address_pair, on_naws=None):
        self.log = logging.getLogger(self.__class__.__name__)
        self.sock = sock
        self.address_pair = address_pair
        self.on_naws = on_naws
        self.active = True
        self.env = dict([('TERM', self.TTYPE_UNDETECTED),
                         ('LINES', 24),
                         ('COLUMNS', 80),
                         ('connection-type', self.kind),
                         ])
        self.send_buffer = array.array('c')
        self.recv_buffer = array.array('c')
        self.bytes_received = 0
        self.connect_time = time.time()
        self.last_input_time = time.time()

    # low level I/O

    def close(self):
        '''
        Close the connection with the client.
        '''
        self.shutdown()

    def fileno(self):
        '''
        Return the active file descriptor number.
        '''
        try:
            return self.sock.fileno()
        except socket.error:
            return None

    def input_ready(self):
        """
        Return True if any data is buffered for reading (keyboard input).
        """
        return bool(self.recv_buffer.__len__())

    def recv_ready(self):
        """
        Subclass and implement: returns True if socket_recv() should be called.
        """
        raise NotImplementedError()

    def send(self):
        """
        Called by Server.poll() when send data is ready.  Send any data
        buffered, trim self.send_buffer to bytes sent, and return number of
        bytes sent.  Throws Disconnected
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
                return self.sock.send(send_bytes)
            except socket.error as err:
                if err.errno in (errno.EDEADLK, errno.EAGAIN):
                    self.log.debug('{self.addrport}: {err} (bandwidth exceed)'
                                   .format(self=self, err=err))
                    return 0
                raise Disconnected('send: {0}'.format(err))

        sent = _send(ready_bytes)
        if sent < len(ready_bytes):
            # re-buffer data that could not be pushed to socket;
            self.send_buffer.fromstring(ready_bytes[sent:])
        return sent

    def send_ready(self):
        """
        Return True if any data is buffered for sending (screen output).
        """
        return bool(self.send_buffer.__len__())

    def shutdown(self):
        """
        Shutdown and close socket.

        Called by event loop after client is marked by deactivate().
        """
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.log.debug('{self.addrport}: socket shutdown '
                           '{self.__class__.__name__}'.format(self=self))
        except socket.error:
            pass
        self.active = False
        self.sock.close()

    def socket_recv(self):
        """
        Receive data from the client socket and returns num bytes received.
        """
        try:
            data = self.sock.recv(self.BLOCKSIZE_RECV)
            recv = len(data)
            if recv == 0:
                raise Disconnected('Closed by client (EOF)')

        except socket.error as err:
            if err.errno == errno.EWOULDBLOCK:
                return 0
            raise Disconnected('socket_recv error: {0}'.format(err))

        self.bytes_received += recv
        self.last_input_time = time.time()
        self.recv_buffer.fromstring(data)
        return recv

    # high level I/O

    def get_input(self):
        """
        Get any input bytes received from the DE. The input_ready method
        returns True when bytes are available.
        """
        data = self.recv_buffer.tostring()
        self.recv_buffer = array.array('c')
        return data

    def send_str(self, bstr):
        """
        Buffer bytestring for client.
        """
        self.send_buffer.fromstring(bstr)

    def send_unicode(self, ucs, encoding='utf8'):
        """
        Buffer unicode string, encoded for client as 'encoding'.
        """
        # Must be escaped 255 (IAC + IAC) to avoid IAC intepretation
        self.send_str(ucs.encode(encoding, 'replace')
                      .replace(chr(255), 2 * chr(255)))

    # activity

    def is_active(self):
        """
        Returns True if this connection is still active.
        """
        return self.active

    def deactivate(self):
        """
        Flag client for disconnection.
        """
        if self.active:
            self.active = False
            self.log.debug('{self.addrport}: deactivated'.format(self=self))

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

    # client information

    @property
    def addrport(self):
        """
        Returns IP address and port of DE as string.
        """
        return '%s:%d' % (self.address_pair[0], self.address_pair[1])


class BaseConnect(threading.Thread):

    '''
    Base class for client connect factories.
    '''

    #: for x/y/z-modem transfers? -- unused.
    is_binary = True

    # whether this thread is completed. Set to ``True`` to cause an on-connect
    # thread to forcefully exit early, such as when the server is shutdown.
    stopped = False

    def __init__(self, client):
        """
        client is a telnet.TelnetClient instance.
        """
        self.client = client
        threading.Thread.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)

    def banner(self):
        """
        Negotiate protocol options or advertise protocol banner.
        """
        pass

    def run(self):
        """
        Negotiate and inquire about terminal type, telnet options, window size,
        and tcp socket options before spawning a new session.
        """
        from x84.bbs.exception import Disconnected
        try:
            self._set_socket_opts()
            self.banner()
            if self.client.is_active():
                return spawn_client_session(client=self.client)
        except (Disconnected, socket.error) as err:
            self.log.debug('Connection closed: %s', err)
        finally:
            self.stopped = True
        self.client.deactivate()

    def _set_socket_opts(self):
        """
        Set socket non-blocking and enable TCP KeepAlive.
        """
        self.client.sock.setblocking(0)
        self.client.sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
