#! /usr/bin/env python
"""
Distribution file for x/84
"""
from distutils.core import setup

setup(name='x84',
      version='1.0.2',
      description='UTF-8 telnet server with default "scene board"',
      author='Jeff Quast',
      author_email='contact@jeffquast.com',
      url='http://github.com/jquast/x84/',
      keywords=[
          'telnet', 'terminal', 'server', 'ansi', 'bbs', 'mud',
          'curses', 'multiprocessing', 'ttyrec', 'ttyplay',
          'sqlite', 'utf8', 'cp437', 'rfc854', 'rfc856', 'rfc857',
          'rfc858', 'rfc859', 'rfc1073', 'rfc1572', 'naws',
          'xterm', 'unix', 'posix', 'doors'],
      license='ISC',
      packages=['x84', 'x84.default', 'x84.default.art', 'x84.bbs'],
      package_data={
          '': ['README.rst'],
          'x84.default': ['*.ans',],
          'x84.default.art': ['*.asc', '*.ans', '*.txt'],
      },
      requires=['requests', 'sauce', 'sqlitedict'],
      scripts=['bin/x84'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Environment :: Console',
          'License :: OSI Approved :: ISC License (ISCL)',
          'Natural Language :: English',
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
          'Topic :: Terminals :: Telnet',]
      )
