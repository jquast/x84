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

    kind = None        # override in subclass
    BLOCKSIZE_RECV = 64
    SB_MAXLEN = 65534  # maximum length of subnegotiation string, allow
                       # a fairly large one for NEW_ENVIRON negotiation

    def __init__(self, sock, address_pair, on_naws=None):
        self.log = logging.getLogger(self.__class__.__name__)
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

        self.log.info('new %s: %s', self.__class__.__name__, self.addrport)

    ## low level I/O

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
        '''
        Returns True if we have received any data. Subclass in implementation.
        '''
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
                if err[0] == errno.EDEADLK:
                    warnings.warn('%s: %s (bandwidth exceed)' % (
                        self.addrport,
                        err[1],
                    ), RuntimeWarning, 2)
                    return 0
                raise Disconnected('send %d: %s' % (err[0], err[1],))

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
        except socket.error:
            pass
        self.sock.close()
        self.deactivate()
        self.log.info('shutdown %s: %s',
                      self.__class__.__name__, self.addrport)

    def socket_recv(self):
        '''
        Receive data from the client socket.
        '''
        try:
            data = self.sock.recv(self.BLOCKSIZE_RECV)
            recv = len(data)
            if recv == 0:
                raise Disconnected('Closed by client (EOF)')

        except socket.error as err:
            err = tuple(err)
            if err[0] == errno.EWOULDBLOCK:
                return
            else:
                if len(err) == 1:
                    err = (-1,) + err
                raise Disconnected('socket errno %d: %s' % (err[0], err[1],))

        self.bytes_received += recv
        self.last_input_time = time.time()
        self.recv_buffer.fromstring(data)

    ## high level I/O

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
        ## Must be escaped 255 (IAC + IAC) to avoid IAC intepretation
        self.send_str(ucs.encode(encoding, 'replace')
                      .replace(chr(255), 2 * chr(255)))

    ## activity

    def is_active(self):
        """
        Returns True if this connection is still active.
        """
        return self.active

    def deactivate(self):
        """
        Flag client for disconnection.
        """
        if not self.active:
            self.log.debug('%s: already deactivated', self.addrport)
            return
        self.log.debug('%s: deactivated', self.addrport)
        self.active = False

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

    ## client information

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

    is_binary = True

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
                spawn_client_session(client=self.client)
        except (Disconnected, socket.error) as err:
            self.log.debug('Connection closed: %s', err)
            self.client.deactivate()

    def _set_socket_opts(self):
        """
        Set socket non-blocking and enable TCP KeepAlive.
        """
        self.client.sock.setblocking(0)
        self.client.sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
