"""
SSH protocol support for X/84 BBS, http://1984.ws
$Id: ssh.py,v 1.11 2010/01/02 00:49:50 dingo Exp $
"""
__license__ = 'ISC'
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (C) 2009 Jeffrey Quast <dingo@1984.ws>',
                 'Copyright (C) 2005 Johannes Lundberg <Johannes.Lundberg@gmail.com']

import base64
from Crypto.PublicKey import RSA, DSA
from twisted.cred import portal
from twisted.conch import error, avatar, checkers
from twisted.conch.ssh import factory, userauth, connection, session
from twisted.python import components
from twisted.internet.error import ConnectionDone
from twisted.python import failure
from twisted.internet import main
import log
import db
import ansi
from terminal import RemoteTerminal

try:
  # Twisted 8.0 introduced a general purpose random-bytes generation API.
  from twisted.python.randbytes import secureRandom
except ImportError:
  # Earlier versions of Twisted had APIs for this, but they were different.
  from twisted.conch.ssh.common import entropy
  secureRandom = entropy.get_bytes

try:
    # Twisted 8.0 introduced structured key objects with useful constructors
    # and methods.
    from twisted.conch.ssh.keys import Key
except ImportError:
    # Earlier versions of Twisted had string-based APIs for manipulating keys.
    from twisted.conch.ssh.keys import getPrivateKeyObject, getPublicKeyString
    from twisted.conch.ssh.keys import makePrivateKeyString, makePublicKeyBlob
    from twisted.conch.ssh.keys import makePublicKeyString
else:
    # Make the Key object API look like the old API
    getPrivateKeyObject = Key.fromString
    makePrivateKeyString = makePublicKeyString = lambda key,comment: Key(key).toString('openssh')
    makePrivateKeyBlob = makePublicKeyBlob = Key.blob

class SSHProtocol(RemoteTerminal):
  def __init__ (self, handle):
    self.type = 'ssh'
    self.info = '?' # XXX ip and host address
    self.handle = handle
    RemoteTerminal.__init__(self)

  def connectionMade (self):
    " Send terminal init string and create new session as avatar handle "
    # enable high-bit art for PC-DOS vga fonts,
    # enable line wrapping at right margin,
    # set graphics rendition (SGR): all attributes off,
    # display cursor
    self.write (ansi.charset() + ' ' \
              + ansi.linewrap() + ' ' \
              + ansi.color() + ' ' \
              + ansi.cursor_show() + ' ')

    # when we add our session, we assume completed authentication
    # and bypass the default matrixscript and go directly
    # to the topscript

    self.addsession (user=self.handle, scriptname=db.cfg.topscript)


class SSHFactory(factory.SSHFactory):
  def __init__(self):
    keytype=db.cfg.ssh_keytype.lower()
    self.publicKeys = { \
      'ssh-'+keytype: Key.fromString(db.cfg.ssh_hostkey_public) \
    }
    self.privateKeys = { \
      'ssh-'+keytype: Key.fromString(db.cfg.ssh_hostkey_private) \
    }
    self.services = { \
      'ssh-userauth': userauth.SSHUserAuthServer,
      'ssh-connection': connection.SSHConnection \
    }

class MySession:
  def __init__(self, avatar):
    self.avatar = avatar
    self.protocol = None
    pass

  def getPty(self, term, windowSize, attrs):
    # save for re-use in openShell()
    self.term, self.windowSize = term, windowSize
    pass

  def execCommand(self, proto, cmd):
    pass

  def openShell(self, trans):
    self.protocol = SSHProtocol(self.avatar.username)
    self.protocol.makeConnection(trans)
    trans.makeConnection(session.wrapProtocol(self.protocol))
    rows, cols, pixels_high, pixels_wide = self.windowSize
    self.protocol.xSession.setWindowSize (cols, rows)
    self.protocol.xSession.setTermType(self.term)

  def windowChanged(self, data):
    h, w = data[0], data[1]
    self.protocol.xSession.setWindowSize(w, h)

  def eofReceived(self):
    self.protocol.connectionLost (failure.Failure(main.CONNECTION_DONE))

  def closed(self):
    self.protocol.connectionLost (failure.Failure(main.CONNECTION_DONE))

class MyAvatar(avatar.ConchUser):
  def __init__(self, username):
    avatar.ConchUser.__init__(self)
    self.username = username
    self.channelLookup.update({'session':session.SSHSession})

class MyRealm:
  __implements__ = portal.IRealm,
  def requestAvatar(self, avatarId, mind, *interfaces):
    return interfaces[0], MyAvatar(avatarId), lambda: None

class PublicKeyCredentialsChecker(checkers.SSHPublicKeyDatabase):
  def checkKey(self, credentials):
    if db.users.has_key(credentials.username):
      if db.users[credentials.username].has_key('pubkey') \
      and db.users[credentials.username].pubkey:
        if base64.decodeString(db.users[credentials.username].pubkey) == credentials.blob:
          log.write('ssh','%s succeeded pubkey authentication' % (credentials.username))
          return True
        else:
          log.write('ssh','%s failed pubkey authentication' % (credentials.username))
      else:
        log.write('ssh','%s no pubkey for authentication' % (credentials.username))
    else:
      log.write('ssh','user account does not exist: %s, failed pubkey authentication' % (credentials.username))
    return False

class UserPasswordCredentialsChecker(checkers.UNIXPasswordDatabase):
  def requestAvatarId(self, credentials):
    if db.users.has_key(credentials.username):
      if db.users[credentials.username].password == credentials.password:
        log.write('ssh','%s succeeded password authentication' % (credentials.username))
        return credentials.username
      else:
        log.write('ssh','%s failed password authentication' % (credentials.username))
    else:
      log.write('ssh','user account does not exist: %s, failed password authentication' % (credentials.username))
    return UnathorizedLogin()

components.registerAdapter(MySession, MyAvatar, session.ISession)

portal = portal.Portal(MyRealm())
portal.registerChecker(PublicKeyCredentialsChecker())
portal.registerChecker(UserPasswordCredentialsChecker())
SSHFactory.portal = portal
