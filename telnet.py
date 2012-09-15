# -*- coding: utf-8 -*-

#  This is a modified version of miniboa. most significant changes are
#  character-at-a-time input instead of linemode, encoding option on send,
#  charset negotiation, strict rejection of linemode, (fixed?) terminal type
#  detection, added .telnet_eight_bit boolean to client

#------------------------------------------------------------------------------
#   miniboa/async.py
#   miniboa/telnet.py
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

This is a modified version of miniboa retrieved from
svn address http://miniboa.googlecode.com/svn/trunk/miniboa
"""

import socket
import select
import time
import sys
import logging
from bbs import exception
logger = logging.getLogger(__name__)
logger.setLevel (logging.DEBUG)

class TelnetServer(object):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """
    MAX_CONNECTIONS=1000
    def __init__(self, port, address, on_connect, on_disconnect, on_naws,
        timeout):
        """
        Create a new Telnet Server.

        port -- Port to listen for new connection on.

        address -- bind ip address. default is loopback address, which is not
        accessible over the network. For that, use '0.0.0.0' for 'any', or a
        static ip address.

        on_connect -- function to call when a new connection is received
        with TelnetClient() instance passed as an argument

        on_disconnect -- function to call when a connection is lost.

        on_naws -- function to call when client negotiates about window size

        timeout -- amount of time the select() call waits for input in poll()
        """

        self.port = port
        self.address = address
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_naws = on_naws
        self.timeout = timeout

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_socket.bind((address, port))
            server_socket.listen(5)
        except socket.error, e:
            logger.error ('Unable to bind: %s' % (e,))
            sys.exit (1)

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

        ## Delete inactive connections
        for client in (c for c in self.clients.values() if c.active is False):
          if self.on_disconnect is not None:
            self.on_disconnect (client)
          client.sock.close ()
          logger.debug ('%s: deleted', client.addrport())
          del self.clients[client.fileno]

        ## Build a list of connections to test for receive data
        recv_list = [self.server_fileno] + [client.fileno \
            for client in self.clients.values()]

        ## Build a list of connections that have data to receieve
        rlist, slist, elist = select.select(recv_list, [], [], self.timeout)

        if self.server_fileno in rlist:
          try:
            sock, addr_tup = self.server_socket.accept()
          except socket.error, e:
            logger.error ('accept error %d:%s' % (e[0], e[1],))
            return

          ## Check for maximum connections
          if self.client_count() < self.MAX_CONNECTIONS:
            client = TelnetClient(sock, addr_tup)
            ## on_naws inherited by client
            client.on_naws = self.on_naws
            ## Add the connection to our dictionary and call handler
            self.clients[client.fileno] = client
            self.on_connect (client)
          else:
            logger.error ('refused new connect; maximum reached.')
            sock.close()

        ## Process sockets with data to receive
        recv_ready = (self.clients[f] for f in rlist if f!=self.server_fileno)
        for client in recv_ready:
          try:
            client.socket_recv ()
          except exception.ConnectionClosed, e:
            logger.info ('%s connection closed%s.' %
                (client.addrport(), ': %s' % (e,) if len(str(e))!=0 else ''))
            client.deactivate()

        ## Process sockets with data to send
        send_ready = (c for c in self.clients.values() if c.active)
        for client in send_ready:
          try:
            client.socket_send ()
          except exception.ConnectionClosed, e:
            logger.debug ('%s connection closed%s.' %
                (client.addrport(), ': %s' % (e,) if len(str(e))!=0 else ''))
            client.deactivate()

#---[ Telnet Notes ]-----------------------------------------------------------
# (See RFC 854 for more information)
#
# Negotiating a Local Option
# --------------------------
#
# Side A begins with:
#
#    "IAC WILL/WONT XX"   Meaning "I would like to [use|not use] option XX."
#
# Side B replies with either:
#
#    "IAC DO XX"     Meaning "OK, you may use option XX."
#    "IAC DONT XX"   Meaning "No, you cannot use option XX."
#
#
# Negotiating a Remote Option
# ----------------------------
#
# Side A begins with:
#
#    "IAC DO/DONT XX"  Meaning "I would like YOU to [use|not use] option XX."
#
# Side B replies with either:
#
#    "IAC WILL XX"   Meaning "I will begin using option XX"
#    "IAC WONT XX"   Meaning "I will not begin using option XX"
#
#
# The syntax is designed so that if both parties receive simultaneous requests
# for the same option, each will see the other's request as a positive
# acknowledgement of it's own.
#
# If a party receives a request to enter a mode that it is already in, the
# request should not be acknowledged.

## Where you see DE in my comments I mean 'Distant End', e.g. the client.

UNKNOWN = -1

#--[ Telnet Commands ]---------------------------------------------------------

EC      = chr(247)      # Erase Character
EL      = chr(248)      # Erase Line
GA      = chr(249)      # The Go Ahead Signal
SB      = chr(250)      # Sub-option to follow
WILL    = chr(251)      # Will; request or confirm option begin
WONT    = chr(252)      # Wont; deny option request
DO      = chr(253)      # Do = Request or confirm remote option
DONT    = chr(254)      # Don't = Demand or confirm option halt
IAC     = chr(255)      # Interpret as Command
SEND    = chr(1)        # Sub-process negotiation SEND command
IS      = chr(0)        # Sub-process negotiation IS command

#--[ Telnet Options ]----------------------------------------------------------

BINARY  = chr(0)      # Transmit Binary
TTYPE   = chr(24)      # Terminal Type
CHARSET = chr(42)      # Character set

# Copyright (c) 2001-2009 Twisted Matrix Laboratories.

NULL =           chr(0)   # No operation.
BEL =            chr(7)   # Produces an audible or
                          # visible signal (which does
                          # NOT move the print head).
BS =             chr(8)   # Moves the print head one
                          # character position towards
                          # the left margin.
HT =             chr(9)   # Moves the printer to the
                          # next horizontal tab stop.
                          # It remains unspecified how
                          # either party determines or
                          # establishes where such tab
                          # stops are located.
LF =             chr(10)  # Moves the printer to the
                          # next print line, keeping the
                          # same horizontal position.
VT =             chr(11)  # Moves the printer to the
                          # next vertical tab stop.  It
                          # remains unspecified how
                          # either party determines or
                          # establishes where such tab
                          # stops are located.
FF =             chr(12)  # Moves the printer to the top
                          # of the next page, keeping
                          # the same horizontal position.
CR =             chr(13)  # Moves the printer to the left
                          # margin of the current line.
ECHO  =          chr(1)   # User-to-Server:  Asks the server to send
                          # Echos of the transmitted data.
SGA =            chr(3)   # Suppress Go Ahead.  Go Ahead is silly
                          # and most modern servers should suppress
                          # it.
NAWS =           chr(31)  # Negotiate About Window Size.  Indicate that
                          # information about the size of the terminal
                          # can be communicated.
LINEMODE =       chr(34)  # Allow line buffering to be
                          # negotiated about.
SE =             chr(240) # End of subnegotiation parameters.
NOP =            chr(241) # No operation.
DM =             chr(242) # "Data Mark": The data stream portion
                          # of a Synch.  This should always be
                          # accompanied by a TCP Urgent
                          # notification.
BRK =            chr(243) # NVT character Break.
IP =             chr(244) # The function Interrupt Process.
AO =             chr(245) # The function Abort Output
AYT =            chr(246) # The function Are You There.#

#-----------------------------------------------------------------Telnet Option

class TelnetOption(object):
    """
    Simple class used to track the status of an extended Telnet option.
    """
    def __init__(self):
        self.local_option = UNKNOWN     # Local state of an option
        self.remote_option = UNKNOWN    # Remote state of an option
        self.reply_pending = False      # Are we expecting a reply?


#------------------------------------------------------------------------Telnet

class TelnetClient(object):
    """
    Represents a client connection via Telnet.

    First argument is the socket discovered by the Telnet Server.
    Second argument is the tuple (ip address, port number).
    """
    BLOCKSIZE_RECV=2048

    def __init__(self, sock, addr_tup):
        self.protocol = 'telnet'
        self.active = True          # Turns False when the connection is lost
        self.sock = sock            # The connection's socket
        self.fileno = sock.fileno() # The socket's file descriptor
        self.address = addr_tup[0]  # The client's remote TCP/IP address
        self.port = addr_tup[1]     # The client's remote port
        self.terminal_type = 'unknown client' # set via request_terminal_type()
        self.charset = 'unknown encoding' # set via request_terminal_charset()
        self.use_ansi = True
        self.columns = None
        self.rows = None
        self.on_naws = None         # callback for window resize events
        self.send_buffer = bytes()
        self.recv_buffer = bytes()
        self.bytes_sent = 0
        self.bytes_received = 0
        self.connect_time = time.time()
        self.last_input_time = time.time()

        ## State variables for interpreting incoming telnet commands
        self.telnet_got_iac = False  # Are we inside an IAC sequence?
        self.telnet_got_cmd = None   # Did we get a telnet command?
        self.telnet_got_sb = False   # Are we inside a subnegotiation?
        self.telnet_opt_dict = {}    # Mapping for up to 256 TelnetOptions
        self.telnet_echo = False     # Echo input back to the client?
        self.telnet_eight_bit = False# Allow transfer of non-ascii characters?
        self.telnet_sb_buffer = ''   # Buffer for sub-negotiations

    def name_option(self, option):
      v = ';?'.join([k for k,v in globals().iteritems() if option == v and
        k not in ('NULL','SEND','IS',)])
      return v if v != '' else ord(option)

    def get_input(self):
        """
        Get any input bytes received from the DE. The input_ready method
        returns True when bytes are available.
        """
        data = self.recv_buffer
        self.recv_buffer = ''
        return data

    def send(self, text, encoding=None):
        """
        Send bytestring to the distant end. If text is unicode,
        encode as ascii if self.eight_bit is False, otherwise as iso8859-1
        unless otherwise specified.
        """
        enc = encoding if encoding is not None else self.charset
        try:
          self.send_buffer += bytes(text) \
              if type(text) is not unicode \
              else text.encode (enc)
        except UnicodeEncodeError, e:
          if enc != 'ascii':
            raise
          # if the terminal cannot negotiate BINARY (8-bit), and encoding has
          # not been specified, then try as iso8859-1, which should allow
          # bytes between 127 and 255 through
          logger.warn ('%s: UnicodeEncodeError: %s; '
            're-trying as iso8859-1 on 7-bit ascii terminal!',
              self.addrport(), e)
          self.send_buffer += bytes(text) \
              if type(text) is not unicode \
              else text.encode ('iso8859-1')

    def deactivate(self):
        """
        Set the client to disconnect on the next server poll.
        """
        logger.debug ('%s: marked for deactivation', self.addrport())
        self.active = False

    def addrport(self):
        """
        Return the DE's IP address and port number as a string.
        """
        return "%s:%s" % (self.address, self.port)

    def idle(self):
        """
        Returns the number of seconds that have elasped since the DE
        last sent us some input.
        """
        return time.time() - self.last_input_time

    def duration(self):
        """
        Returns the number of seconds the DE has been connected.
        """
        return time.time() - self.connect_time

    def request_do_sga(self):
        """
        Request DE to Suppress Go-Ahead.  See RFC 858.
        """
        self._iac_do(SGA)
        self._note_reply_pending(SGA, True)

    def request_will_echo(self):
        """
        Tell the DE that we would like to echo their text.  See RFC 857.
        """
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)
        self.telnet_echo = True

    def request_wont_echo(self):
        """
        Tell the DE that we would like to stop echoing their text.
        See RFC 857.
        """
        self._iac_wont(ECHO)
        self._note_reply_pending(ECHO, True)
        self.telnet_echo = False

    def request_do_binary(self):
        """
        Request to use BINARY telnet mode (telnet -8 hostname). See RFC ....
        """
        self._iac_do(BINARY)
        self._note_reply_pending(BINARY, True)

    def request_do_naws(self):
        """
        Request to Negotiate About Window Size.  See RFC 1073.
        """
        self._iac_do(NAWS)
        self._note_reply_pending(NAWS, True)

    def request_do_charset(self):
        """
        Request terminal character set. See RFC 2066.
        """
        self._iac_do(CHARSET)
        self._note_reply_pending(CHARSET, True)

    def request_ttype(self):
        """
        Request sub-negotiation ttype.  See RFC 779.
        A successful response will set self.terminal_type.
        """
        self.send (bytes(''.join((IAC, SB, TTYPE, SEND, IAC, SE))))

    def send_ready(self):
        """
        Return True if any data is buffered for sending (screen output).
        """
        return bool(0 != len(self.send_buffer))

    def input_ready(self):
        """
        Return True if any data is buffered for reading (keyboard input).
        """
        return bool(0 != len(self.recv_buffer))

    def socket_send(self):
        """
        Called by TelnetServer.poll() when send data is ready.  Send any
        data buffered, trim self.send_buffer to bytes sent, and return
        number of bytes sent. exception.ConnectionClosed may be raised.
        """
        bytes_sent = 0
        try:
          bytes_sent = self.sock.send(self.send_buffer)
        except socket.error, e:
          raise exception.ConnectionClosed('socket send %d:%s' % (e[0], e[1],))
        self.bytes_sent += bytes_sent
        self.send_buffer = self.send_buffer[bytes_sent:]
        return bytes_sent

    def socket_recv(self):
        """
        Called by TelnetServer.poll() when recv data is ready.  Read any
        data on socket, processing telnet commands, and buffering all
        other bytestrings to self.recv_buffer.  If data is not received,
        or the connection is closed, exception.ConnectionClosed is raised.
        """
        bytes_received = 0
        try:
          data = self.sock.recv (self.BLOCKSIZE_RECV)
          bytes_received = len(data)
          if 0 == bytes_received:
            raise exception.ConnectionClosed ('client disconnected')
        except socket.error, e:
          raise exception.ConnectionClosed('socket errorno %d: %s' % (e[0], e[1],))

        self.bytes_received += bytes_received
        self.last_input_time = time.time()

        ## Test for telnet commands, non-telnet bytes
        ## are pushed to self.recv_buffer (side-effect),
        map(self._iac_sniffer, data)
        return bytes_received

    def _recv_byte(self, byte):
        """
        Buffer non-telnet commands bytestrings into recv_buffer.
        """
        self.recv_buffer += byte

    def _iac_sniffer(self, byte):
        """
        Watches incomming data for Telnet IAC sequences.
        Passes the data, if any, with the IAC commands stripped to
        _recv_byte().
        """
        ## Are we not currently in an IAC sequence coming from the DE?
        if self.telnet_got_iac is False:
            if byte == IAC:
                self.telnet_got_iac = True
            ## Are we currenty in a sub-negotion?
            elif self.telnet_got_sb is True:
                ## Sanity check on length
                assert len(self.telnet_sb_buffer) < 64, \
                    'sub-negotiation buffer full: %r' \
                    % (self.telnet_sb_buffer,)
                self.telnet_sb_buffer += byte
            else:
                ## Just a normal NVT character
                self._recv_byte(byte)
            return

        else:
            ## Did we get sent a second IAC?
            if byte == IAC and self.telnet_got_sb is True:
                ## Must be an escaped 255 (IAC + IAC)
                self.telnet_sb_buffer += byte
                self.telnet_got_iac = False
                return

            ## Do we already have an IAC + CMD?
            elif self.telnet_got_cmd:
                ## Yes, so handle the option
                self._three_byte_cmd(byte)
                return

            ## We have IAC but no CMD
            else:

                ## Is this the middle byte of a three-byte command?
                if byte == DO:
                    self.telnet_got_cmd = DO
                    return

                elif byte == DONT:
                    self.telnet_got_cmd = DONT
                    return

                elif byte == WILL:
                    self.telnet_got_cmd = WILL
                    return

                elif byte == WONT:
                    self.telnet_got_cmd = WONT
                    return

                else:
                    ## Nope, must be a two-byte command
                    self._two_byte_cmd(byte)


    def _two_byte_cmd(self, cmd):
        """
        Handle incoming Telnet commands that are two bytes long.
        """
        logger.debug ('_two_byte_cmd %s' % (self.name_option(cmd),))

        if cmd == SB:
            ## Begin capturing a sub-negotiation string
            self.telnet_got_sb = True
            self.telnet_sb_buffer = ''

        elif cmd == SE:
            ## Stop capturing a sub-negotiation string
            self.telnet_got_sb = False
            self._sb_decoder()

        elif cmd in (NOP, IP, AO, AYT, EC, EL, GA, DM):
            pass

        else:
          logger.error ('_two_byte_cmd invalid: %r'  % (ord(cmd),))

        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _three_byte_cmd(self, option):
        """
        Handle incoming Telnet commmands that are three bytes long.
        """
        cmd = self.telnet_got_cmd
        logger.debug ('_three_byte_cmd %s %s' % (self.name_option(cmd),
          self.name_option(option),))

        ## Incoming DO's and DONT's refer to the status of this end

        #---[ DO ]-------------------------------------------------------------

        if cmd == DO:

            if option == BINARY:

                if self._check_reply_pending(BINARY):
                    self._note_reply_pending(BINARY, False)
                    self._note_local_option(BINARY, True)
                    self.telnet_eight_bit = True
                    logger.debug ('eight-bit binary enabled')

                elif (self._check_local_option(BINARY) is False or
                        self._check_local_option(BINARY) is UNKNOWN):
                    self._note_local_option(BINARY, True)
                    self.telnet_eight_bit = True
                    logger.debug ('eight-bit binary enabled')
                    self._iac_will(BINARY)

            elif option == ECHO:

                if self._check_reply_pending(ECHO):
                    self._note_reply_pending(ECHO, False)
                    self._note_local_option(ECHO, True)

                elif (self._check_local_option(ECHO) is False or
                        self._check_local_option(ECHO) is UNKNOWN):
                    self._note_local_option(ECHO, True)
                    self._iac_will(ECHO)
                    self.telnet_echo = True

            elif option == SGA:

                if self._check_reply_pending(SGA):
                    self._note_reply_pending(SGA, False)
                    self._note_local_option(SGA, True)

                elif (self._check_local_option(SGA) is False or
                        self._check_local_option(SGA) is UNKNOWN):
                    self._note_local_option(SGA, True)
                    self._iac_will(SGA)

            elif option == LINEMODE:
              if self._check_local_option(option) is UNKNOWN:
                self._note_local_option(option, False)
                self._iac_wont(option)
                logger.warn ('%s: linemode requested but refused.' % \
                    (self.addrport(),))

            else:

                ## ALL OTHER OTHERS = Default to refusing once
                if self._check_local_option(option) is UNKNOWN:
                    self._note_local_option(option, False)
                    logger.warn ('%s: unhandled do: %s; wont.' % \
                        (self.addrport(), self.name_option(option)))
                    self._iac_wont(option)


        #---[ DONT ]-----------------------------------------------------------

        elif cmd == DONT:

            if option == BINARY:
                # client: DONT BINARY, us: ok, we won't.
                if self._check_reply_pending(BINARY):
                    self._note_reply_pending(BINARY, False)
                    self._note_local_option(BINARY, False)

                elif (self._check_local_option(BINARY) is True or
                        self._check_local_option(BINARY) is UNKNOWN):
                    self._note_local_option(BINARY, False)
                    self._iac_wont(BINARY)
                    ## Just nod

            elif option == ECHO:
                # client: DONT ECHO, us: ok, we won't (but we will anyway)
                if self._check_reply_pending(ECHO):
                    self._note_reply_pending(ECHO, False)
                    self._note_local_option(ECHO, True)
                    self.telnet_echo = False

                elif (self._check_local_option(BINARY) is True or
                        self._check_local_option(BINARY) is UNKNOWN):
                    self._note_local_option(ECHO, False)
                    self._iac_wont(ECHO)
                    self.telnet_echo = False

            elif option == SGA:
                # client: DONT SGA, us: ok, we won't
                if self._check_reply_pending(SGA):
                    self._note_reply_pending(SGA, False)
                    self._note_local_option(SGA, False)

                elif (self._check_remote_option(SGA) is True or
                        self._check_remote_option(SGA) is UNKNOWN):
                    self._note_local_option(SGA, False)
                    self._iac_wont(SGA)

            elif option == LINEMODE:
                # client: DONT LINEMODE, us: ok, we won't
                if self._check_reply_pending(LINEMODE):
                    self._note_reply_pending(LINEMODE, False)
                    self._note_local_option(LINEMODE, False)

                elif (self._check_remote_option(LINEMODE) is True or
                        self._check_remote_option(LINEMODE) is UNKNOWN):
                    self._note_local_option(LINEMODE, False)
                    self._iac_wont(LINEMODE)

            else:
                ## ALL OTHER OPTIONS = Default to ignoring
                logger.warn ('%s: unhandled dont: %s.' % \
                    (self.addrport(), self.name_option(option)))
                pass


        ## Incoming WILL's and WONT's refer to the status of the DE

        #---[ WILL ]-----------------------------------------------------------

        elif cmd == WILL:

            if option == ECHO:

                ## Nutjob DE offering to echo the server...
                if self._check_remote_option(ECHO) is UNKNOWN:
                    self._note_remote_option(ECHO, False)
                    # No no, bad DE!
                    self._iac_dont(ECHO)

            elif option == NAWS:

                if self._check_reply_pending(NAWS):
                    self._note_reply_pending(NAWS, False)
                    self._note_remote_option(NAWS, True)
                    ## Nothing else to do, client follow with SB

                elif (self._check_remote_option(NAWS) is False or
                        self._check_remote_option(NAWS) is UNKNOWN):
                    self._note_remote_option(NAWS, True)
                    self._iac_do(NAWS)
                    ## Client should respond with SB

            elif option == SGA:

                if self._check_reply_pending(SGA):
                    self._note_reply_pending(SGA, False)
                    self._note_remote_option(SGA, True)
                    self._note_local_option(SGA, True) # ?

                elif (self._check_remote_option(SGA) is False or
                        self._check_remote_option(SGA) is UNKNOWN):
                    self._note_remote_option(SGA, True)
                    self._note_local_option(SGA, True) # ?
                    self._iac_do(SGA)
                    ## Just nod

            elif option == TTYPE:

                if self._check_reply_pending(TTYPE):
                    self._note_reply_pending(TTYPE, False)
                    self._note_remote_option(TTYPE, True)
                    ## Tell them to send their terminal type
                    self.send (bytes(''.join((IAC, SB, TTYPE, SEND, IAC, SE))))

                elif (self._check_remote_option(TTYPE) is False or
                        self._check_remote_option(TTYPE) is UNKNOWN):
                    self._note_remote_option(TTYPE, True)
                    self._iac_do(TTYPE)

            # linemode is for girls .. ?
            elif option == LINEMODE:
              if self._check_remote_option(LINEMODE) is UNKNOWN:
                  self._note_remote_option(LINEMODE, False)
                  self._iac_dont(LINEMODE)

            elif option == BINARY:
              if self._check_remote_option(BINARY) is UNKNOWN:
                  self._note_remote_option(BINARY, True)
                  self._iac_do(BINARY)
                  self.telnet_eight_bit = True
                  logger.debug ('eight-bit binary enabled')

            else:
                ## ALL OTHER OPTIONS = Default to ignoring
                logger.debug ('%s: unhandled will: %s.' % \
                    (self.addrport(), self.name_option(option)))
                pass

        #---[ WONT ]-----------------------------------------------------------

        elif cmd == WONT:

            if option == ECHO:

                ## DE states it wont echo us -- good, they're not suppose to.
                if self._check_remote_option(ECHO) is UNKNOWN:
                    self._note_remote_option(ECHO, False)
                    self._iac_dont(ECHO)

            elif option == SGA:

                if self._check_reply_pending(SGA):
                    self._note_reply_pending(SGA, False)
                    self._note_remote_option(SGA, False)

                elif (self._check_remote_option(SGA) is True or
                        self._check_remote_option(SGA) is UNKNOWN):
                    self._note_remote_option(SGA, False)
                    self._iac_dont(SGA)

                if self._check_reply_pending(TTYPE):
                    self._note_reply_pending(TTYPE, False)
                    self._note_remote_option(TTYPE, False)

                elif (self._check_remote_option(TTYPE) is True or
                        self._check_remote_option(TTYPE) is UNKNOWN):
                    self._note_remote_option(TTYPE, False)
                    self._iac_dont(TTYPE)

            elif option == CHARSET:
                if self._check_reply_pending(CHARSET):
                  self._note_reply_pending(CHARSET, False)

            else:
                logger.debug ('%s: unhandled wont: %s.' % \
                    (self.addrport(), self.name_option(option)))
                pass

        else:
            logger.warn ('%s: unhandled _three_byte_cmd: %s.' % \
                (self.addrport(), self.name_option(option)))

        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _sb_decoder(self):
        """
        Figures out what to do with a received sub-negotiation block.
        """
        bloc = self.telnet_sb_buffer
        if len(bloc) > 2:

            if bloc[0] == TTYPE and bloc[1] == IS:
                self.terminal_type = bloc[2:].lower()
                logger.debug ('%s: terminal type %s' % \
                    (self.addrport(), self.terminal_type,))

            if bloc[0] == NAWS:
                if len(bloc) != 5:
                    logger.error('%s: bad length in NAWS block (%d)' % \
                        (self.addrport(), len(block),))
                else:
                    self.columns = (256 * ord(bloc[1])) + ord(bloc[2])
                    self.rows = (256 * ord(bloc[3])) + ord(bloc[4])
                    logger.debug ('%s: window size is %dx%d' % \
                        (self.addrport(), self.columns, self.rows))
                    if self.on_naws is not None:
                      self.on_naws (self)

        self.telnet_sb_buffer = ''


    #---[ State Juggling for Telnet Options ]----------------------------------

    ## Sometimes verbiage is tricky.  I use 'note' rather than 'set' here
    ## because (to me) set infers something happened.

    def _check_local_option(self, option):
        """Test the status of local negotiated Telnet options."""
        logger.debug ('check_local_option, %s' % (self.name_option(option,)))
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].local_option

    def _note_local_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        logger.debug ('note_local_option, %s, %s' \
            % (self.name_option(option,), state,))
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].local_option = state

    def _check_remote_option(self, option):
        """Test the status of remote negotiated Telnet options."""
        logger.debug ('check_remote_option, %s' \
            % (self.name_option(option,)))
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].remote_option

    def _note_remote_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        logger.debug ('note_remote_option, %s, %s' \
            % (self.name_option(option), state,))
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].remote_option = state

    def _check_reply_pending(self, option):
        """Test the status of requested Telnet options."""
        logger.debug ('check_reply_pending, %s' \
            % (self.name_option(option),))
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].reply_pending

    def _note_reply_pending(self, option, state):
        """Record the status of requested Telnet options."""
        logger.debug ('note_reply_pending, %s, %s' \
            % (self.name_option(option), state,))
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].reply_pending = state


    #---[ Telnet Command Shortcuts ]-------------------------------------------

    def _iac_do(self, option):
        """Send a Telnet IAC "DO" sequence."""
        logger.debug ('IAC DO %s' % (self.name_option(option)))
        self.send (bytes(''.join((IAC, DO, option))))

    def _iac_dont(self, option):
        """Send a Telnet IAC "DONT" sequence."""
        logger.debug ('IAC DONT %s' % (self.name_option(option)))
        self.send (bytes(''.join((IAC, DONT, option))))

    def _iac_will(self, option):
        """Send a Telnet IAC "WILL" sequence."""
        logger.debug ('IAC WILL %s' % (self.name_option(option)))
        self.send (bytes(''.join((IAC, WILL, option))))

    def _iac_wont(self, option):
        """Send a Telnet IAC "WONT" sequence."""
        logger.debug ('IAC WONT %s' % (self.name_option(option)))
        self.send (bytes(''.join((IAC, WONT, option))))
