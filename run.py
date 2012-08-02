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
  log_level = logging.DEBUG if '-d' in sys.argv else logging.INFO
  sys.stdout.write ('x/84 bbs ')
  sys.stdout.flush()
  import log, engine
  engine.main(logHandler=log.get_stderr(level=log_level))
