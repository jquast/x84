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

import socket
import select
import array
import time
import sys
import logging
logger = logging.getLogger(__name__)
logger.setLevel (logging.DEBUG)

#--[ Telnet Options ]----------------------------------------------------------
from telnetlib import BINARY, SGA, ECHO, STATUS, TTYPE, LINEMODE
from telnetlib import TSPEED, NAWS, LFLOW, NEW_ENVIRON
from telnetlib import COM_PORT_OPTION, ENCRYPT
from telnetlib import IAC, DONT, DO, WONT, WILL, theNULL as NULL
from telnetlib import SE, NOP, DM, BRK, IP, AO, AYT, EC, EL, GA, SB
IS      = chr(0)        # Sub-process negotiation IS command
SEND    = chr(1)        # Sub-process negotiation SEND command

from bbs import exception

class TelnetServer(object):
    """
    Poll sockets for new connections and sending/receiving data from clients.
    """
    MAX_CONNECTIONS=1000
    def __init__(self, port, address, on_connect, on_disconnect, on_naws,
        on_env, timeout):
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

        on_env -- this callable receives a TelnetClient when a client
        negotiates environment variables changes

        timeout -- number of seconds to wait for socket event for each call to
          the poll method.
        """
        self.port = port
        self.address = address
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_naws = on_naws
        self.on_env = on_env
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
        recv_list = [self.server_fileno] + [c.fileno \
            for c in self.clients.values() if c.active]

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
            client = TelnetClient(sock, addr_tup, self.on_naws, self.on_env)
            ## Add the connection to our dictionary and call handler
            self.clients[client.fileno] = client
            self.on_connect (client)
          else:
            logger.error ('refused new connect; maximum reached.')
            sock.close()

        ## Process sockets with data to receive
        recv_ready = (self.clients[f] for f in rlist \
            if f != self.server_fileno)
        for client in recv_ready:
          try:
            client.socket_recv ()
          except exception.ConnectionClosed, e:
            logger.debug ('%s connection closed: %s.' % (client.addrport(), e))
            client.deactivate()

        ## Process sockets with data to send
        slist = (c for c in self.clients.values() \
            if c.active and c.send_ready())
        for client in slist:
          try:
            client.socket_send ()
          except exception.ConnectionClosed, e:
            logger.debug ('%s connection closed: %s.' % (client.addrport(), e))
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


#------------------------------------------------------------------------Telnet

class TelnetClient(object):
    """
    Represents a client connection via Telnet.

    First argument is the socket discovered by the Telnet Server.
    Second argument is the tuple (ip address, port number).
    """
    BLOCKSIZE_RECV=64
    SB_MAXLEN = 65534 # maximum length of subnegotiation string, allow
                      # a fairly large one for NEW_ENVIRON negotiation
    def __init__(self, sock, addr_tup, on_naws=None, on_env=None):
        self.sock = sock
        self.address = addr_tup[0]
        self.port = addr_tup[1]
        self.on_naws = on_naws if on_naws is not None else None
        self.on_env = on_env if on_env is not None else None
        self.fileno = sock.fileno()
        self.active = True
        self.terminal_type='unknown'
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
        # we don't actually honor telnet_echo anymore, we just
        # use it for 'did the client actually agree?' bool
        self.telnet_echo = False

    def name_option(self, option):
      v = ';?'.join([k for k,v in globals().iteritems() if option == v and
        k not in ('NULL','SEND','IS',)])
      return v if v != '' else ord(option)

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
        self.send_str (unibytes.encode(encoding, 'replace') \
            .replace(chr(255), 2*chr(255)))

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
        self.telnet_echo = False

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

    def request_do_NEW_ENVIRON(self):
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
        ready_bytes = ''.join(self.send_buffer)
        if 0 == len(ready_bytes):
          logger.warn ('why did you call socket.send() with no data ready?')
          return

        try:
          sent = self.sock.send(ready_bytes)
        except socket.error, e:
          raise exception.ConnectionClosed('socket send %d:%s' % (e[0], e[1],))
        assert sent > 0 # now, what?
        self.bytes_sent += sent
        self.send_buffer = array.array('c')
        self.send_buffer.fromstring (''.join(ready_bytes[sent:]))

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
        except socket.error, e:
          raise exception.ConnectionClosed \
              ('socket errorno %d: %s' % (e[0], e[1],))
        self.bytes_received += recv
        self.last_input_time = time.time()

        ## Test for telnet commands, non-telnet bytes
        ## are pushed to self.recv_buffer (side-effect),
        map(self._iac_sniffer, data)
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
              raise exception.ConnectionClosed \
                  ('sub-negotiation buffer filled: %r', self.telnet_sb_buffer)
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
        logger.debug ('recv _two_byte_cmd %s' % (self.name_option(cmd),))
        if cmd == SB:
          ## Begin capturing a sub-negotiation string
          self.telnet_got_sb = True
          self.telnet_sb_buffer = array.array('c')
        elif cmd == SE:
          ## Stop capturing a sub-negotiation string
          self.telnet_got_sb = False
          self._sb_decoder()
          logger.debug ('decoded (SE)')
        elif cmd in (NOP, IP, AO, AYT, EC, EL, GA, DM):
          ## Unimplemented -- DM-relateds
          logger.warn ('_two_byte_cmd not implemented: %r',
              self.name_option(cmd,))
          pass
        else:
          logger.error ('_two_byte_cmd invalid: %r', cmd)
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _three_byte_cmd(self, option):
        """
        Handle incoming Telnet commmands that are three bytes long.
        """
        cmd = self.telnet_got_cmd
        logger.debug ('recv _three_byte_cmd %s', self.name_option(cmd))
        ## Incoming DO's and DONT's refer to the status of this end
        #---[ DO ]-------------------------------------------------------------
        if cmd == DO:
          if option == ECHO:
            if self._check_reply_pending(ECHO):
              self._note_reply_pending(ECHO, False)
              self._note_local_option(ECHO, True)
            elif (self._check_local_option(ECHO) in (False, UNKNOWN)):
              self._note_local_option(ECHO, True)
              self._iac_will(ECHO)
            self.telnet_echo = True
          elif option == SGA:
            if self._check_reply_pending(SGA):
              self._note_reply_pending(SGA, False)
              self._note_local_option(SGA, True)
              self._note_remote_option(SGA, True)
            # client wants to SGA? Yes please !
            elif (self._check_local_option(SGA) in (False, UNKNOWN)):
              self._note_local_option(SGA, True)
              self._note_remote_option(SGA, True)
              self._iac_will(SGA)
              # always send 'do' SGA after 'will' SGA. I don't know why, but
              # this order seems to be the 'magic sequence' to disable
              # linemode on some clients ! #XXX Prove w/testcase XXX
              self._iac_do(SGA)
          elif option == LINEMODE:
            if self._check_local_option(option) is UNKNOWN:
              self._note_local_option(option, False)
              self._iac_wont(LINEMODE)
          elif option == STATUS:
            # TODO Not Yet Implemented
            if self._check_local_option(option) is UNKNOWN:
              self._note_local_option(option, False)
              self._iac_wont(STATUS)
          else:
            if self._check_local_option(option) is UNKNOWN:
              self._note_local_option(option, False)
              logger.warn ('%s: unhandled do: %s.',
                  self.addrport(), self.name_option(option))
              self._iac_wont(option)
        #---[ DONT ]-----------------------------------------------------------
        elif cmd == DONT:
          if option == BINARY:
            if self._check_reply_pending(BINARY):
              self._note_reply_pending(BINARY, False)
              self._note_local_option(BINARY, False)
            elif self._check_local_option(BINARY) in (True, UNKNOWN):
              self._note_local_option(BINARY, False)
              self._iac_wont(BINARY) # agree
          elif option == ECHO:
            # local echo is not actually supported.
            if self._check_reply_pending(ECHO):
              self._note_reply_pending(ECHO, False)
              self._note_local_option(ECHO, False)
              self.telnet_echo = False
            elif self._check_local_option(ECHO) in (True, UNKNOWN):
              self._note_local_option(ECHO, False)
              self._iac_wont(ECHO) # agree
              self.telnet_echo = False
          elif option == SGA:
            # client: DONT SGA, us: ok, we won't
            if self._check_reply_pending(SGA):
              self._note_reply_pending(SGA, False)
              self._note_local_option(SGA, False)
            elif self._check_remote_option(SGA) in (True,UNKNOWN):
              self._note_local_option(SGA, False)
              self._iac_wont(SGA)
          elif option == LINEMODE:
            # client: DONT LINEMODE, us: ok, we won't
            if self._check_reply_pending(LINEMODE):
              self._note_reply_pending(LINEMODE, False)
              self._note_local_option(LINEMODE, False)
            if self._check_remote_option(LINEMODE) in (True, UNKNOWN):
              self._note_remote_option(LINEMODE, False)
              self._iac_wont(LINEMODE)
          else:
            ## ALL OTHER OPTIONS = Default to ignoring
            logger.warn ('%s: unhandled dont: %s.',
                self.addrport(), self.name_option(option))
        #---[ WILL ]-----------------------------------------------------------
        elif cmd == WILL:
          if option == ECHO:
            ## Nutjob DE offering to echo the server...
            if self._check_remote_option(ECHO) in (UNKNOWN,False):
              # No no, bad DE!
              self._iac_dont(ECHO)
              logger.error ('nutjob condition?')
# TODO
#            elif option == TSPEED:
#              if self._check_reply_pending(TSPEED):
#                  self._note_reply_pending(TSPEED, False)
#              if (self._check_remote_option(TSPEED) in (False, UNKNOWN):
#                self._note_remote_option(TSPEED, True)
#                self._note_local_option(TSPEED, True)
#                self._iac_do(TSPEED) # ?
          elif option == NAWS:
            if self._check_reply_pending(NAWS):
                self._note_reply_pending(NAWS, False)
            if self._check_remote_option(NAWS) in (False, UNKNOWN):
              self._note_remote_option(NAWS, True)
              self._note_local_option(NAWS, True)
              self._iac_do(NAWS)
          elif option == LINEMODE:
            self._iac_dont (LINEMODE)
          elif option == SGA:
            if self._check_reply_pending(SGA):
                self._note_reply_pending(SGA, False)
            if self._check_remote_option(SGA) in (False, UNKNOWN):
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
          elif option == LFLOW:
            self._iac_wont(LFLOW) # TODO
          else:
            logger.warn ('%s: unhandled will: %s.',
                self.addrport(), self.name_option(option))
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
                self.addrport(), self.name_option(option))
        else:
            logger.warn ('%s: unhandled _three_byte_cmd: %s.' % \
                (self.addrport(), self.name_option(option)))
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _sb_decoder(self):
        """
        Figures out what to do with a received sub-negotiation block.
        """
        buf = self.telnet_sb_buffer
        slc = chr(3) # naw,
        if 1 == len(buf) and buf[0] == chr(0):
          logger.debug ('nil SB')
          return
        elif COM_PORT_OPTION == buf[0]:
          logger.warn ('%s: COM_PORT_OPTION not supported: %r',
              self.addrport(), buf)
        elif (TSPEED, IS) == (buf[0], buf[1]):
          self.terminal_speed = buf[2:].lower()
          logger.info ('%s: terminal speed %s',
              self.addrport(), self.terminal_speed)
        elif (TTYPE, IS) == (buf[0], buf[1]):
          term_str = buf[2:].tostring().lower()
          if self.terminal_type == 'unknown':
            logger.info ("env['TERM'] = %r", term_str,)
          elif self.terminal_type != term_str:
            logger.warn ("env['TERM'] = %r by TTYPE", term_str)
            if self.on_env is not None:
              self.on_env (self) # simulate update of 'TERM' ..
          else:
            logger.debug ('.. ttype repeated')
          if self.env.get('TERM', None) != term_str:
            self.env['TERM'] = term_str
            if self.on_env is not None:
              self.on_env (self) # simulate update of 'TERM' ..
          else:
            logger.debug ('.. ttype ignored (TERM already set)')
          self.terminal_type = term_str
        elif (NEW_ENVIRON, chr(0)) == (buf[0], buf[1],):
          if 2 == len(buf):
            logger.debug ('NEW_ENVIRON SB; empty')
          nwrites = 0
          columns, lines = (None, None)
          for keyvalue in buf[3:].tostring().split(chr(3)):
            if 0 == len(keyvalue):
              continue
            ksp = keyvalue.split(chr(1))
            # validation of environment variables .. i guess so
            if 1 == len(ksp) or 0 == len(ksp[1]):
              if ksp[0] in self.env:
                logger.warn ("del env[%r]", ksp[0],)
                del self.env[ksp[0]]
            elif 2 != len(ksp):
              logger.error ('bad NEW_ENVIRON SB; %r ' \
                  'bad chr(3) split length in %r', buf[3:], ksp)
            elif chr(1) in ksp:
              logger.error ('bad NEW_ENVIRON SB; %r ' \
                  'misaligned chr(1) or chr(0) in %r', buf[3:], ksp)
            elif not ksp[0].isupper():
              logger.error ('bad NEW_ENVIRON SB; %r ' \
                  '(non-upper: %r)', buf[3:], ksp[0])
            else:
              moar = ksp[1].split('\x00',1)
              ksp[1] = moar[0]
              if len(moar) > 1:
                logger.debug ('not found; env: %s', moar[1:])
              valid=True
              for ch in (chr(n) for n in range(0,32)+range(127,256)):
                if ch not in ksp[0] and ch not in ksp[1]:
                  continue
                logger.error ('bad NEW_ENVIRON SB; %r ' \
                    '(unprintable: %r)', buf[3:], ch)
                valid=False
              if True == valid:
                ksp[1] = ksp[1].lower()
                if self.env.get(ksp[0], None) == ksp[1]:
                  continue # repeated
                self.env[ksp[0]] = ksp[1]
                nwrites += 1
                logger.info ('env[%r] = %r', ksp[0], ksp[1])
                if ksp[0] == 'TERM':
                  if self.terminal_type == 'unknown':
                    self.terminal_type = ksp[1]
                  elif ksp[1] == self.terminal_type:
                    logger.info ('double-plus good terminal type detected.')
                  else:
                    logger.warn ('TTYPE %r different from TERM %r',
                        self.terminal_type, ksp[1])
                elif ksp[0] == 'COLUMNS':
                  try: columns = int(ksp[1])
                  except ValueError: pass
                elif ksp[0] == 'LINES':
                  try: lines = int(ksp[1])
                  except ValueError: pass
          if 0 == nwrites:
            logger.debug ('NEW_ENVIRON SB: no updates')
          elif (None, None) != (columns, lines):
            if (self.columns, self.rows) != (columns, lines):
              # simulate a NAWS event, as if a terminal could update
              # window size with response of both LINES, COLUMNS.
              self.columns, self.rows = (columns, lines)
              if self.on_naws is not None:
                self.on_naws (self)
            logger.debug ('NEW_ENVIRON SB: %d updates', nwrites,)
            if self.on_env is not None:
              self.on_env (self)
        elif (NAWS,) == (buf[0],):
          if 5 != len(buf):
            logger.error('%s: bad length in NAWS buf (%d)' % \
                (self.addrport(), len(buf),))
          else:
            columns = (256 * ord(buf[1])) + ord(buf[2])
            rows = (256 * ord(buf[3])) + ord(buf[4])
            if (self.columns, self.rows) == (columns, rows):
              logger.debug ('.. naws repeated')
            else:
              self.columns, self.rows = (columns, rows)
              if self.on_naws is not None:
                self.on_naws (self)
              logger.info ('%s: window size is %dx%d' % \
                  (self.addrport(), self.columns, self.rows))
        else:
          logger.error ('unsupported subnegotiation: %r' % (buf,))
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
        logger.debug ('send IAC DO %s' % (self.name_option(option)))
        self.send_str (bytes(''.join((IAC, DO, option))))

    def _iac_dont(self, option):
        """Send a Telnet IAC "DONT" sequence."""
        logger.debug ('send IAC DONT %s' % (self.name_option(option)))
        self.send_str (bytes(''.join((IAC, DONT, option))))

    def _iac_will(self, option):
        """Send a Telnet IAC "WILL" sequence."""
        logger.debug ('send IAC WILL %s' % (self.name_option(option)))
        self.send_str (bytes(''.join((IAC, WILL, option))))

    def _iac_wont(self, option):
        """Send a Telnet IAC "WONT" sequence."""
        logger.debug ('send IAC WONT %s' % (self.name_option(option)))
        self.send_str (bytes(''.join((IAC, WONT, option))))
