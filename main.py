#!/usr/bin/env python
"""
 Main entry point for X/84 bbs, http://1984.ws
 $Id: main.py,v 1.5 2010/01/01 09:32:14 dingo Exp $
"""
__license__ = 'ISC'
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (C) 2009 Jeffrey Quast <dingo@1984.ws>',
                 'Copyright (C) 2005 Johannes Lundberg <Johannes.Lundberg@gmail.com']

if __name__ == '__main__':
  import sys
  sys.stdout.write ('x/84 bbs loading engine...')
  sys.stdout.flush()
  import engine
  print 'main()'
  engine.main()
