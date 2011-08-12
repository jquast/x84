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

import log, logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main(logHandler=None):
  """
  x84 main entry point. The system begins and ends here.
  """
  import db, session, scripting, telnet, local, finger
  if logHandler is not None:
    for mod in (db, session, scripting, telnet, local, finger):
      try:
        getattr(mod,'logger').addHandler (logHandler)
      except Exception, e:
        raise Exception, 'could not addHandler %s to module %s: %s' % (logHandler, mod, e)
        raise Exception, e
    logger.addHandler (logHandler) # engine

  # initialize the database subsystem
  db.openDB ()

  # Initialize script cache, preload with bbs.py
  scripting.scriptinit ()

  for ttyname in db.cfg.local_ttys:
    term = local.LocalTerminal(ttyname)
    reactor.addReader (term)
    logger.info ('[tty%s] type: %r info: %r on LocalTerminal', term.tty, term.type, term.info)

  if db.cfg.local_wfc:
    term = local.LocalTerminal(db.cfg.local_wfc, db.cfg.wfcscript)
    reactor.addReader (term)
    logger.info ('[tty%s] type: %r info: %r on WFC', term.tty, term.type, term.info)

  # TODO: if /dev/tty is not used as a line, then fork as daemon and exit

  telnetFactory = telnet.TelnetFactory()
  for port in db.cfg.telnet_ports:
    reactor.listenTCP (port, telnetFactory)
    logger.info ('[telnet:%i] listening tcp', port)

  # XXX: We need to inject the sessionlist into the finger factory
  fingerFactory = finger.FingerFactory(session.sessions)
  if db.cfg.finger_port:
    reactor.listenTCP (db.cfg.finger_port, fingerFactory)
    logger.info ('[finger:%i] listening tcp', db.cfg.finger_port,)

  reactor.run ()
  # the bbs ends here
  db.close ()
