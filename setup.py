#! /usr/bin/env python
"""
Distribution module for the X/84 BBS
$Id: setup.py,v 1.2 2009/05/18 15:40:27 maze Exp $

"""
__author__ = 'Wijnand Modderman <python@tehmaze.com>'
__copyright__ = 'Copyright (c) 2006, 2007, 2009 Jeffrey Quast, Johannes Lundberg, Wijnand Modderman'
__license__ = 'ISC'

from distutils.core import setup

setup(name         = 'X84',
      version      = '0.0.1',
      description  = 'X/84 Progressive BBS',
      author       = 'Jeff Quast',
      author_email = 'dingo@1984.ws',
      url          = 'http://1984.ws/',
      packages     = [
                        'x84', 
                        'x84.default', 
                        'x84.games',
                        'x84.games.sots',
                        'x84.script', 
                        'x84.ui'
      ],
      package_dir  = {
                        'x84':            '',
                        'x84.default':    'default',
                        'x84.games':      'games',
                        'x84.games.sots': 'games/sots',
                        'x84.script':     'script',
                        'x84.ui':         'ui',
      },
      package_data = {
                        'x84':         ['*.cfg'
                                        'default/art/*.ans',
                                        'default/art/*.asc'],
      },
      requires     = ['ZODB'],
      scripts      = ['x84'],
      data_files   = [('doc', ['doc/readme.1st', 'doc/readme.txt'])],
)

