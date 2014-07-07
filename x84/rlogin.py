'''
rlogin server for x84, https://github.com/jquast/x84
'''

import array
import logging
import socket
import time

# local
from .client import BaseClient, BaseConnect
from .server import BaseServer


class RLoginClient(BaseClient):
    '''
    rlogin protocol client handler.
    '''

    def __init__(self, sock, address_pair, on_naws=None):
        super(RLoginClient, self).__init__(sock, address_pair, on_naws)

        # Urgent packet buffers
        self.usend_buffer = array.array('c')
        self.urecv_buffer = array.array('c')

    def get_urgent_input(self):
        '''
        Retrieves data from the urgent (out of band) receive buffer.
        '''
        data = self.urecv_buffer.tostring()
        self.urecv_buffer = array.array('c')
        return data

    def recv_ready(self):
        return True

    def send(self):
        if len(self.usend_buffer) > 0:
            ready_bytes = bytes(''.join(self.usend_buffer))
            self.usend_buffer = array.array('c')

            def _send_urgent(send_bytes):
                '''
                Sent urgent (out of band) TCP packet.
                '''
                return self.sock.send(send_bytes, socket.MSG_OOB)

            sent = _send_urgent(ready_bytes)
            if sent < len(ready_bytes):
                self.usend_buffer.fromstring(ready_bytes[sent:])

        else:
            super(RLoginClient, self).send()

    def send_ready(self):
        return bool(len(self.send_buffer) + len(self.usend_buffer))

    def send_urgent_str(self, bstr):
        '''
        Buffer urgent (OOB) message to client from bytestring.
        '''
        self.usend_buffer.fromstring(bstr)

    def socket_recv(self):
        # First try to flush out all urgent data
        try:
            data = self.sock.recv(self.BLOCKSIZE_RECV, socket.MSG_OOB)
            recv = len(data)
            if recv:
                self.bytes_received += recv
                self.urecv_buffer.fromstring(data)

        except socket.error:
            pass

        # And now handle the "normal" data
        super(RLoginClient, self).socket_recv()


class ConnectRLogin(BaseConnect):
    '''
    rlogin protocol connection handler, takes care of the (initial) handshake,
    terminal and session setup.
    '''

    def banner(self):
        '''
        Read the rlogin/rsh connection details.
        '''
        data = self.client.get_input()
        while data == '':
            time.sleep(0.1)
            data = self.client.get_input()

        try:
            part = data.split('\x00')
            # We need this because SyncTERM is not fully BSD rlogin compliant
            # and leaves out the terminating NULL byte
            if len(part) == 5 and part[4] == '':
                part.pop(4)

            self.client.env['TERM'] = part[3].split('/')[0]
        except ValueError:
            pass

        # Acknowledge client
        self.client.send_str(bytes('\x00'))

        # Request window size information
        self.client.send_urgent_str(bytes('\x80'))

    def _set_sock_opts(self):
        '''
        Set the socket in non-blocking mode.
        '''
        self.client.sock.setblocking(0)
        self.client.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)


class RLoginServer(BaseServer):
    '''
    RLogin/RSH protocol server.
    '''

    client_factory = RLoginClient
    connect_factory = ConnectRLogin

    def __init__(self, config):
        self.log = logging.getLogger(__name__)
        self.config = config
        self.addr = config.get('rlogin', 'addr')
        self.port = config.getint('rlogin', 'port')

        # bind
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.addr, self.port))
            self.server_socket.listen(self.LISTEN_BACKLOG)
        except socket.error as err:
            self.log.error('unable to bind {0}: {1}'.format(
                (self.addr, self.port), err
            ))
            exit(1)

        self.log.info('listening on {self.addr}:{self.port}/tcp'.format(
            self=self
        ))

    def client_fds(self):
        '''
        Returns a list of rlogin client file descriptors.
        '''
        fds = [client.fileno() for client in self.clients.values()]
        # pylint: disable=bad-builtin
        #         You're drunk, pylint
        return filter(None, fds)
