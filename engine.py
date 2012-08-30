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

import threading
import multiprocessing
import Queue
import logging
import os

import log
logger = logging.getLogger(__name__)
#logger = multiprocessing.get_logger()#__name__)
logger.setLevel(logging.DEBUG)
logger.warning('doomed')

def main(logHandler=None):
  """
  x84 main entry point. The system begins and ends here.
  """
  import db, scripting, terminal, session, miniboa
  scripting.logger.addHandler (logHandler)
  terminal.logger.addHandler (logHandler)
  session.logger.addHandler (logHandler)
  miniboa.telnet.logger.addHandler (logHandler)

  # initialize the database subsystem
  db.openDB ()
  scriptpath = db.cfg.get('system','scriptpath')

  # Initialize script cache, preload with bbs.py
  scripting.scriptinit (scriptpath)

  telnet_port = int(db.cfg.get('system', 'telnet_port'))
  telnet_addr = db.cfg.get('system', 'telnet_addr')

  server = miniboa.TelnetServer \
      (port=telnet_port, address='0.0.0.0',
       on_connect=terminal.on_connect,
       on_disconnect=terminal.on_disconnect,
       timeout=0.01)

  logger.info ('[telnet:%s] listening tcp', telnet_port)
  eof_errors = list()
  while True:
    event = server.poll()
    for client, pipe in terminal.CHANNELS:
      # poll for keyboard input, send to session channel monitor
      if client.input_ready:
        inp = client.get_input()
        pipe.send (('input', inp))
      if pipe.poll():
        try:
          event, data = pipe.recv()
          assert event in ('output',), \
              'Unhandled event: %s' % (event,)
          if event == 'output':
            client.send (data)
        except EOFError:
          eof_errors.append ((client, pipe))
    while 0 != len(eof_errors):
      terminal.CHANNELS.remove (eof_errors.pop())

  # the bbs ends here
  db.close ()
