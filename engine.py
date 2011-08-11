"""
Scripting and session engine
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = 'Copyright (C) 2011 Jeffrey Quast'
__license__ = 'ISC'
__maintainer__ = 'Jeffrey Quast'
__email__ = 'dingo@1984.ws'
__status__ = 'Alpha'
__version__ = '3.0rc0'
# version 1, unnamed? 2001 johannes, 2003 jeff
# version 2, PRSV, 2008 johannes, 2010 jeff
# version 3, x84, 2011 jeff

# 3rd party modules (dependencies)
from twisted.internet import reactor
from twisted.python import threadable

# python modules
import threading as threading
import traceback as traceback
from StringIO import StringIO
import exceptions
import os.path
import thread
import string
import Queue
import time
import imp
import sys
import os

# refactoring... jdq
# prsv modules
import db
import log
#import ansi
#import keys
#import strutils
#import fileutils
#import exception

import session
import scripting

#import terminal
import telnet
#import ssh
import local
import finger

def main():
  """
  x84 main entry point. The system begins and ends here.
  """
  # initialize the database subsystem
  db.openDB ()

  # Initialize script cache, preload with bbs.py
  scripting.scriptinit ()

  for ttyname in db.cfg.local_ttys:
    term = local.LocalTerminal(ttyname)
    reactor.addReader (term)
    log.write ('tty%s' % (term.tty,), '%s terminal on %s' \
      % (term.type, term.info,))

  if db.cfg.local_wfc:
    term = local.LocalTerminal(db.cfg.local_wfc, db.cfg.wfcscript)
    reactor.addReader (term)
    log.write ('tty%s' % (term.tty,), '%s terminal on %s for %s' % \
      (term.type, term.info, db.cfg.local_wfc,))

  # TODO: if /dev/tty isn't attached to any lines, fork as a daemon and exit

  telnetFactory = telnet.TelnetFactory()
  for port in db.cfg.telnet_ports:
    reactor.listenTCP (port, telnetFactory)
    log.write ('telnet', 'listening on tcp port %s' % (port,))

  # XXX: We need to inject the sessionlist into the finger factory
  fingerFactory = finger.FingerFactory(session.sessions)
  if db.cfg.finger_port:
    reactor.listenTCP (db.cfg.finger_port, fingerFactory)
    log.write ('finger', 'listening on tcp port %s' % (db.cfg.finger_port,))
  reactor.run ()
  # the bbs ends here
  db.close ()


