# -*- coding: utf-8 -*-

#  This is a modified version of miniboa.
# TODO: Merge back into miniboa as a pull request if author is interested ?
#  most significant changes are
#  character-at-a-time input instead of linemode, encoding option on send,
#  strict rejection of linemode, (fixed?) terminal type
#  detection, #  environment variable support,

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

import inspect
import socket
import select
import array
import time
import sys
import os
import logging
logger = logging.getLogger(__name__)
logger.setLevel (logging.DEBUG)

#--[ Telnet Options ]----------------------------------------------------------
from telnetlib import BINARY, SGA, ECHO, STATUS, TTYPE, LINEMODE
from telnetlib import NAWS, NEW_ENVIRON
from telnetlib import COM_PORT_OPTION, ENCRYPT
from telnetlib import IAC, DONT, DO, WONT, WILL
from telnetlib import SE, NOP, DM, BRK, IP, AO, AYT, EC, EL, GA, SB
IS      = chr(0)        # Sub-process negotiation IS command
SEND    = chr(1)        # Sub-process negotiation SEND command
NEGOTIATE_STATUS = (ECHO, SGA, LINEMODE, TTYPE, NAWS, NEW_ENVIRON,)
from bbs import exception

class TelnetServer(object):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """
    MAX_CONNECTIONS = 1000
    def __init__(self, port, address, on_connect, on_disconnect, on_naws,
        timeout):
        """ Create a new Telnet Server.

        Arguments:

        port -- bind port

        address -- bind ip

        on_connect -- this callback receives TelnetClient after a
        connection is initiated.

        on_disconnect -- this callback receives TelnetClient after
        connect is lost.

        on_naws -- this callable receives a TelnetClient when a client
        negotiates about window size (resize event).

        timeout -- number of seconds to wait for socket event for each call to
          the poll method.
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
        except socket.error, err:
            logger.error ('Unable to bind: %s', err,)
            sys.exit (1)

        self.server_socket = server_socket
        self.server_fileno = server_socket.fileno()

        ## Dictionary of active clients,
        ## key = file descriptor, value = TelnetClient (see miniboa.telnet)
        self.clients = {}

        ## Dictionary of environment variables received by negotiation
        self.env = {}

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
            client.sock.close ()
            logger.debug ('%s: deleted', client.addrport())
            del self.clients[client.fileno]
            if self.on_disconnect is not None:
                self.on_disconnect (client)

        ## Build a list of connections to test for receive data
        recv_list = [self.server_fileno] + [c.fileno
            for c in self.clients.values() if c.active]

        ## Build a list of connections that have data to receieve
        #pylint: disable=W0612
        #        Unused variable 'elist'
        rlist, slist, elist = select.select(recv_list, [], [], self.timeout)

        if self.server_fileno in rlist:
            try:
                sock, addr_tup = self.server_socket.accept()
            except socket.error, err:
                logger.error ('accept error %d:%s', err[0], err[1],)
                return

            ## Check for maximum connections
            if self.client_count() < self.MAX_CONNECTIONS:
                client = TelnetClient(sock, addr_tup, self.on_naws)
                ## Add the connection to our dictionary and call handler
                self.clients[client.fileno] = client
                self.on_connect (client)
            else:
                logger.error ('refused new connect; maximum reached.')
                sock.close()

        ## Process sockets with data to receive
        recv_ready = (self.clients[f] for f in rlist
            if f != self.server_fileno)
        for client in recv_ready:
            try:
                client.socket_recv ()
            except exception.ConnectionClosed, err:
                logger.debug ('%s connection closed: %s.',
                        client.addrport(), err)
                client.deactivate()

        ## Process sockets with data to send
        slist = (c for c in self.clients.values()
            if c.active and c.send_ready())
        for client in slist:
            try:
                client.socket_send ()
            except exception.ConnectionClosed, err:
                logger.debug ('%s connection closed: %s.',
                        client.addrport(), err)
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

#-----------------------------------------------------------------Telnet Option

class TelnetOption(object):
    """
    Simple class used to track the status of an extended Telnet option.
    """
    def __init__(self):
        self.local_option = UNKNOWN     # Local state of an option
        self.remote_option = UNKNOWN    # Remote state of an option
        self.reply_pending = False      # Are we expecting a reply?

def name_option(option):
    """
    Perform introspection of global CONSTANTS for equivalent values,
    and return a string that displays its possible meanings
    """
    values = ';?'.join([k for k, v in globals().iteritems()
        if option == v and k not in ('SEND', 'IS',)])
    return values if values != '' else ord(option)

def debug_option(func):
    """ This function is a decorator that debug prints the 'from' address for
        callables decorated with this. This helps during telnet negotiation,
        to understand which function sets or checks local or remote option
        states.
    """
    def wrapper(self, *args):
        """ inner wrapper for debug_option """
        stack = inspect.stack()
        logger.debug ('%s:%s %s(%s%s)',
            os.path.basename(stack[1][1]), stack[1][2],
            func.__name__, name_option(args[0]),
            ', %s' % (args[1],) if len(args) == 2 else '')
        return func(self, *args)
    return wrapper


#------------------------------------------------------------------------Telnet

class TelnetClient(object):
    """
    Represents a client connection via Telnet.

    First argument is the socket discovered by the Telnet Server.
    Second argument is the tuple (ip address, port number).
    """
    BLOCKSIZE_RECV = 64
    SB_MAXLEN = 65534 # maximum length of subnegotiation string, allow
                      # a fairly large one for NEW_ENVIRON negotiation

    def __init__(self, sock, addr_tup, on_naws=None):
        self.sock = sock
        self.address = addr_tup[0]
        self.port = addr_tup[1]
        self.on_naws = on_naws if on_naws is not None else None
        self.fileno = sock.fileno()
        self.active = True
        self.terminal_type = 'unknown'
        self.env = dict()
        self.columns = None
        self.rows = None
        self.send_buffer = array.array('c')
        self.recv_buffer = array.array('c')
        self.telnet_sb_buffer = array.array('c')
        self.bytes_sent = 0
        self.bytes_received = 0
        self.connect_time = time.time()
        self.last_input_time = time.time()
        ## State variables for interpreting incoming telnet commands
        self.telnet_got_iac = False
        self.telnet_got_cmd = None
        self.telnet_got_sb = False
        self.telnet_opt_dict = {}

    def get_input(self):
        """
        Get any input bytes received from the DE. The input_ready method
        returns True when bytes are available.
        """
        data = self.recv_buffer.tostring ()
        self.recv_buffer = array.array('c')
        return data

    def send_str(self, bytestring):
        """
        buffer bytestrings for sending to the distant end.
        """
        self.send_buffer.fromstring (bytestring)

    def send_unicode(self, unibytes, encoding='utf8'):
        """
        buffer unicode data, encoded to bytestrings as 'encoding'
        """
        bytestring = unibytes.encode(encoding, 'replace')
        ## Must be escaped 255 (IAC + IAC) to avoid IAC intepretation
        bytestring = bytestring.replace(chr(255), 2*chr(255))
        self.send_str (bytestring)

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


    def request_will_sga(self):
        """
        Request DE to Suppress Go-Ahead.  See RFC 858.
        """
        self._iac_will(SGA)
        self._note_reply_pending(SGA, True)


    def request_will_echo(self):
        """
        Tell the DE that we would like to echo their text.  See RFC 857.

        The echo option is enabled, usually by the server, to indicate that the
        server will echo every character it receives. A combination of
        "suppress go ahead" and "echo" is called character at a time mode
        meaning that each character is separately transmitted and echoed.

        There is an understanding known as kludge line mode which means that if
        either "suppress go ahead" or "echo" is enabled but not both then
        telnet operates in line at a time mode meaning that complete lines are
        assembled at each end and transmitted in one "go".
        """
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)


    def request_wont_echo(self):
        """
        Tell the DE that we would like to stop echoing their text.
        See RFC 857.
        """
        self._iac_wont(ECHO)
        self._note_reply_pending(ECHO, True)


    def request_do_sga(self):
        """
        Request to Negotiate SGA.  See ...
        """
        self._iac_do(SGA)
        self._note_reply_pending(SGA, True)


    def request_do_naws(self):
        """
        Request to Negotiate About Window Size.  See RFC 1073.
        """
        self._iac_do(NAWS)
        self._note_reply_pending(NAWS, True)

    def request_do_env(self):
        """
        Request to Negotiate About Window Size.  See RFC 1073.
        """
        self._iac_do(NEW_ENVIRON)
        self._note_reply_pending(NEW_ENVIRON, True)
        self.request_env ()

    def request_env(self):
        """
        Request sub-negotiation NEW_ENVIRON. See RFC 1572.
        """
        # chr(0) indicates VAR request,
        #  followed by variable name,
        # chr(3) indicates USERVAR request,
        # chr(0)
        self.send_str (bytes(''.join((IAC, SB, NEW_ENVIRON, SEND, chr(0)))))
        self.send_str (bytes(chr(0).join( \
            ("USER", "TERM", "SHELL", "COLUMNS", "LINES", "LC_CTYPE",
            "XTERM_LOCALE", "DISPLAY", "SSH_CLIENT", "SSH_CONNECTION",
            "SSH_TTY", "HOME", "HOSTNAME", "PWD", "MAIL", "LANG", "PWD",
            "UID", "USER_ID", "EDITOR", "LOGNAME"))))
        self.send_str (bytes(''.join((chr(3), IAC, SE))))

    def request_ttype(self):
        """
        Request sub-negotiation ttype.  See RFC 779.
        A successful response will set self.terminal_type.
        """
        self.send_str (bytes(''.join((IAC, SB, TTYPE, SEND, IAC, SE))))

    def send_ready(self):
        """
        Return True if any data is buffered for sending (screen output).
        """
        return bool(0 != self.send_buffer.__len__())

    def input_ready(self):
        """
        Return True if any data is buffered for reading (keyboard input).
        """
        return bool(0 != self.recv_buffer.__len__())

    def socket_send(self):
        """
        Called by TelnetServer.poll() when send data is ready.  Send any
        data buffered, trim self.send_buffer to bytes sent, and return
        number of bytes sent. exception.ConnectionClosed may be raised.
        """
        sent = 0
        ready_bytes = bytes(''.join(self.send_buffer))
        if 0 == len(ready_bytes):
            logger.warn ('why did you call socket.send() with no data ready?')
            return

        try:
            sent = self.sock.send(ready_bytes)
        except socket.error, err:
            raise exception.ConnectionClosed (
                    'socket send %d:%s' % (err[0], err[1],))
        assert sent > 0 # now, what?
        self.bytes_sent += sent
        self.send_buffer = array.array('c')
        self.send_buffer.fromstring (ready_bytes[sent:])

    def socket_recv(self):
        """
        Called by TelnetServer.poll() when recv data is ready.  Read any
        data on socket, processing telnet commands, and buffering all
        other bytestrings to self.recv_buffer.  If data is not received,
        or the connection is closed, exception.ConnectionClosed is raised.
        """
        recv = 0
        try:
            data = self.sock.recv (self.BLOCKSIZE_RECV)
            recv = len(data)
            if 0 == recv:
                raise exception.ConnectionClosed ('Client closed connection')
        except socket.error, err:
            raise exception.ConnectionClosed (
                    'socket errorno %d: %s' % (err[0], err[1],))
        self.bytes_received += recv
        self.last_input_time = time.time()

        ## Test for telnet commands, non-telnet bytes
        ## are pushed to self.recv_buffer (side-effect),
        for byte in data:
            self._iac_sniffer(byte)
        return recv

    def _recv_byte(self, byte):
        """
        Buffer non-telnet commands bytestrings into recv_buffer.
        """
        self.recv_buffer.fromstring(byte)

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
                self.telnet_sb_buffer.fromstring (byte)
                ## Sanity check on length
                if len(self.telnet_sb_buffer) >= self.SB_MAXLEN:
                    raise exception.ConnectionClosed (
                            'sub-negotiation buffer filled')
            else:
                ## Just a normal NVT character
                self._recv_byte (byte)
            return

        ## Did we get sent a second IAC?
        if byte == IAC and self.telnet_got_sb is True:
            ## Must be an escaped 255 (IAC + IAC)
            self.telnet_sb_buffer.fromstring (byte)
            self.telnet_got_iac = False
        ## Do we already have an IAC + CMD?
        elif self.telnet_got_cmd is not None:
            ## Yes, so handle the option
            self._three_byte_cmd(byte)
        ## We have IAC but no CMD
        else:
            ## Is this the middle byte of a three-byte command?
            if byte in (DO, DONT, WILL, WONT):
                self.telnet_got_cmd = byte
            else:
                ## Nope, must be a two-byte command
                self._two_byte_cmd(byte)

    def _two_byte_cmd(self, cmd):
        """
        Handle incoming Telnet commands that are two bytes long.
        """
        logger.debug ('recv _two_byte_cmd %s', name_option(cmd),)
        if cmd == SB:
            ## Begin capturing a sub-negotiation string
            self.telnet_got_sb = True
            self.telnet_sb_buffer = array.array('c')
        elif cmd == SE:
            ## Stop capturing a sub-negotiation string
            self.telnet_got_sb = False
            self._sb_decoder()
            logger.debug ('decoded (SE)')
        elif cmd in (NOP, IP, AO, AYT, EC, EL, GA, DM, BRK):
            ## Unimplemented -- DM-relateds
            logger.warn ('_two_byte_cmd not implemented: %r',
                name_option(cmd,))
        else:
            logger.error ('_two_byte_cmd invalid: %r', cmd)
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _three_byte_cmd(self, option):
        """
        Handle incoming Telnet commmands that are three bytes long.
        """
        cmd = self.telnet_got_cmd
        logger.debug ('recv _three_byte_cmd %s %s', name_option(cmd),
            name_option(option))
        # Incoming DO's and DONT's refer to the status of this end

        #---[ DO ]-------------------------------------------------------------
        if cmd == DO:
            self._note_reply_pending(option, False)
            if option == ECHO:
                # DE requests us to echo their input
                if self._check_local_option(ECHO) is not True:
                    self._note_local_option(ECHO, True)
                    self._iac_will(ECHO)
            elif option == SGA:
                # DE wants us to supress go-ahead
                if self._check_local_option(SGA) is not True:
                    self._note_local_option(SGA, True)
                    self._iac_will(SGA)
                    self._iac_do(SGA)
                    # always send DO SGA after WILL SGA, requesting the DE
                    # also supress their go-ahead. this order seems to be the
                    # 'magic sequence' to disable linemode on certain clients
            elif option == LINEMODE:
                # DE wants to do linemode editing
                # denied
                if self._check_local_option(option) is not False:
                    self._note_local_option(option, False)
                    self._iac_wont(LINEMODE)
            elif option == ENCRYPT:
                # DE is willing to receive encrypted data
                # denied
                if self._check_local_option(option) is not False:
                    self._note_local_option(option, False)
                    # let DE know we refuse to send encrypted data.
                    self._iac_wont(ENCRYPT)
            elif option == STATUS:
                # DE wants us to report our status
                # TODO Not Yet Implemented
                if self._check_local_option(option) is not True:
                    self._note_local_option(option, True)
                    self._iac_will(STATUS)
                    # the sender of the WILL STATUS is free to transmit status
                    # information, spontaneously or in response to a request
                    # from the sender of the DO.
                    #self._iac_do(STATUS) # go ahead, so will i..
                    #self.send_str (
                    #    bytes(''.join((IAC, SB, STATUS, SEND, IAC, SE))))
                    # IAC SB STATUS SEND IAC SE

                    # Sender requests receiver to transmit his (the receiver's)
                    # perception of the current status of Telnet
                    # options. The code for SEND is 1. (See below.)

                    # begin sending status ...
                    #logger.debug ('begin status')
                    self.send_str (bytes(''.join((IAC, SB, STATUS, IS))))
                    for option in NEGOTIATE_STATUS:
                        status = self._check_local_option(cmd)
                        if status == True:
                            logger.debug ('status, DO %s',
                                    name_option(option))
                            self.send_str(bytes(''.join((DO, cmd))))
                        elif status == False:
                            logger.debug ('status, DONT %s',
                                    name_option(option))
                            self.send_str(bytes(''.join((DONT, cmd))))
                        else:
                            logger.debug ('status, UNKNOWN %s (not sent)',
                                    name_option(option))
                    self.send_str (bytes(''.join((IAC, SE))))
                    logger.debug ('end status')
            else:
                if self._check_local_option(option) is UNKNOWN:
                    self._note_local_option(option, False)
                    logger.warn ('%s: unhandled do: %s.',
                        self.addrport(), name_option(option))
                    self._iac_wont(option)

        #---[ DONT ]-----------------------------------------------------------
        elif cmd == DONT:
            self._note_reply_pending(option, False)
            if option == BINARY:
                # client demands no binary mode
                if self._check_local_option(BINARY) is not False:
                    self._note_local_option (BINARY, False)
                    self._iac_wont(BINARY) # agree
            elif option == ECHO:
                # client demands we do not echo
                if self._check_local_option(ECHO) is not False:
                    self._note_local_option(ECHO, False)
                    self._iac_wont(ECHO) # agree
            elif option == SGA:
                # DE demands that we start or continue transmitting
                # GAs (go-aheads) when transmitting data.
                if self._check_local_option(SGA) is not False:
                    self._note_local_option(SGA, False)
                    self._iac_wont(SGA)
            elif option == LINEMODE:
                # client demands no linemode.
                if self._check_remote_option(LINEMODE) is not False:
                    self._note_remote_option(LINEMODE, False)
                    self._iac_wont(LINEMODE)
            else:
                logger.warn ('%s: unhandled dont: %s.',
                    self.addrport(), name_option(option))

        # Incoming WILL's and WONT's refer to the status of DE
        #---[ WILL ]-----------------------------------------------------------
        elif cmd == WILL:
            if self._check_reply_pending(option):
                self._note_reply_pending(option, False)
            if option == ECHO:
                raise exception.ConnectionClosed \
                    ('Refuse WILL ECHO by client, closing connection.')
            elif option == NAWS:
                if self._check_remote_option(NAWS) is not True:
                    self._note_remote_option(NAWS, True)
                    self._note_local_option(NAWS, True)
                    self._iac_do(NAWS)
            elif option == STATUS:
                if self._check_remote_option(STATUS) is not True:
                    self._note_remote_option(STATUS, True)
                    self.send_str (bytes(''.join((
                        IAC, SB, STATUS, SEND, IAC, SE)))) # go ahead
            elif option == ENCRYPT:
                # DE is willing to send encrypted data
                # denied
                if self._check_local_option(ENCRYPT) is not False:
                    self._note_local_option(ENCRYPT, False)
                    # let DE know we refuse to receive encrypted data.
                    self._iac_dont(ENCRYPT)
            elif option == LINEMODE:
                self._iac_dont (LINEMODE)
            elif option == SGA:
                # DE is willing to supress go-ahead when sending

#  IAC WILL SUPPRESS-GO-AHEAD
#
# The sender of this command requests permission to begin
# suppressing transmission of the TELNET GO AHEAD (GA)
# character when transmitting data characters, or the
# sender of this command confirms it will now begin suppressing
# transmission of GAs with transmitted data characters.

                # XXX correct?
                if self._check_remote_option(SGA) is not True:
                    self._note_remote_option(SGA, True)
                    self._note_local_option(SGA, True)
                    self._iac_will(SGA)
            elif option == NEW_ENVIRON:
                if self._check_reply_pending(NEW_ENVIRON):
                    self._note_reply_pending(NEW_ENVIRON, False)
                if self._check_remote_option(NEW_ENVIRON) in (False, UNKNOWN):
                    self._note_remote_option(NEW_ENVIRON, True)
                    self._note_local_option(NEW_ENVIRON, True)
                    self._iac_do(NEW_ENVIRON)
                    self.request_env ()
            elif option == TTYPE:
                if self._check_reply_pending(TTYPE):
                    self._note_reply_pending(TTYPE, False)
                if self._check_remote_option(TTYPE) in (False, UNKNOWN):
                    self._note_remote_option(TTYPE, True)
                    self._iac_do(TTYPE)
                    # trigger SB response
                    self.send_str (bytes(''.join( \
                        (IAC, SB, TTYPE, SEND, IAC, SE))))
            else:
                logger.warn ('%s: unhandled will: %s (ignored).',
                    self.addrport(), name_option(option))
        #---[ WONT ]-----------------------------------------------------------
        elif cmd == WONT:
            if option == ECHO:
                if self._check_remote_option(ECHO) in (True, UNKNOWN):
                    self._note_remote_option(ECHO, False)
                    self._iac_dont(ECHO)
            elif option == SGA:
                if self._check_reply_pending(SGA):
                    self._note_reply_pending(SGA, False)
                    self._note_remote_option(SGA, False)
                elif self._check_remote_option(SGA) in (True, UNKNOWN):
                    self._note_remote_option(SGA, False)
                    self._iac_dont(SGA)
            elif option == TTYPE:
                if self._check_reply_pending(TTYPE):
                    self._note_reply_pending(TTYPE, False)
                    self._note_remote_option(TTYPE, False)
                elif self._check_remote_option(TTYPE) in (True, UNKNOWN):
                    self._note_remote_option(TTYPE, False)
                    self._iac_dont(TTYPE)
            else:
                logger.debug ('%s: unhandled wont: %s.',
                    self.addrport(), name_option(option))
        else:
            logger.warn ('%s: unhandled _three_byte_cmd: %s.',
                    self.addrport(), name_option(option))
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _sb_decoder(self):
        """
        Figures out what to do with a received sub-negotiation block.
        """
        buf = self.telnet_sb_buffer
        if 0 == len(buf):
            logger.error ('nil SB')
            return
        if 1 == len(buf) and buf[0] == chr(0):
            logger.error ('0nil SB')
            return
        elif COM_PORT_OPTION == buf[0]:
            logger.error ('%s: COM_PORT_OPTION not supported: %r',
                self.addrport(), buf)
#        elif (TSPEED, IS) == (buf[0], buf[1]):
#          self.terminal_speed = buf[2:].lower()
#          logger.info ('%s: terminal speed %s',
#              self.addrport(), self.terminal_speed)
        elif (TTYPE, IS) == (buf[0], buf[1]):
            prev_term = self.env.get('TERM', None)
            term_str = buf[2:].tostring().lower()
            if prev_term is None:
                logger.info ("env['TERM'] = %r", term_str,)
            elif prev_term != term_str:
                logger.warn ("env['TERM'] = %r by TTYPE (TERM was %s)",
                    term_str, prev_term)
            else:
                logger.debug ('.. ttype ignored (TERM already set)')
            self.env['TERM'] = term_str
            self.terminal_type = term_str
        elif (NEW_ENVIRON, IS) == (buf[0], buf[1],):
            if 2 == len(buf):
                logger.debug ('client NEW_ENVIRON: nil.')
                breaks = list()
                for idx, byte in enumerate(buf[2:]):
                    if byte in (chr(0), chr(1), chr(3)):
                        breaks.append (idx)
                for start, end in zip(breaks, breaks[1:]):
                    logger.debug ('%r', buf[2+start:2+end])
                logger.debug ('%r', buf[2:])
                logger.debug ('%r', breaks)
            # RCVD IAC SB ENVIRON SEND 000 "USER" 000 "TERM" 000 "SHELL" 000
            # "COLUMNS" 000 "LINES" 000 "LC_CTYPE" 000 "XTERM_LOCALE" 000
            # "DISPLAY" 000 "SSH_CLIENT" 000 "SSH_CONNECTION" 000 "SSH_TTY" 000
            # "HOME" 000 "HOSTNAME" 000 "PWD" 000 "MAIL" 000 "LANG" 000 "PWD"
            # 000 "UID" 000 "USER_ID" 000 "EDITOR" 000 "LOGNAME" 003

            # SENT IAC SB ENVIRON IS

            # SENT IAC SB NEW-ENVIRON IS VAR "USER" VALUE "dingo" USERVAR "TERM"
            # VALUE "SCREEN" USERVAR "SHELL" VALUE "/bin/ksh" USERVAR "COLUMNS"
            # USERVAR "LINES" USERVAR "LC_CTYPE" USERVAR "XTERM_LOCALE" VAR
            # "DISPLAY" USERVAR "SSH_CLIENT" VALUE "108.71.224.103 19033 1984"
            # USERVAR "SSH_CONNECTION" VALUE
            # "12.34.36.250 51008 64.150.165.47 443"
            # USERVAR "SSH_TTY" VALUE "/dev/pts/13" USERVAR "HOME" VALUE
            # "/home/dingo" USERVAR "HOSTNAME" USERVAR "PWD" USERVAR "MAIL"
            # VALUE "/var/mail/dingo" USERVAR "LANG" VALUE "en_US.UTF-8"
            # USERVAR "PWD" USERVAR "UID" USERVAR "USER_ID" USERVAR "EDITOR"
            # USERVAR "LOGNAME" VALUE "dingo"
            #nwrites = 0
            #columns, lines = (None, None)
            #for keyvalue in buf[3:].tostring().split(chr(3)):
            #  if 0 == len(keyvalue):
            #    continue
            #  ksp = keyvalue.split(chr(1))
            #  # validation of environment variables .. i guess so
            #  if 1 == len(ksp) or 0 == len(ksp[1]):
            #    if ksp[0] in self.env:
            #      logger.warn ("del env[%r]", ksp[0],)
            #      del self.env[ksp[0]]
            #  elif 2 != len(ksp):
            #    logger.error ('bad NEW_ENVIRON SB; %r ' \
            #        'bad chr(3) split length in %r', buf[3:], ksp)
            #  elif chr(1) in ksp:
            #    logger.error ('bad NEW_ENVIRON SB; %r ' \
            #        'misaligned chr(1) or chr(0) in %r', buf[3:], ksp)
            #  elif not ksp[0].isupper():
            #    logger.error ('bad NEW_ENVIRON SB; %r ' \
            #        '(non-upper: %r)', buf[3:], ksp[0])
            #  else:
            #    moar = ksp[1].split('\x00',1)
            #    ksp[1] = moar[0]
            #    if len(moar) > 1:
            #      logger.debug ('not found; env: %s', moar[1:])
            #    valid=True
            #    for ch in (chr(n) for n in range(0,32)+range(127,256)):
            #      if ch not in ksp[0] and ch not in ksp[1]:
            #        continue
            #      logger.error ('bad NEW_ENVIRON SB; %r ' \
            #          '(unprintable: %r)', buf[3:], ch)
            #      valid=False
            #    if True == valid:
            #      ksp[1] = ksp[1].lower()
            #      if self.env.get(ksp[0], None) == ksp[1]:
            #        continue # repeated
            #      self.env[ksp[0]] = ksp[1]
            #      nwrites += 1
            #      logger.info ('env[%r] = %r', ksp[0], ksp[1])
            #      if ksp[0] == 'TERM':
            #        if self.terminal_type == 'unknown':
            #          self.terminal_type = ksp[1]
            #        elif ksp[1] == self.terminal_type:
            #          logger.info ('double-plus good terminal type detected.')
            #        else:
            #          logger.warn ('TTYPE %r different from TERM %r',
            #              self.terminal_type, ksp[1])
            #      elif ksp[0] == 'COLUMNS':
            #        try: columns = int(ksp[1])
            #        except ValueError: pass
            #      elif ksp[0] == 'LINES':
            #        try: lines = int(ksp[1])
            #        except ValueError: pass
            #if 0 == nwrites:
            #  logger.debug ('NEW_ENVIRON SB: no updates')
            #elif (None, None) != (columns, lines):
            #  if (self.columns, self.rows) != (columns, lines):
            #    # simulate a NAWS event, as if a terminal could update
            #    # window size with response of both LINES, COLUMNS.
            #    self.columns, self.rows = (columns, lines)
            #    if self.on_naws is not None:
            #      self.on_naws (self)
            #  logger.debug ('NEW_ENVIRON SB: %d updates', nwrites,)
            #  if self.on_env is not None:
            #    self.on_env (self)
        elif (NAWS,) == (buf[0],):
            if 5 != len(buf):
                logger.error('%s: bad length in NAWS buf (%d)',
                    self.addrport(), len(buf),)
            else:
                columns = (256 * ord(buf[1])) + ord(buf[2])
                rows = (256 * ord(buf[3])) + ord(buf[4])
                if (self.columns, self.rows) == (columns, rows):
                    logger.debug ('.. naws repeated')
                else:
                    self.columns, self.rows = (columns, rows)
                    if self.on_naws is not None:
                        self.on_naws (self)
                    logger.info ('%s: window size is %dx%d',
                            self.addrport(), columns, rows)
                self.env['LINES'] = str(rows)
                self.env['COLUMNS'] = str(columns)
        else:
            logger.error ('unsupported subnegotiation: %r', buf,)
        self.telnet_sb_buffer = ''

    #---[ State Juggling for Telnet Options ]----------------------------------

    ## Sometimes verbiage is tricky.  I use 'note' rather than 'set' here
    ## because (to me) set infers something happened.

    @debug_option
    def _check_local_option(self, option):
        """Test the status of local negotiated Telnet options."""
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].local_option

    @debug_option
    def _note_local_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].local_option = state

    @debug_option
    def _check_remote_option(self, option):
        """Test the status of remote negotiated Telnet options."""
        if not self.telnet_opt_dict.has_key(option):
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].remote_option

    @debug_option
    def _note_remote_option(self, option, state):
        """Record the status of local negotiated Telnet options."""
        if not option in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].remote_option = state

    @debug_option
    def _check_reply_pending(self, option):
        """Test the status of requested Telnet options."""
        if not option in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].reply_pending

    @debug_option
    def _note_reply_pending(self, option, state):
        """Record the status of requested Telnet options."""
        if not option in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].reply_pending = state


    #---[ Telnet Command Shortcuts ]-------------------------------------------

    def _iac_do(self, option):
        """Send a Telnet IAC "DO" sequence."""
        logger.debug ('send IAC DO %s', name_option(option))
        self.send_str (bytes(''.join((IAC, DO, option))))

    def _iac_dont(self, option):
        """Send a Telnet IAC "DONT" sequence."""
        logger.debug ('send IAC DONT %s', name_option(option))
        self.send_str (bytes(''.join((IAC, DONT, option))))

    def _iac_will(self, option):
        """Send a Telnet IAC "WILL" sequence."""
        logger.debug ('send IAC WILL %s', name_option(option))
        self.send_str (bytes(''.join((IAC, WILL, option))))

    def _iac_wont(self, option):
        """Send a Telnet IAC "WONT" sequence."""
        logger.debug ('send IAC WONT %s', name_option(option))
        self.send_str (bytes(''.join((IAC, WONT, option))))
