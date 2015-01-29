""" Base classes for clients and connections of x/84. """

import array
import errno
import logging
import socket
import threading
import time
import warnings

# local
from x84.bbs.exception import Disconnected
from x84.terminal import spawn_client_session


class BaseClient(object):

    """
    Base class for remote client implementations.

    Instantiated by the corresponding :class:`BaseServer` class.
    """

    #: Override in subclass: a general string identifier for the
    #: connecting protocol (for example, 'telnet', 'ssh', 'rlogin')
    kind = None

    #: maximum unit of data received for each call to socket_recv()
    BLOCKSIZE_RECV = 64

    #: terminal type identifier when not yet negotiated
    TTYPE_UNDETECTED = 'unknown'

    def __init__(self, sock, address_pair, on_naws=None):
        """ Class initializer. """
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

    def close(self):
        """ Close connection with the client. """
        self.shutdown()

    def fileno(self):
        """ File descriptor number of socket. """
        try:
            return self.sock.fileno()
        except socket.error:
            return None

    def input_ready(self):
        """ Whether any data is buffered for reading. """
        return bool(self.recv_buffer.__len__())

    def recv_ready(self):
        """
        Subclass and implement: whether socket_recv() should be called.

        :raises NotImplementedError
        """
        raise NotImplementedError()

    def send(self):
        """
        Send any data buffered and return number of bytes send.

        :raises Disconnected: client has disconnected (cannot write to socket).
        """
        if not self.send_ready():
            warnings.warn('send() called on empty buffer', RuntimeWarning, 2)
            return 0

        ready_bytes = bytes(''.join(self.send_buffer))
        self.send_buffer = array.array('c')

        def _send(send_bytes):
            """
            Inner low-level function for socket send.

            :raises Disconnected: on sock.send error.
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
        """ Whether any data is buffered for delivery. """
        return bool(self.send_buffer.__len__())

    def shutdown(self):
        """
        Shutdown and close socket.

        Called by event loop after client is marked by :meth:`deactivate`.
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
        Receive data from socket, returns number of bytes received.

        :raises Disconnect: client has disconnected.
        :rtype: int
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

    def get_input(self):
        """
        Receive input from client into ``self.recv_buffer``.

        Should be called conditionally when :meth:`input_ready` returns True.
        """
        data = self.recv_buffer.tostring()
        self.recv_buffer = array.array('c')
        return data

    def send_str(self, bstr):
        """ Buffer bytestring for client. """
        self.send_buffer.fromstring(bstr)

    def send_unicode(self, ucs, encoding='utf8'):
        """ Buffer unicode string, encoded for client as 'encoding'. """
        self.send_str(ucs.encode(encoding, 'replace'))

    def is_active(self):
        """ Whether this connection is active (bool). """
        return self.active

    def deactivate(self):
        """ Flag client for disconnection by engine loop. """
        if self.active:
            self.active = False
            self.log.debug('{self.addrport}: deactivated'.format(self=self))

    def idle(self):
        """ Time elapsed since data was last received. """
        return time.time() - self.last_input_time

    def duration(self):
        """ Time elapsed since connection was made. """
        return time.time() - self.connect_time

    @property
    def addrport(self):
        """ IP address and port of connection as string (ip:port). """
        return '%s:%d' % (self.address_pair[0], self.address_pair[1])


class BaseConnect(threading.Thread):

    """ Base class for client connect factories. """

    #: whether this thread is completed. Set to ``True`` to cause an on-connect
    #: thread to forcefully exit.
    stopped = False

    def __init__(self, client):
        """ Class initializer. """
        self.client = client
        threading.Thread.__init__(self)
        self.log = logging.getLogger(self.__class__.__name__)

    def banner(self):
        """ Write data on-connect, callback from :meth:`run`. """
        pass

    def run(self):
        """
        Negotiate a connecting session.

        In the case of telnet and ssh, for example, negotiates and
        inquires about terminal type, telnet options, window size,
        and tcp socket options before spawning a new session.
        """
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

        Callback from :meth:`run`.
        """
        self.client.sock.setblocking(0)
        self.client.sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
