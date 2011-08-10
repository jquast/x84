"""
Telnet protocol support for X/84 BBS, http://1984.ws
$Id: telnet.py,v 1.10 2009/12/31 08:54:26 dingo Exp $
#"""
__license__ = 'ISC'
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast <dingo@1984.ws>',
                 'Copyright (c) 2005 Johannes Lundberg <johannes.lundberg@gmail.com>']

import struct
from twisted.internet.protocol import ServerFactory
from twisted.conch.telnet import Telnet
import terminal
import log

from twisted.conch.telnet import LINEMODE, NAWS, SGA, ECHO, IAC, SB, SE

# rfc1091
SEND = chr(1)
TERMTYPE = chr(24)

class TelnetProtocol (Telnet, terminal.RemoteTerminal):
  def __init__ (self, addr):
    self.type = 'telnet'
    self.info = str(addr.host) + ':' + str(addr.port)
    terminal.RemoteTerminal.__init__(self)
    Telnet.__init__(self)

# simple debug tap
#  def _write(self, data):
#    for byte in data:
#      print 'SEND', ord(byte), repr(byte)
#    Telnet._write(self, data)
#
#  def dataReceived(self, data):
#    for byte in data:
#      print 'RECV', ord(byte), repr(byte)
#    Telnet.dataReceived(self, data)

  def requestNegotiation(self, about, bytes):
    """
    Send a negotiation message for the option C{about} with C{bytes} as the
    payload.

    @see: L{ITelnetTransport.requestNegotiation}

    Twisted v8.1.0 does not send 'about' in payload, this method copied from trunk
    """
    bytes = bytes.replace(IAC, IAC * 2)
    self._write(IAC + SB + about + bytes + IAC + SE)

  def connectionMade(self):
    self.address = self.transport.getPeer()
    log.write ('telnet', 'CONNECT from %s:%s' % (self.address.host, self.address.port))

    # add the default session with no handle, the default
    # db.cfg.matrixscript will handle authentication
    self.addsession (user=None)

    # now that we have a running session, we'll do
    # some customary tcp and telnet negotiation for
    # a pleasent telnet session
    self.transport.setTcpNoDelay (True)
    self.transport.setTcpKeepAlive (True)

    self.negotiationMap[NAWS] = self.telnet_NAWS
    self.negotiationMap[TERMTYPE] = self.telnet_TERMTYPE

    # echo & supress "go-ahead", http://www.faqs.org/rfcs/rfc858.html
    self.will (ECHO)
    self.will (SGA)

    # do negotiation of window size, terminal type,
    # the self.handle_NAWS method will handle the answer
    self.do (NAWS)
    self.do (TERMTYPE)

    # request terminal type, http://www.faqs.org/rfcs/rfc1091.html
    self.requestNegotiation (TERMTYPE, SEND)

  def connectionLost(self, reason):
    terminal.RemoteTerminal.connectionLost (self, reason)
    Telnet.connectionLost (self, reason)

  def enableRemote(self, opt):
    return opt in (LINEMODE, NAWS, SGA, TERMTYPE)

  def telnet_TERMTYPE(self, bytes):
    self.xSession.setTermType (''.join(bytes[1:]).lower())

  def telnet_NAWS(self, bytes):
    " Handle negotiation of window size "
    if len(bytes) == 4:
      w, h = struct.unpack('!HH', ''.join(bytes))
      self.xSession.setWindowSize (w, h)
    else:
      log.write('telnet', 'Wrong number of NAWS bytes')

  def applicationDataReceived(self, bytes):
    terminal.RemoteTerminal.dataReceived (self, bytes)

class TelnetFactory (ServerFactory):
  def buildProtocol (self, addr):
    return TelnetProtocol(addr)
