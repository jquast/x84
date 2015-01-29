"""
Telnet server for x84.

Limitations:

- No linemode support, character-at-a-time only.
- No out-of-band / data mark (DM) / sync supported
- No flow control (``^S``, ``^Q``)

This is a modified version of miniboa retrieved from svn address
http://miniboa.googlecode.com/svn/trunk/miniboa which is meant for
MUD's. This server would not be safe for most (linemode) MUD clients.

Changes from miniboa:

- character-at-a-time input instead of linemode
- encoding option on send
- strict rejection of linemode
- terminal type detection
- environment variable support
- GA and SGA
- utf-8 safe
"""
# ------------------------------------------------------------------------------
#   miniboa/async.py
#   miniboa/telnet.py
#
#   Copyright 2009 Jim Storch
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain a
#   copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
# ------------------------------------------------------------------------------

from __future__ import absolute_import

# std
import socket
import array
import time
import logging
import select
import errno
from telnetlib import LINEMODE, NAWS, NEW_ENVIRON, ENCRYPT, AUTHENTICATION
from telnetlib import BINARY, SGA, ECHO, STATUS, TTYPE, TSPEED, LFLOW
from telnetlib import XDISPLOC, IAC, DONT, DO, WONT, WILL, SE, NOP, DM, BRK
from telnetlib import IP, AO, AYT, EC, EL, GA, SB

# local
from x84.bbs.exception import Disconnected
from .terminal import spawn_client_session, on_naws
from .client import BaseClient, BaseConnect
from .server import BaseServer

IS = chr(0)  # Sub-process negotiation IS command
SEND = chr(1)  # Sub-process negotiation SEND command
UNSUPPORTED_WILL = (LINEMODE, LFLOW, TSPEED, ENCRYPT, AUTHENTICATION)

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
# acknowledgment of it's own.
#
# If a party receives a request to enter a mode that it is already in, the
# request should not be acknowledged.

# Where you see DE in my comments I mean 'Distant End', e.g. the client.

UNKNOWN = -1

#-----------------------------------------------------------------Telnet Option


class TelnetOption(object):

    """
    Simple class used to track the status of an extended Telnet option.

    Attributes and their state values:

    - ``local_option``: UNKNOWN (default), True, or False.
    - ``remote_option``: UNKNOWN (default), True, or False.
    - ``reply_pending``: True or Fale.
    """
    # pylint: disable=R0903
    #         Too few public methods (0/2)

    def __init__(self):
        """
        Set attribute defaults on init.
        """
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
    return values if values != '' else str(ord(option))


def debug_option(func):
    """
    This function is a decorator that debug prints the 'from' address for
    callables decorated with this. This helps during telnet negotiation, to
    understand which function sets or checks local or remote option states.
    """
    import os
    import inspect

    def wrapper(self, *args):
        """
        inner wrapper for debug_option
        """
        stack = inspect.stack()
        self.log.debug('%s:%s %s(%s%s)',
                       os.path.basename(stack[1][1]), stack[1][2],
                       func.__name__, name_option(args[0]),
                       ', %s' % (args[1],) if len(args) == 2 else '')
        return func(self, *args)
    return wrapper


#------------------------------------------------------------------------Telnet

class TelnetClient(BaseClient):

    """
    Represents a remote Telnet Client, instantiated from TelnetServer.
    """
    # pylint: disable=R0902,R0904
    #         Too many instance attributes
    #         Too many public methods

    kind = 'telnet'

    #: maximum size of telnet subnegotiation string, allowing for a fairly
    #: large value for NEW_ENVIRON.
    SB_MAXLEN = 65534

    def __init__(self, sock, address_pair, on_naws=None):
        super(TelnetClient, self).__init__(sock, address_pair, on_naws)
        self.telnet_sb_buffer = array.array('c')

        # State variables for interpreting incoming telnet commands
        self.telnet_got_iac = False
        self.telnet_got_cmd = None
        self.telnet_got_sb = False
        self.telnet_opt_dict = {}

        self.ENV_REQUESTED = False
        self.ENV_REPLIED = False

    def request_will_sga(self):
        """
        Request DE to Suppress Go-Ahead.  See RFC 858.
        """
        self._iac_will(SGA)
        self._note_reply_pending(SGA, True)

    def request_will_echo(self):
        """
        Tell the DE that we would like to echo their text.  See RFC 857.
        """
        self._iac_will(ECHO)
        self._note_reply_pending(ECHO, True)

    def request_will_binary(self):
        """
        Tell the DE that we would like to use binary 8-bit (utf8).
        """
        self._iac_will(BINARY)
        self._note_reply_pending(BINARY, True)

    def request_do_binary(self):
        """
        Tell the DE that we would like them to input binary 8-bit (utf8).
        """
        self._iac_do(BINARY)
        self._note_reply_pending(BINARY, True)

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

    def request_env(self):
        """
        Request sub-negotiation NEW_ENVIRON. See RFC 1572.
        """
        if self.ENV_REQUESTED:
            return  # avoid asking twice ..
        rstr = bytes(''.join((IAC, SB, NEW_ENVIRON, SEND, chr(0))))
        rstr += bytes(chr(0).join(
            ("USER TERM SHELL COLUMNS LINES C_CTYPE XTERM_LOCALE DISPLAY "
             "SSH_CLIENT SSH_CONNECTION SSH_TTY HOME HOSTNAME PWD MAIL LANG "
             "PWD UID USER_ID EDITOR LOGNAME".split())))
        rstr += bytes(''.join((chr(3), IAC, SE)))
        self.ENV_REQUESTED = True
        self.send_str(rstr)

    def request_do_ttype(self):
        """
        Begins TERMINAL-TYPE negotiation
        """
        if self.check_remote_option(TTYPE) in (False, UNKNOWN):
            self._iac_do(TTYPE)
            self._note_reply_pending(TTYPE, True)

    def request_ttype(self):
        """
        Sends IAC SB TTYPE SEND IAC SE
        """
        self.send_str(bytes(''.join((
            IAC, SB, TTYPE, SEND, IAC, SE))))

    def recv_ready(self):
        """
        Returns True if data is awaiting on the telnet socket.
        """
        return (self.is_active() and bool(
            select.select([self.sock.fileno()], [], [], 0)[0]))

    def socket_recv(self):
        """
        Called by TelnetServer.poll() when recv data is ready.  Read any
        data on socket, processing telnet commands, and buffering all
        other bytestrings to self.recv_buffer.  If data is not received,
        or the connection is closed, x84.bbs.exception.Disconnected is
        raised.
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

        # Test for telnet commands, non-telnet bytes
        # are pushed to self.recv_buffer (side-effect),
        for byte in data:
            self._iac_sniffer(byte)
        return recv

    def send_unicode(self, ucs, encoding='utf8'):
        """ Buffer unicode string, encoded for client as 'encoding'. """
        # Must be escaped 255 (IAC + IAC) to avoid IAC interpretation.
        self.send_str(ucs.encode(encoding, 'replace').replace(IAC, 2 * IAC))

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
        # Are we not currently in an IAC sequence coming from the DE?
        if self.telnet_got_iac is False:
            if byte == IAC:
                self.telnet_got_iac = True
            # Are we currently in a sub-negotiation?
            elif self.telnet_got_sb is True:
                self.telnet_sb_buffer.fromstring(byte)
                # Sanity check on length
                if len(self.telnet_sb_buffer) >= self.SB_MAXLEN:
                    raise Disconnected('sub-negotiation buffer filled')
            else:
                # Just a normal NVT character
                self._recv_byte(byte)
            return

        # Did we get sent a second IAC?
        if byte == IAC and self.telnet_got_sb is True:
            # Must be an escaped 255 (IAC + IAC)
            self.telnet_sb_buffer.fromstring(byte)
            self.telnet_got_iac = False
        # Do we already have an IAC + CMD?
        elif self.telnet_got_cmd is not None:
            # Yes, so handle the option
            self._three_byte_cmd(byte)
        # We have IAC but no CMD
        else:
            # Is this the middle byte of a three-byte command?
            if byte in (DO, DONT, WILL, WONT):
                self.telnet_got_cmd = byte
            else:
                # Nope, must be a two-byte command
                self._two_byte_cmd(byte)

    def _two_byte_cmd(self, cmd):
        """
        Handle incoming Telnet commands that are two bytes long.
        """
        # self.log.debug ('recv _two_byte_cmd %s', name_option(cmd),)
        if cmd == SB:
            # Begin capturing a sub-negotiation string
            self.telnet_got_sb = True
            self.telnet_sb_buffer = array.array('c')
        elif cmd == SE:
            # Stop capturing a sub-negotiation string
            self.telnet_got_sb = False
            self._sb_decoder()
        elif cmd == IAC:
            # IAC, IAC is used for a literal \xff character.
            self._recv_byte(IAC)
        elif cmd == IP:
            self.deactivate()
            self.log.info('{self.addrport} received (IAC, IP): closing.'
                          .format(self=self))
        elif cmd == AO:
            flushed = len(self.recv_buffer)
            self.recv_buffer = array.array('c')
            self.log.debug('Abort Output (AO); %s bytes discarded.', flushed)
        elif cmd == AYT:
            self.send_str(bytes('\b'))
            self.log.debug('Are You There (AYT); "\\b" sent.')
        elif cmd == EC:
            self.recv_buffer.fromstring('\b')
            self.log.debug('Erase Character (EC); "\\b" queued.')
        elif cmd == EL:
            self.log.warn('Erase Line (EC) received; ignored.')
        elif cmd == GA:
            self.log.warn('Go Ahead (GA) received; ignored.')
        elif cmd == NOP:
            self.log.debug('NUL ignored.')
        elif cmd == DM:
            self.log.warn('Data Mark (DM) received; ignored.')
        elif cmd == BRK:
            self.log.warn('Break (BRK) received; ignored.')
        else:
            self.log.error('_two_byte_cmd invalid: %r', cmd)
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _three_byte_cmd(self, option):
        """
        Handle incoming Telnet commmands that are three bytes long.
        """
        cmd = self.telnet_got_cmd
        self.log.debug('recv IAC %s %s', name_option(cmd), name_option(option))
        # Incoming DO's and DONT's refer to the status of this end

        if cmd == DO:
            self._handle_do(option)
        elif cmd == DONT:
            self._handle_dont(option)
        elif cmd == WILL:
            self._handle_will(option)
        elif cmd == WONT:
            self._handle_wont(option)
        else:
            self.log.debug('{self.addrport}: unhandled _three_byte_cmd: {opt}.'
                           .format(self=self, opt=name_option(option)))
        self.telnet_got_iac = False
        self.telnet_got_cmd = None

    def _handle_do(self, option):
        """
        Process a DO command option received by DE.
        """
        # pylint: disable=R0912
        #         TelnetClient._handle_do: Too many branches (13/12)
        # if any pending WILL options were send, they have been received
        self._note_reply_pending(option, False)
        if option == ECHO:
            # DE requests us to echo their input
            if self.check_local_option(ECHO) is not True:
                self._note_local_option(ECHO, True)
                self._iac_will(ECHO)
        elif option == BINARY:
            # DE requests to recv BINARY
            if self.check_local_option(BINARY) is not True:
                self._note_local_option(BINARY, True)
                self._iac_will(BINARY)
        elif option == SGA:
            # DE wants us to supress go-ahead
            if self.check_local_option(SGA) is not True:
                self._note_local_option(SGA, True)
                # always send DO SGA after WILL SGA, requesting the DE
                # also supress their go-ahead. this order seems to be the
                # 'magic sequence' to disable linemode on certain clients
                self._iac_will(SGA)
                self._iac_do(SGA)
        elif option == LINEMODE:
            # DE wants to do linemode editing
            # denied
            if self.check_local_option(option) is not False:
                self._note_local_option(option, False)
                self._iac_wont(LINEMODE)
        elif option == ENCRYPT:
            # DE is willing to receive encrypted data
            # denied
            if self.check_local_option(option) is not False:
                self._note_local_option(option, False)
                # let DE know we refuse to send encrypted data.
                self._iac_wont(ENCRYPT)
        elif option == STATUS:
            # DE wants to know if we support STATUS,
            if self.check_local_option(option) is not True:
                self._note_local_option(option, True)
                self._iac_will(STATUS)
                self._send_status()
        else:
            if self.check_local_option(option) is UNKNOWN:
                self._note_local_option(option, False)
                self.log.debug('{self.addrport}: unhandled do: {opt}.'
                               .format(self=self, opt=name_option(option)))
                self._iac_wont(option)

    def _send_status(self):
        """
        Process a DO STATUS sub-negotiation received by DE. (rfc859)
        """
        # warning:
        rstr = bytes(''.join((IAC, SB, STATUS, IS)))
        for opt, status in self.telnet_opt_dict.items():
            # my_want_state_is_will
            if status.local_option is True:
                self.log.debug('send WILL %s', name_option(opt))
                rstr += bytes(''.join((WILL, opt)))
            elif status.reply_pending is True and opt in (ECHO, SGA):
                self.log.debug('send WILL %s (want)', name_option(opt))
                rstr += bytes(''.join((WILL, opt)))
            # his_want_state_is_will
            elif status.remote_option is True:
                self.log.debug('send DO %s', name_option(opt))
                rstr += bytes(''.join((DO, opt)))
            elif (status.reply_pending is True
                    and opt in (NEW_ENVIRON, NAWS, TTYPE)):
                self.log.debug('send DO %s (want)', name_option(opt))
                rstr += bytes(''.join((DO, opt)))
        rstr += bytes(''.join((IAC, SE)))
        self.log.debug('send %s', ' '.join(name_option(opt) for opt in rstr))
        self.send_str(rstr)

    def _handle_dont(self, option):
        """
        Process a DONT command option received by DE.
        """
        self._note_reply_pending(option, False)
        if option == ECHO:
            # client demands we do not echo
            if self.check_local_option(ECHO) is not False:
                self._note_local_option(ECHO, False)
        elif option == BINARY:
            # client demands no binary mode
            if self.check_local_option(BINARY) is not False:
                self._note_local_option(BINARY, False)
        elif option == SGA:
            # DE demands that we start or continue transmitting
            # GAs (go-aheads) when transmitting data.
            if self.check_local_option(SGA) is not False:
                self._note_local_option(SGA, False)
        elif option == LINEMODE:
            # client demands no linemode.
            if self.check_remote_option(LINEMODE) is not False:
                self._note_remote_option(LINEMODE, False)
        else:
            self.log.debug('{self.addrport}: unhandled dont: {opt}.'
                           .format(self=self, opt=name_option(option)))

    def _handle_will(self, option):
        """
        Process a WILL command option received by DE.
        """
        # pylint: disable=R0912
        #        Too many branches (19/12)
        self._note_reply_pending(option, False)
        if option == ECHO:
            raise Disconnected(
                'Refuse WILL ECHO by client, closing connection.')
        elif option == BINARY:
            if self.check_remote_option(BINARY) is not True:
                self._note_remote_option(BINARY, True)
                # agree to use BINARY
                self._iac_do(BINARY)
        elif option == NAWS:
            if self.check_remote_option(NAWS) is not True:
                self._note_remote_option(NAWS, True)
                self._note_local_option(NAWS, True)
                # agree to use NAWS, / go ahead ?
                self._iac_do(NAWS)
        elif option == STATUS:
            if self.check_remote_option(STATUS) is not True:
                self._note_remote_option(STATUS, True)
                self.send_str(bytes(''.join((
                    IAC, SB, STATUS, SEND, IAC, SE))))  # go ahead
        elif option in UNSUPPORTED_WILL:
            if self.check_remote_option(option) is not False:
                # let DE know we refuse to do linemode, encryption, etc.
                self._iac_dont(option)
        elif option == SGA:
            #  IAC WILL SUPPRESS-GO-AHEAD
            #
            # The sender of this command requests permission to begin
            # suppressing transmission of the TELNET GO AHEAD (GA)
            # character when transmitting data characters, or the
            # sender of this command confirms it will now begin suppressing
            # transmission of GAs with transmitted data characters.
            if self.check_remote_option(SGA) is not True:
                # sender of this command confirms that the sender of data
                # is expected to suppress transmission of GAs.
                self._iac_do(SGA)
                self._note_remote_option(SGA, True)
        elif option == NEW_ENVIRON:
            if self.check_remote_option(NEW_ENVIRON) in (False, UNKNOWN):
                self._note_remote_option(NEW_ENVIRON, True)
                self.request_env()
            self._note_local_option(NEW_ENVIRON, True)
        elif option == XDISPLOC:
            # if they want to send it, go ahead.
            if self.check_remote_option(XDISPLOC):
                self._note_remote_option(XDISPLOC, True)
                self._iac_do(XDISPLOC)
                self.send_str(bytes(''.join((
                    IAC, SB, XDISPLOC, SEND, IAC, SE))))
        elif option == TTYPE:
            if self.check_remote_option(TTYPE) in (False, UNKNOWN):
                self._note_remote_option(TTYPE, True)
                self.request_ttype()
        else:
            self.log.debug('{self.addrport}: unhandled will: {opt} (ignored).'
                           .format(self=self, opt=name_option(option)))

    def _handle_wont(self, option):
        """
        Process a WONT command option received by DE.
        """
        # pylint: disable=R0912
        #         TelnetClient._handle_wont: Too many branches (13/12)
        self._note_reply_pending(option, False)
        if option == ECHO:
            if self.check_remote_option(ECHO) in (True, UNKNOWN):
                self._note_remote_option(ECHO, False)
                self._iac_dont(ECHO)
        elif option == BINARY:
            # client demands no binary mode
            if self.check_remote_option(BINARY) in (True, UNKNOWN):
                self._note_remote_option(BINARY, False)
                self._iac_dont(BINARY)
        elif option == SGA:
            if self._check_reply_pending(SGA):
                self._note_reply_pending(SGA, False)
                self._note_remote_option(SGA, False)
            elif self.check_remote_option(SGA) in (True, UNKNOWN):
                self._note_remote_option(SGA, False)
                self._iac_dont(SGA)
        elif option == TTYPE:
            if self._check_reply_pending(TTYPE):
                self._note_reply_pending(TTYPE, False)
                self._note_remote_option(TTYPE, False)
            elif self.check_remote_option(TTYPE) in (True, UNKNOWN):
                self._note_remote_option(TTYPE, False)
                self._iac_dont(TTYPE)
        elif option in (NEW_ENVIRON, NAWS):
            if self._check_reply_pending(option):
                self._note_reply_pending(option, False)
                self._note_remote_option(option, False)
            elif self.check_remote_option(option) in (True, UNKNOWN):
                self._note_remote_option(option, False)
        else:
            self.log.debug('{self.addrport}: unhandled wont: {opt}.'
                           .format(self=self, opt=name_option(option)))
            self._note_remote_option(option, False)

    def _sb_decoder(self):
        """
        Figures out what to do with a received sub-negotiation block.
        """

        buf = self.telnet_sb_buffer
        if 0 == len(buf):
            self.log.error('nil SB')
            return
        self.log.debug('recv SB: %s %s',
                       name_option(buf[0]),
                       'IS %r' % (buf[2:],) if len(buf) > 1 and buf[1] is IS
                       else repr(buf[1:]))
        if 1 == len(buf) and buf[0] == chr(0):
            self.log.error('0nil SB')
            return
        elif len(buf) < 2:
            self.log.error('SB too short')
            return
        elif (TTYPE, IS) == (buf[0], buf[1]):
            self._sb_ttype(buf[2:].tostring())
        elif (XDISPLOC, IS) == (buf[0], buf[1]):
            self._sb_xdisploc(buf[2:].tostring())
        elif (NEW_ENVIRON, IS) == (buf[0], buf[1]):
            self._sb_env(buf[2:].tostring())
        elif NAWS == buf[0]:
            self._sb_naws(buf)
        elif (STATUS, SEND) == (buf[0], buf[1]):
            self._send_status()
        else:
            self.log.error('unsupported subnegotiation, %s: %r',
                           name_option(buf[0]), buf,)
        self.telnet_sb_buffer = ''

    def _sb_xdisploc(self, bytestring):
        """
        Process incoming sub-negotiation XDISPLOC
        """
        prev_display = self.env.get('DISPLAY', None)
        if prev_display is None:
            self.log.info("env['DISPLAY'] = %r.", bytestring)
        elif prev_display != bytestring:
            self.log.info("env['DISPLAY'] = %r by XDISPLOC was:%s.",
                          bytestring, prev_display)
        else:
            self.log.debug('XDSIPLOC ignored (DISPLAY already set).')
        self.env['DISPLAY'] = bytestring

    def _sb_ttype(self, bytestring):
        """
        Processes incoming subnegotiation TTYPE
        """
        term_str = bytestring.lower().strip()
        while term_str.endswith('\x00'):
            term_str = term_str[:-1]  # netrunner did this ..
        prev_term = self.env.get('TERM', None)
        if prev_term is None:
            self.log.debug("env['TERM'] = %r.", term_str)
        elif prev_term != term_str:
            self.log.debug("env['TERM'] = %r by TTYPE%s.", term_str,
                           ', was: %s' % (prev_term,)
                           if prev_term != self.TTYPE_UNDETECTED else '')
        else:
            self.log.debug('TTYPE ignored (TERM already set).')
        self.env['TERM'] = term_str

    def _sb_env(self, bytestring):
        """
        Processes incoming sub-negotiation NEW_ENVIRON
        """
        breaks = list([idx for (idx, byte) in enumerate(bytestring)
                       if byte in (chr(0), chr(3))])
        for start, end in zip(breaks, breaks[1:]):
            pair = bytestring[start + 1:end].split(chr(1))
            if len(pair) == 1:
                if (pair[0] in self.env
                        and pair[0] not in ('LINES', 'COLUMNS', 'TERM')):
                    self.log.warn("del env[%r]", pair[0])
                    del self.env[pair[0]]
            elif len(pair) == 2:
                if pair[0] == 'TERM':
                    pair[1] = pair[1].lower()
                overwrite = (pair[0] == 'TERM'
                             and self.env['TERM'] == self.TTYPE_UNDETECTED)
                if (not pair[0] in self.env or overwrite):
                    self.log.debug('env[%r] = %r', pair[0], pair[1])
                    self.env[pair[0]] = pair[1]
                elif pair[1] == self.env[pair[0]]:
                    self.log.debug('env[%r] repeated', pair[0])
                else:
                    self.log.warn('%s=%s; conflicting value %s ignored.',
                                  pair[0], self.env[pair[0]], pair[1])
            else:
                self.log.error('client NEW_ENVIRON; invalid %r', pair)
        self.ENV_REPLIED = True

    def _sb_naws(self, charbuf):
        """
        Processes incoming subnegotiation NAWS
        """
        if 5 != len(charbuf):
            self.log.error('{self.addrport}: bad length in NAWS buf ({buflen})'
                           .format(self=self, buflen=len(charbuf)))
            return

        columns = (256 * ord(charbuf[1])) + ord(charbuf[2])
        rows = (256 * ord(charbuf[3])) + ord(charbuf[4])
        old_rows = self.env.get('LINES', None)
        old_columns = self.env.get('COLUMNS', None)
        if (old_rows == str(rows) and old_columns == str(columns)):
            self.log.debug('{self.addrport}: NAWS repeated'.format(self=self))
            return
        if rows <= 0:
            self.log.debug('LINES %s ignored', rows)
            rows = old_rows
        if columns <= 0:
            self.log.debug('COLUMNS %s ignored', columns)
            columns = old_columns
        self.env['LINES'] = str(rows)
        self.env['COLUMNS'] = str(columns)
        if self.on_naws is not None:
            self.on_naws(self)

    #---[ State Juggling for Telnet Options ]----------------------------------
    def check_local_option(self, option):
        """
        Test the status of local negotiated Telnet options.
        """
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].local_option

    def _note_local_option(self, option, state):
        """
        Record the status of local negotiated Telnet options.
        """
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].local_option = state

    def check_remote_option(self, option):
        """
        Test the status of remote negotiated Telnet options.
        """
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].remote_option

    def _note_remote_option(self, option, state):
        """
        Record the status of local negotiated Telnet options.
        """
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].remote_option = state

    def _check_reply_pending(self, option):
        """
        Test the status of requested Telnet options.
        """
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        return self.telnet_opt_dict[option].reply_pending

    def _note_reply_pending(self, option, state):
        """
        Record the status of requested Telnet options.
        """
        if option not in self.telnet_opt_dict:
            self.telnet_opt_dict[option] = TelnetOption()
        self.telnet_opt_dict[option].reply_pending = state

    #---[ Telnet Command Shortcuts ]-------------------------------------------
    def _iac_do(self, option):
        """
        Send a Telnet IAC "DO" sequence.
        """
        self.log.debug('send IAC DO %s', name_option(option))
        self.send_str(bytes(''.join((IAC, DO, option))))

    def _iac_dont(self, option):
        """
        Send a Telnet IAC "DONT" sequence.
        """
        self.log.debug('send IAC DONT %s', name_option(option))
        self.send_str(bytes(''.join((IAC, DONT, option))))

    def _iac_will(self, option):
        """
        Send a Telnet IAC "WILL" sequence.
        """
        self.log.debug('send IAC WILL %s', name_option(option))
        self.send_str(bytes(''.join((IAC, WILL, option))))

    def _iac_wont(self, option):
        """
        Send a Telnet IAC "WONT" sequence.
        """
        self.log.debug('send IAC WONT %s', name_option(option))
        self.send_str(bytes(''.join((IAC, WONT, option))))


class ConnectTelnet(BaseConnect):

    """
    Accept new Telnet Connection and negotiate options.
    """
    #: maximum time elapsed allowed to begin on-connect negotiation
    TIME_NEGOTIATE = 2.50
    #: wait upto 3500ms for all stages of negotiation to complete
    TIME_WAIT_STAGE = 3.50
    #: polling duration during negotiation
    TIME_POLL = 0.10

    def banner(self):
        """
        This method is called after the connection is initiated.

        This routine happens to communicate with a wide variety of network
        scanners when listening on the default port on a public IP address.
        """
        # According to Roger Espel Llima (espel@drakkar.ens.fr), you can
        #   have your server send a sequence of control characters:
        # (0xff 0xfb 0x01) (0xff 0xfb 0x03) (0xff 0xfd 0x0f3).
        #   Which translates to:
        # (IAC WILL ECHO) (IAC WILL SUPPRESS-GO-AHEAD)
        # (IAC DO SUPPRESS-GO-AHEAD).
        self.client.request_will_echo()
        self.client.request_will_sga()
        self.client.request_do_sga()
        # add DO & WILL BINARY, for utf8 input/output.
        self.client.request_do_binary()
        self.client.request_will_binary()
        # and terminal type, naws, and env,
        self.client.request_do_ttype()
        self.client.request_do_naws()
        self.client.request_do_env()
        self.client.send()  # push

    def run(self):
        """
        Negotiate and inquire about terminal type, telnet options, window size,
        and tcp socket options before spawning a new session.
        """
        try:
            self._set_socket_opts()
            mrk_bytes = self.client.bytes_received

            self.banner()

            # wait at least {TIME_NEGOTIATE} for the client to speak.
            # If it doesn't, we try only TTYPE.
            # If it fails to report that, we forget the rest.
            self.log.debug('{client.addrport}: pausing for negotiation'
                           .format(client=self.client))
            st_time = time.time()
            while ((0 == self.client.bytes_received
                    or mrk_bytes == self.client.bytes_received)
                   and time.time() - st_time < self.TIME_NEGOTIATE):
                if not self.client.is_active():
                    return
                if self.client.send_ready():
                    self.client.send()
                time.sleep(self.TIME_POLL)

            if self._check_ttype(start_time=st_time):
                # if client is able to negotiate terminal type,
                # try NAWS or ENV negotiation.
                if self.client.is_active():
                    self._check_env(start_time=st_time)
                if self.client.is_active():
                    self._check_naws(start_time=st_time)

            self.set_encoding()

            if self.client.is_active():
                return spawn_client_session(client=self.client)
        except (Disconnected, socket.error) as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        except EOFError:
            self.log.debug('{client.addrport}: EOF from client'
                           .format(client=self.client))
        except Exception as err:
            self.log.debug('{client.addrport}: connection closed: {err}'
                           .format(client=self.client, err=err))
        finally:
            self.stopped = True
        self.client.deactivate()

    def set_encoding(self):
        # set encoding to utf8 for clients negotiating BINARY mode and
        # not beginning with TERM 'ansi'.
        #
        # This assumes a very simple dualistic model: modern unix terminal
        # (probably using bsd telnet client), or SyncTerm.
        #
        # Clients *could* negotiate CHARSET for encoding, or simply forward a
        # LANG variable -- SyncTerm does neither. So we just assume any
        # terminal that says its "ansi" is just any number of old-world DOS
        # terminal emulating clients that are incapable of comprehending
        # "encoding" (Especially multi-byte!), they only decide upon a "font"
        # or "code page" to map char 0-255 to.
        #
        self.client.env['encoding'] = 'cp437'
        local = self.client.check_local_option
        remote = self.client.check_remote_option
        term = self.client.env.get('TERM', 'ansi')

        if (local(BINARY) and remote(BINARY) and not term.startswith('ansi')):
            self.client.env['encoding'] = 'utf8'

    def _timeleft(self, st_time):
        """
        Returns True when difference of current time and st_time is below
        TIME_WAIT_STAGE.
        """
        return bool(time.time() - st_time < self.TIME_WAIT_STAGE)

    def _check_env(self, start_time):
        """
        Check for NEW_ENVIRON negotiation.
        """
        def detected():
            return (self.client.check_remote_option(NEW_ENVIRON) is not UNKNOWN
                    or self.client.ENV_REPLIED)

        while not detected() and self._timeleft(start_time):
            if not self.client.is_active():
                return
            if self.client.send_ready():
                self.client.send()
            time.sleep(self.TIME_POLL)

        if detected():
            self.log.debug('{client.addrport}: ENV={client.env!r}.'
                           .format(client=self.client))
        else:
            self.log.debug('{client.addrport}: request-do-new_environ failed.'
                           .format(client=self.client))

    def _check_naws(self, start_time):
        """
        Check for NAWS negotiation.
        """
        def detected():
            return (self.client.env.get('LINES', None) is not None
                    and self.client.env.get('COLUMNS', None) is not None)

        while not detected() and self._timeleft(start_time):
            if not self.client.is_active():
                return
            if self.client.send_ready():
                self.client.send()
            time.sleep(self.TIME_POLL)

        if detected():
            self.log.debug('{client.addrport}: COLUMNS={client.env[COLUMNS]}, '
                           'LINES={client.env[LINES]}.'
                           .format(client=self.client))
        else:
            self.log.debug('{client.addrport}: request-do-naws failed.'
                           .format(client=self.client))

    def _check_ttype(self, start_time):
        """
        Check for TTYPE negotiation.
        """
        def detected():
            return self.client.env['TERM'] != self.client.TTYPE_UNDETECTED

        while not detected() and self._timeleft(start_time):
            if not self.client.is_active():
                return False
            if self.client.send_ready():
                self.client.send()
            time.sleep(self.TIME_POLL)

        if detected():
            self.log.debug('{client.addrport}: TERM={client.env[TERM]}.'
                           .format(client=self.client))
            return True
        self.log.debug('{client.addrport}: request-terminal-type failed.'
                       .format(client=self.client))
        return False


class TelnetServer(BaseServer):

    """
    Poll sockets for new connections and sending/receiving data from clients.
    """

    client_factory = TelnetClient
    connect_factory = ConnectTelnet
    client_factory_kwargs = dict(on_naws=on_naws)

    # Dictionary of active clients, (file descriptor, TelnetClient,)
    clients = {}

    def __init__(self, config):
        """
        Create a new Telnet Server.

        :param ConfigParser.ConfigParser config: configuration section
                                         ``[telnet]``, with options ``'addr'``,
                                         ``'port'``
        """
        self.log = logging.getLogger(__name__)
        self.address = config.get('telnet', 'addr')
        self.port = config.getint('telnet', 'port')

        # bind
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.address, self.port))
            self.server_socket.listen(self.LISTEN_BACKLOG)
        except socket.error as err:
            self.log.error('Unable to bind {0}:{1}: {2}'
                           .format(self.address, self.port, err))
            exit(1)
        self.log.info('telnet listening on {self.address}:{self.port}/tcp'
                      .format(self=self))
