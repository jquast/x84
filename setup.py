#! /usr/bin/env python
"""
Distribution file for x/84
"""
from __future__ import print_function
import subprocess
import warnings
import platform
import pipes
import errno
import sys
import os
from distutils.core import setup
from distutils.sysconfig import get_python_inc
from distutils.unixccompiler import UnixCCompiler

from setuptools.command.develop import develop as _develop
from setuptools import Command


HERE = os.path.dirname(__file__)
README = 'README.rst'
DOC_URL = 'http://x84.rtfd.org'


def check_virtualenv():
    """
    Used for commands that require a virtualenv -- when VIRTUAL_ENV
    is not set, prints an error and exits 1.
    """
    if not os.getenv('VIRTUAL_ENV'):
        print('You must be in a virtualenv, See developer documentation '
              'at filepath docs/developers.rst or online at {0}'
              .format(DOC_URL), file=sys.stderr)
        exit(1)


class develop(_develop):
    """ This derived develop command class ensures virtualenv and requirements. """
    def finalize_options(self):
        check_virtualenv()
        _develop.finalize_options(self)

    def run(self):
        cargs = ['pip', 'install', '--upgrade', 'sphinx', 'tox']
        print('>>', ' '.join(map(pipes.quote, list(cargs))))
        subprocess.check_call(cargs)
        _develop.run(self)


class build_docs(Command):
    """ Build documentation using sphinx. """
    #: path to source documentation folder.
    DOCS_SRC = os.path.join(HERE, 'docs')

    #: path to output html documentation folder.
    DOCS_DST = os.path.join(HERE, 'build', 'docs')

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        check_virtualenv()

    def run(self):
        " Call sphinx-build. "
        try:
            subprocess.call(
                ('sphinx-build', '-E', self.DOCS_SRC, self.DOCS_DST),
                stdout=sys.stdout, stderr=sys.stderr)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise
            print("You must install 'sphinx' to build documentation.",
                  file=sys.stderr)
            sys.exit(1)


setup(name='x84',
      version='1.9.84',
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
                              'weather/*',
                              'bulletins/*/*',
                              ],
      },
      install_requires=[
          'blessed==1.9.5',
          'requests==2.5.1',
          'irc==9.0',
          'sqlitedict==1.1.0',
          'wcwidth==0.1.4',
          'python-dateutil==2.3',
          'jaraco.timing==1.1',
          'jaraco.util==10.6',
          'more-itertools==2.2',
          'sauce==1.1',
          'six==1.8.0',
          'wsgiref==0.1.2',
          'xmodem==0.3.2',
      ],
      extras_require={
          'with_crypto': (
              # These cryptogaphy requirements may only be installed:
              # - if a C compiler is available,
              # - if libssl is available,
              # - (sometimes, only) if libffi is available
              #
              # for this reason, they are **optional**, so that x/84 may be installed
              # without a compiler or these external C libraries -- however it is
              # highly recommended to always try to install x84[with_crypto].
              'bcrypt==1.1.0',
              'cffi==0.8.6',
              'cryptography==0.7.1',
              'ecdsa==0.11',
              'enum34==1.0.4',
              'paramiko==1.15.2',
              'pyOpenSSL==0.14',
              'pyasn1==0.1.7',
              'pycparser==2.10',
              'pycrypto==2.6.1',
              'web.py==0.37',
              'cherrypy==3.6.0',
          )
      },
entry_points = {
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
cmdclass={
    'develop': develop,
    'docs': build_docs,
},
zip_safe=False,
)
