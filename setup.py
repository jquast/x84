#! /usr/bin/env python
"""
Distribution file for x/84
"""
from distutils.core import setup

setup(name='x84',
      version='1.0.2',
      description="Telnet server with default 'scene bbs'",
      author='Jeff Quast',
      author_email='contact@jeffquast.com',
      url='http://github.com/jquast/x84/',
      keywords='telnet, terminal, server, ansi, bbs, mud, curses, utf8, cp437',
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
          'Classifier: Development Status :: 4 - Beta',
          'Classifier: Environment :: Console',
          'Classifier: Environment :: Console :: Curses',
          'Classifier: Intended Audience :: Developers',
          'Classifier: License :: OSI Approved :: ISC License (ISCL)',
          'Classifier: Natural Language :: English',
          'Classifier: Operating System :: MacOS :: MacOS X',
          'Classifier: Operating System :: POSIX',
          'Classifier: Operating System :: POSIX :: BSD',
          'Classifier: Operating System :: POSIX :: BSD :: FreeBSD',
          'Classifier: Operating System :: POSIX :: BSD :: NetBSD',
          'Classifier: Operating System :: POSIX :: .BSD :: OpenBSD',
          'Classifier: Operating System :: POSIX :: Linux',
          'Classifier: Operating System :: POSIX :: SunOS/Solaris',
          'Classifier: Operating System :: Unix',
          'Classifier: Programming Language :: Python :: 2.6',
          'Classifier: Programming Language :: Python :: 2.7',
          'Classifier: Programming Language :: Python :: 2 :: Only',
          'Classifier: Topic :: Artistic Software',
          'Classifier: Topic :: Communications :: BBS',
          'Classifier: Topic :: Software Development :: Libraries :: Application Frameworks',
          'Classifier: Topic :: Software Development :: User Interfaces',
          'Classifier: Topic :: System :: Console Fonts',
          'Classifier: Topic :: Terminals',
          'Classifier: Topic :: Terminals :: Telnet',],
      )
