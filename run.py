#!/usr/bin/env python2.6
"""
Command line launcher for x/84 bbs.
"""
import sys, logging
"""
 Main entry point for X/84 bbs, http://1984.ws
"""
__license__ = 'ISC'
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = 'Copyright (C) 2011 Jeffrey Quast <dingo@1984.ws>',

if __name__ == '__main__':
  sys.stdout.write ('x/84 bbs ')
  import engine
  import log
  log_level = logging.INFO
  logOut = log.get_stderr(level=log_level)
  if '-v' in sys.argv:
    sys.argv.remove('-v')
    log_level = logging.DEBUG
  sys.stdout.flush()
  engine.main(logHandler=logOut)
