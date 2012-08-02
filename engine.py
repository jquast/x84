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
  import db, session, scripting, telnet, local, finger, terminal
  if logHandler is not None:
    for mod in (db, session, scripting, telnet, local, finger, terminal):
      try:
        getattr(mod,'logger').addHandler (logHandler)
      except Exception, e:
        raise Exception, 'could not addHandler %s to module %s: %s' % (logHandler, mod, e)
        raise Exception, e
    logger.addHandler (logHandler) # engine


  # initialize the database subsystem
  db.openDB ()
  scriptpath = db.cfg.get('system','scriptpath')

  # Initialize script cache, preload with bbs.py
  scripting.scriptinit (scriptpath)

  local_ttys = db.cfg.get('system', 'local_ttys')
  if local_ttys:
    local_ttys = [t.strip() for t in local_ttys.split(',')]
    for ttyname in local_ttys:
      term = local.LocalTerminal(ttyname)
      reactor.addReader (term)
      logger.info ('[tty%s] type: %r info: %r on LocalTerminal', term.tty, term.type, term.info)

  local_wfc = db.cfg.get('system', 'local_wfc')
  if local_wfc:
    wfcscript = db.cfg.get('system', 'wfcscript')
    assert wfcscript
    print 'using wfcscript', wfcscript
    term = local.LocalTerminal(local_wfc, wfcscript)
    reactor.addReader (term)
    logger.info ('[tty%s] type: %r info: %r on WFC', term.tty, term.type, term.info)

  # XXX todo: support binding to specific IP's XXX

  telnet_port = db.cfg.get('system', 'telnet_port')
  assert telnet_port, 'No telnet port defined for listening!'
  telnetFactory = telnet.TelnetFactory()
  reactor.listenTCP (int(telnet_port), telnetFactory)
  logger.info ('[telnet:%s] listening tcp', telnet_port)

  # XXX: We need to inject the sessionlist into the finger factory (!)@#

  finger_port = db.cfg.get('system', 'finger_port')
  if finger_port:
    fingerFactory = finger.FingerFactory(session.sessions)
    reactor.listenTCP (int(finger_port), fingerFactory)
    logger.info ('[finger:%s] listening tcp', finger_port,)

  # reactor mainloop. its hard to give up control, we'd like to
  # take twisted out of the picture soon (...)
  reactor.run ()

  # the bbs ends here
  db.close ()
