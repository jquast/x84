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
from setuptools.command.develop import develop as _develop
from setuptools import Command

HERE = os.path.dirname(__file__)
README = 'README.rst'
DOC_URL = 'http://x84.rtfd.org'


def check_virtualenv():
    """ Ensure a virtualenv is used. """
    if not os.getenv('VIRTUAL_ENV'):
        print('You must be in a virtualenv, See developer documentation '
              'at filepath docs/developers.rst or online at {0}'
              .format(DOC_URL), file=sys.stderr)
        exit(1)


class Develop(_develop):

    """ Ensure a virtualenv is used and install developer requirements. """

    def finalize_options(self):
        """ Validate options. """
        check_virtualenv()
        _develop.finalize_options(self)

    def run(self):
        """ Run develop command. """
        cargs = ['pip', 'install', '--upgrade', 'sphinx', 'tox']
        print('>>', ' '.join(map(pipes.quote, list(cargs))))
        subprocess.check_call(cargs)
        _develop.run(self)


class BuildDocs(Command):

    """ Build documentation using sphinx. """

    #: path to source documentation folder.
    DOCS_SRC = os.path.join(HERE, 'docs')

    #: path to output html documentation folder.
    DOCS_DST = os.path.join(HERE, 'build', 'docs')

    user_options = []

    def initialize_options(self):
        """ Initialize options. """
        pass

    def finalize_options(self):
        """ Validation options. """
        # pylint: disable=R0201
        #         Method could be a function
        check_virtualenv()

    def run(self):
        """ Call sphinx-build. """
        try:
            subprocess.call(
                ('sphinx-build', '-v', '-n', '-E',
                 self.DOCS_SRC, self.DOCS_DST),
                stdout=sys.stdout, stderr=sys.stderr)
        except OSError as err:
            if err.errno != errno.ENOENT:
                raise
            print("run '{0} develop' first".format(__file__), file=sys.stderr)
            sys.exit(1)


setup(name='x84',
      version='2.0.7',
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
          'blessed==1.9.5',
          'requests==2.5.1',
          'irc==11.0.1',
          'sqlitedict==1.1.0',
          'python-dateutil==2.3',
          'jaraco.timing==1.1',
          'jaraco.util==10.6',
          'more-itertools==2.2',
          'sauce==1.1',
          'six==1.8.0',
          'wsgiref==0.1.2',
          'xmodem==0.3.2',
          'feedparser==5.1.3',
          'html2text==2014.12.29',
      ],
      extras_require={
          'with_crypto': (
              # These cryptogaphy requirements may only be installed:
              # - if a C compiler is available,
              # - if libssl is available,
              # - (sometimes, only) if libffi is available
              #
              # for this reason, they are **optional**, so that x/84 may be
              # installed without a compiler or these external C libraries
              # -- however it is **highly** recommended to always try to
              # use install x84[with_crypto].  It has always been a goal for
              # x/84 to be "pure python" to remain compatible with alternative
              # python interpreter implementations.
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
      cmdclass={
          'develop': Develop,
          'docs': BuildDocs,
      },
      zip_safe=False,
)
