# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
#   miniboa/async.py
#   Copyright 2009 Jim Storch
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain a
#   copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#------------------------------------------------------------------------------

"""
Handle Asynchronous Telnet Connections.
"""

import socket
import select
import sys

from miniboa.telnet import TelnetClient
from miniboa.error import BogConnectionLost

## Cap sockets to 512 on Windows because winsock can only process 512 at time
if sys.platform == 'win32':
    MAX_CONNECTIONS = 500
## Cap sockets to 1000 on Linux because you can only have 1024 file descriptors
else:
    MAX_CONNECTIONS = 1000


#-----------------------------------------------------Dummy Connection Handlers

def _on_connect(client):
    """
    Placeholder new connection handler.
    """
    print "++ Opened connection to %s, sending greeting..." % client.addrport()
    client.send("Greetings from Miniboa! "
        " Now it's time to add your code.\n")

def _on_disconnect(client):
    """
    Placeholder lost connection handler.
    """
    print "-- Lost connection to %s" % client.addrport()


#-----------------------------------------------------------------Telnet Server

class TelnetServer(object):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """
    def __init__(self, port=7777, address='', on_connect=_on_connect,
            on_disconnect=_on_disconnect, timeout=0.005):
        """
        Create a new Telnet Server.

        port -- Port to listen for new connection on.  On UNIX-like platforms,
            you made need root access to use ports under 1025.

        address -- Address of the LOCAL network interface to listen on.  You
            can usually leave this blank unless you want to restrict traffic
            to a specific network device.  This will usually NOT be the same
            as the Internet address of your server.

        on_connect -- function to call with new telnet connections

        on_disconnect -- function to call when a client's connection dies,
            either through a terminated session or client.active being set
            to False.

        timeout -- amount of time that Poll() will wait from user inport
            before returning.  Also frees a slice of CPU time.
        """

        self.port = port
        self.address = address
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.timeout = timeout

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind((address, port))
            server_socket.listen(5)
        except socket.error, err:
            print >> sys.stderr, "Unable to create the server socket:", err
            sys.exit(1)

        self.server_socket = server_socket
        self.server_fileno = server_socket.fileno()

        ## Dictionary of active clients,
        ## key = file descriptor, value = TelnetClient (see miniboa.telnet)
        self.clients = {}

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


    def poll(self):
        """
        Perform a non-blocking scan of recv and send states on the server
        and client connection sockets.  Process new connection requests,
        read incomming data, and send outgoing data.  Sends and receives may
        be partial.
        """

        ## Delete inactive connections from the dictionary
        for client in [c for c in self.clients.values() if not c.active]:
          self.on_disconnect (client)
          del self.clients[client.fileno]

        ## Build a list of connections to test for receive data pending
        recv_list = [self.server_fileno] + [client.fileno \
            for client in self.clients.values()]

        ## Build a list of connections that need to send data
        try:
            rlist, slist, elist = select.select(recv_list, [], [], self.timeout)

        except select.error, err:
            ## If we can't even use select(), game over man, game over
            print >> sys.stderr, ("!! FATAL SELECT error '%d:%s'!"
                % (err[0], err[1]))
            sys.exit(1)

        if self.server_fileno in rlist:
            try:
                sock, addr_tup = self.server_socket.accept()

            except socket.error, err:
                print >> sys.stderr, ("!! ACCEPT error '%d:%s'." %
                    (err[0], err[1]))
            ## Check for maximum connections
            if self.client_count() < MAX_CONNECTIONS:
              client = TelnetClient(sock, addr_tup)
              #print "++ Opened connection to %s" % client.addrport()
              ## Add the connection to our dictionary and call handler
              self.clients[client.fileno] = client
              self.on_connect(client)
            else:
                print '?? Refusing new connection; maximum in use.'
                sock.close()

        ## Process socket file descriptors with data to recieve
        for sock_fileno in [r for r in rlist if r != self.server_fileno]:
            try:
                self.clients[sock_fileno].socket_recv()
            except BogConnectionLost:
                self.clients[sock_fileno].deactivate()

        ## Process sockets with data to send
        for sock_fileno in [client.fileno \
          for client in self.clients.values() if client.send_pending]:
            self.clients[sock_fileno].socket_send()
