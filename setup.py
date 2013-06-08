#! /usr/bin/env python
"""
Distribution file for x/84
"""
from distutils.core import setup
import os

setup(name='x84',
      version='1.0.7',
      description="Telnet server for UTF-8 and cp437 terminals.",
      long_description=open(os.path.join(os.path.dirname(__file__),
                                         'README.txt')).read(),
      author='Jeff Quast',
      author_email='contact@jeffquast.com',
      url='http://x84.rtfd.org/',
      keywords='telnet, terminal, server, ansi, bbs, mud, curses, utf8, cp437',
      license='ISC',
      packages=['x84', 'x84.default', 'x84.default.art', 'x84.bbs'],
      package_data={
          '': ['README.txt'],
          'x84.default': ['*.ans', '*.txt', ],
          'x84.default.art': ['*.asc', '*.ans', '*.txt'],
      },
      install_requires=[
          'requests >=1.1.0',
          'sauce >=0.1.1',
          'sqlitedict >=1.0.8'],
      scripts=['bin/x84'],
      classifiers=[
          'Environment :: Console',
          'Environment :: Console :: Curses',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: ISC License (ISCL)',
          'Natural Language :: English',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: POSIX',
          'Operating System :: POSIX :: BSD',
          'Operating System :: POSIX :: BSD :: FreeBSD',
          'Operating System :: POSIX :: BSD :: NetBSD',
          'Operating System :: POSIX :: BSD :: OpenBSD',
          'Operating System :: POSIX :: Linux',
          'Operating System :: POSIX :: SunOS/Solaris',
          'Operating System :: Unix',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 2 :: Only',
          'Topic :: Artistic Software',
          'Topic :: Communications :: BBS',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'Topic :: Software Development :: User Interfaces',
          'Topic :: System :: Console Fonts',
          'Topic :: Terminals',
          'Topic :: Terminals :: Telnet', ],
      )
