#!/usr/bin/env python2.6
"""
Scripting and session engine
"""
__license__ = 'ISC'
__maintainer__ = 'Jeff Quast'
__email__ = 'dingo@1984.ws'
__status__ = 'Alpha'
__version__ = '1.0rc1'
# iteration #1, pybbs? 2001 jojo, dingo contributing
# iteration #2, The Progressive (PRSV), 2004 jojo, dingo & maze contributing
#               twisted for networking, zodb for database, ssh support ...
# Copyright (C) 2004 Johannes Lundberg
# This archive can be redistributed, unmodified or modified, in whatever
# ways that may please you.
#
# THIS IS FREE SOFTWARE. USE AT YOUR OWN RISK. NO WARRANTY.

# this is iteration #3, x/84, 2010-2012 dingo
import db
import bbs.session

import sys
import traceback
import threading

def main (logger, logHandler, cfgFile='default.ini', doTAP=False):
  """
  x84 main entry point. The system begins and ends here.
  """
  import bbs.ini
  import terminal
  terminal.logger.addHandler (logHandler)
  terminal.logger.setLevel (logger.level)
  logger.addHandler (logHandler)

  bbs.session.logger.addHandler (logHandler)
  bbs.session.logger.setLevel (logger.level)
  logger.addHandler (logHandler)

  # load .ini file
  bbs.ini.init (cfgFile)

  # initialize scripting subsystem
  import bbs.scripting
  bbs.scripting.init (bbs.ini.cfg.get('session', 'scriptpath'))

  if doTAP:
    bbs.ini.cfg.set('session', 'tap_input', 'yes')
    bbs.ini.cfg.set('session', 'tap_output', 'yes')

  # initialize ftp server
  import ftp
  ftp.logger.addHandler (logHandler)
  # XXX just a hack to get it to poll ...
  client, pipe, lock = None, ftp.init(), threading.Lock()
  terminal.SESSION_CHANNELS.append ((client, pipe, lock,))

  # initialize telnet server
  import telnet
  telnet.logger.setLevel (logger.level)
  telnet.logger.addHandler (logHandler)
  telnet_port = int(bbs.ini.cfg.get('telnet', 'port'))
  telnet_addr = bbs.ini.cfg.get('telnet', 'addr')
  server = telnet.TelnetServer \
      (port=telnet_port, address=telnet_addr,
       on_connect=terminal.on_connect,
       on_disconnect=terminal.on_disconnect,
       on_naws=terminal.on_naws,
       timeout=0.01)
  logger.info ('[telnet:%s] listening tcp', telnet_port)

  # main event loop
  eof_pipes = set()
  while True:
    event = server.poll()
    for client, pipe, lock in terminal.SESSION_CHANNELS:
      # poll for keyboard input, send to session channel monitor
      if client is not None and client.input_ready():
        if lock.acquire(False):
          inp = client.get_input()
          lock.release()
          pipe.send (('input', inp))

      # poll for events received on child process pipe
      if pipe.poll():
        try:
          if not lock.acquire(False):
            # this client currently 'locked', by POSHandler, likely.
            continue
          lock.release ()
          try:
            event, data = pipe.recv()
          except TypeError, e:
            logger.error (e)
            continue
          if event == 'disconnect':
            client.deactivate ()
          elif event == 'output':
            # data to send
            if not lock.acquire (False):
              # somebody slipped us a lock. ignore for this pass,
              continue
            client.send (*data)
            lock.release ()
          elif event == 'global':
            pass
#            # broadcast: repeat data as global to all other channels
#            for (c,p,l) in terminal.SESSION_CHANNELS:
#              if c != client:
#                p.send ((event, data))
          elif event == 'pos':
            # query: what is the cursor position ?
            t = terminal.POSHandler(pipe, client, lock, event, data)
            t.start ()
          elif event.startswith ('db-'):
            # query: database dictionary method
            t = db.DBHandler(pipe, event, data)
            t.start ()
          else:
            assert 0, 'Unhandled event: %s' % ((event,data,),)
        except EOFError:
          eof_pipes.add ((client, pipe, lock))
    while 0 != len(eof_pipes):
      terminal.SESSION_CHANNELS.remove (eof_pipes.pop())


if __name__ == '__main__':
  # TODO: Proper getopts
  import sys
  import logging
  import log
  logger = logging.getLogger(__name__)
  logger.setLevel(logging.INFO)
  sys.stdout.write ('x/84 bbs ')
  log_level = logging.INFO
  cfgFile = 'default.ini'
  doTAP=False
  if '-v' in sys.argv:
    sys.argv.remove('-v')
    log_level = logging.DEBUG
    logger.setLevel(log_level)
  if '-cfg' in sys.argv:
    cfgFile = sys.argv[sys.argv.index('-cfg')+1]
    sys.argv.remove(cfgFile)
    sys.argv.remove('-cfg')
  if '-tap' in sys.argv:
    doTAP = True
  logHandler = log.get_stderr(level=log_level)
  sys.stdout.flush()
  main (logger, logHandler, cfgFile, doTAP)
