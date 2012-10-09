#!/usr/bin/env python2.6
"""
Scripting and session engine
"""
__license__ = 'ISC'
__maintainer__ = 'Jeff Quast'
__email__ = 'dingo@1984.ws'
__status__ = 'Alpha'
__version__ = '1.0rc1'
# iteration #1, pybbs? 2001 jojo, dingo contributing, public domain
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

def main (logger, logHandler, cfgFile='default.ini'):
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

  # initialize telnet server
  import telnet
  telnet.logger.setLevel (logger.level)
  telnet.logger.addHandler (logHandler)
  telnet_port = int(bbs.ini.cfg.get('telnet', 'port'))
  telnet_addr = bbs.ini.cfg.get('telnet', 'addr')
  telnet_server = telnet.TelnetServer \
      (port=telnet_port, address=telnet_addr,
       on_connect=terminal.on_connect,
       on_disconnect=terminal.on_disconnect,
       on_naws=terminal.on_naws,
       on_env=terminal.on_env,
       timeout=0.01)
  logger.info ('[telnet:%s] listening tcp', telnet_port)

  if bbs.ini.cfg.get('ftp', 'enabled', 'no'):
    # initialize ftp server
    import ftp
    ftp.logger.addHandler (logHandler)
    ftp_eventpipe = ftp.init()
    #ftp_lock = threading.Lock()

  # main event loop
  eof_pipes = set()
  while True:
    event, data = (None, None)

    # process telnet server i/o, byte buffers ..
    telnet_server.poll()

    # process ftp server i/o
    if bbs.ini.cfg.get('ftp', 'enabled', 'no') == 'yes':
      if ftp_eventpipe.poll():
        # ftp child process sent us a gift
        event, data = ftp_eventpipe.recv()

    for client, pipe, lock in terminal.registry[:]:
      if not lock.acquire(False):
        # this client currently 'locked', by POSHandler, likely.
        continue
      lock.release ()

      # process telnet input as keypresses 'input' events,
      if client.input_ready() and lock.acquire(False):
        lock.release()
        inp = client.get_input()
        pipe.send (('input', inp))

      # process bbs session i/o, requests from child processes,
      if False == pipe.poll ():
        # no session i/o to process, next client,
        continue

      try:
        # session i/o sent from child process
        event, data = pipe.recv()

      except EOFError:
        logger.info ('eof,')
        terminal.registry.remove ((client, pipe, lock))
        continue

      if event == 'disconnect':
        client.deactivate ()

      elif event == 'output':
        text, cp437 = data
        if cp437 == True:
          print repr(text)
          client.send_str (bytes(text.encode('iso8859-1')))
          # probobly should catch conversion errors,
          # decode as iso8859-1, and try again ?
        else:
          assert cp437 == False
          client.send_unicode (text)

      # broadcast event to all other telnet clients,
      elif event == 'global':
        for (c,p,l) in terminal.registry:
            if c != client:
              p.send ((event, data,))

      elif event == 'pos':
        # assert 'timeout' parameter
        assert type(data) in (float, int, type(None))
        # 'pos' query: 'what is the cursor position ?'
        # 'pos-reply' event is a callback mechanism
        # data of (None, None) indicates timeout
        t = terminal.POSHandler(pipe, client, lock,
            reply_event='pos-reply', timeout=data)
        t.start ()

      elif event.startswith ('db-'):
        # db query-> database dictionary method, callback
        # with a matching ('db-*',) event. sqlite is used
        # for now and is quick, but this prevents slow
        # database queries from locking the i/o event loop.
        t = db.DBHandler(pipe, event, data)
        t.start ()

      elif event == 'env':
        # data is dictionary of key, values
        matches = set()
        for key, value in data:
          if not key in client.env \
          or not client.env[key] == value:
            client.env[key] = value
            matches.add (key)
        # notify userland of env updated variables ..
        if 0 != len(matches):
          p.send ((event, matches,))
      else:
        assert 0, 'Unhandled event: %s' % ((event,data,),)


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
  if '-v' in sys.argv:
    sys.argv.remove('-v')
    log_level = logging.DEBUG
    logger.setLevel(log_level)
  if '-cfg' in sys.argv:
    cfgFile = sys.argv[sys.argv.index('-cfg')+1]
    sys.argv.remove(cfgFile)
    sys.argv.remove('-cfg')
  logHandler = log.get_stderr(level=log_level)
  sys.stdout.flush()
  main (logger, logHandler, cfgFile)
