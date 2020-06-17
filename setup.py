#! /usr/bin/env python
""" Distribution file for x/84. """
from __future__ import print_function
import subprocess
import pipes
import errno
import sys
import os

# pylint: disable=E0611,F0401
#         No name 'core' in module 'distutils'
#         Unable to import 'distutils.core'
from distutils.core import setup
from setuptools import Command

HERE = os.path.dirname(__file__)
README = 'README.rst'
DOC_URL = 'http://x84.rtfd.org'


setup(name='x84',
      version='2.0.17',
      description=("Framework for Telnet and SSH BBS or MUD server "
                   "development with example default bbs board"),
      long_description=open(os.path.join(HERE, README)).read(),
      author='Jeff Quast',
      author_email='contact@jeffquast.com',
      url=DOC_URL,
      keywords="telnet ssh terminal server ansi bbs mud curses utf8 cp437",
      license='ISC',
      packages=['x84', 'x84.default', 'x84.default.art', 'x84.bbs',
                'x84.encodings', 'x84.webmodules'],
      package_data={
          '': [README],
          'x84.default': ['*.ans', '*.txt', ],
          'x84.default.art': ['*.asc', '*.ans', '*.txt',
                              'top/*',
                              'weather/*',
                              'bulletins/*/*',
                              ],
      },
      install_requires=[
          'blessed>=1.17.8,<2',
          'feedparser>=5.2.1,<6',
          'html2text==2019.8.11',
          'hgtools==8.1.1',
          'requests>=2.23.0,<3',
          'sauce>=1.2,<2',
          'six>=1.15.0,<2',
          'sqlitedict>=1.6.0,<2',
          'wcwidth>=0.2.4,<1',
          'python-dateutil>=2.8.1,<3',
          'backports.functools-lru-cache>=1.6.1,<2'
      ],
      extras_require={
          'with_crypto': (
              'bcrypt>=3.1.7,<4',
              'cherrypy>=17.4.2,<18',
              'cryptography>=2.9.2,<3',
              'paramiko>=2.7.1,<3',
              'web.py>=0.51,<1',
          )
      },
      entry_points={
          'console_scripts': ['x84=x84.engine:main'],
      },
      classifiers=[
          'Environment :: Console :: Curses',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: ISC License (ISCL)',
          'Natural Language :: English',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: POSIX :: BSD :: FreeBSD',
          'Operating System :: POSIX :: BSD :: NetBSD',
          'Operating System :: POSIX :: BSD :: OpenBSD',
          'Operating System :: POSIX :: BSD',
          'Operating System :: POSIX :: Linux',
          'Operating System :: POSIX :: SunOS/Solaris',
          'Operating System :: POSIX',
          'Operating System :: Unix',
          'Programming Language :: Python :: 2 :: Only',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Artistic Software',
          'Topic :: Communications :: BBS',
          'Topic :: Software Development :: User Interfaces',
          'Topic :: Terminals :: Telnet',
          'Topic :: Terminals',
      ],
      zip_safe=False,
)
