#! /usr/bin/env python
"""
Distribution module for the X/84 BBS
"""

#pylint: disable=E0611,F0401
# ?      No name 'core' in module 'distutils'
# ?      Unable to import 'distutils.core'
from distutils.core import setup

setup(name         = 'X84',
      version      = '3.0-rc1',
      description  = 'X/84 Progressive BBS',
      author       = 'Jeff Quast',
      author_email = 'dingo@1984.ws',
      url          = 'http://1984.ws/',
      packages     = [
                        'x84',
                        'x84.default',
                        'x84.bbs',
      ],
      package_data = {
                        'x84':         ['*.ini'
                                        'data/*',
                                        'default/art/*.ans',
                                        'default/art/*.asc'],
      },
      requires     = ['blessings', 'sauce', 'sqlitedict', 'xmodem'],
      scripts      = ['bin/x84'],
)
