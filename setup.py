#! /usr/bin/env python
"""
Distribution file for x/84
"""
from distutils.core import setup

setup(name = 'x84', version = '1.0.1',
        description = 'UTF-8 Telnet BBS',
        author = 'Jeff Quast', author_email = 'dingo@1984.ws',
        url = 'http://github.com/jquast/x84/',
        license = 'ISC',
        packages = ['x84', 'x84.default', 'x84.bbs',],
        package_data = {
            '': ['README.rst'],
            'x84.default': ['art/*.asc', 'art/*.ans', 'art/*.txt'
                'art/top/*.ans', 'art/top/*.asc'],
            },
        requires = ['py_bcrypt', 'requests', 'sauce', 'sqlitedict',
            'xmodem', ],
      scripts = ['bin/x84'],
      classifiers = [ 'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: ISC License (ISCL)',
          'Operating System :: Unix',
          'Operating System :: MacOS :: MacOS 9',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: BSD',
          'Operating System :: POSIX :: Linux',
          'Operating System :: POSIX :: SunOS/Solaris',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Communications :: BBS',
          'Topic :: Terminals :: Telnet', ]
      )
