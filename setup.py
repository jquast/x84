#! /usr/bin/env python
"""
Distribution file for x/84
"""
from __future__ import print_function
import warnings
import platform
import sys
import os
import subprocess
import errno

from distutils.core import setup
from distutils.sysconfig import get_python_inc
from distutils.unixccompiler import UnixCCompiler

from setuptools.command.develop import develop as _develop
from setuptools import Command


here = os.path.dirname(__file__)
readme = 'README.rst'
doc_url = 'http://x84.rtfd.org'
maybe_requires = [
    # These are installed only if a C compiler is available,
    # otherwise a warning is emitted and they are excluded.
    'bcrypt >= 1.0.1',
    'paramiko >=1.14.0',
    'ecdsa >=0.11',
    'pycrypto >= 2.6.1',
]


def check_virtualenv():
    """
    Used for commands that require a virtualenv -- when VIRTUAL_ENV
    is not set, prints an error and exits 1.
    """
    if not os.getenv('VIRTUAL_ENV'):
        print('You must be in a virtualenv, See developer documentation '
              'at filepath docs/developers.rst or online at {0}'
              .format(doc_url), file=sys.stderr)


class develop(_develop):
    """
    This derived develop command class ensures a virtualenv is used.
    """
    def finalize_options(self):
        check_virtualenv()
        _develop.finalize_options(self)


class build_docs(Command):
    """
    Build documentation using sphinx.
    """
    #: path to source documentation folder.
    DOCS_SRC = os.path.join(here, 'docs')

    #: path to output html documentation folder.
    DOCS_DST = os.path.join(here, 'build', 'docs')

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
        except OSError, err:
            if err.errno != errno.ENOENT:
                raise
            print("You must install 'sphinx' to build documentation.",
                  file=sys.stderr)
            sys.exit(1)


def get_maybe_requires():
    """
    Checks for Python.h, libffi, and a C compiler -- if available, returns
    all of maybe_requires[], which is a list of (optional) python packages
    that require a C compiler environment, otherwise emits the appropriate
    warning and returns an empty list.

    This list extends ``install_requires`` of the call to setup().
    """
    msg_nosupport = ('This installation will not support ssh server '
                     'or fast encryption of passwords using bcrypt.')

    has_python_h = bool(
        'Python.h' in os.listdir(get_python_inc()))

    bin_cc = UnixCCompiler.executables.get('compiler', ['cc'])[0]
    has_cc = False
    try:
        has_cc = bool(0 == subprocess.call(('which', bin_cc),
                                           stdout=open(os.devnull, 'w')))
    except WindowsError:
        pass

    has_libffi = False
    try:
        has_libffi = bool(
            0 == subprocess.call(('pkg-config', '--exists', 'libffi',),
                                 stdout=open(os.devnull, 'w')))
    except OSError, err:
        if err.errno != errno.ENOENT:
            raise
        warnings.warn("pkg-config was not found. {0}".format(msg_nosupport))
    except WindowsError:
        pass

    if not has_python_h:
        suggest_cmd = ''
        if sys.platform.lower() == 'linux':
            dist = platform.linux_distribution()[0]
            if dist in ('debian', 'ubuntu',):
                suggest_cmd = (" Try `apt-get install python2.7-dev'.")
        elif sys.platform.lower() == 'win32':
            suggest_cmd = " Try using linux or osx."
        warnings.warn("header files for Python not found (Python.h). "
                      "{0}{1}".format(msg_nosupport, suggest_cmd))

    elif not has_libffi:
        suggest_cmd = ''
        if sys.platform.lower() == 'darwin':
            suggest_cmd = (" Try `brew install libffi' followed by "
                           "`brew link --force libffi' (requires homebrew)")
        elif sys.platform.lower() == 'linux':
            dist = platform.linux_distribution()[0]
            if dist in ('debian', 'ubuntu',):
                suggest_cmd = (" Try `apt-get install libffi'.")
        elif sys.platform.lower() == 'win32':
            suggest_cmd = " Try using linux or osx."
        warnings.warn("Foreign Function Interface library not found (libffi). "
                      "{0}{1}".format(msg_nosupport, suggest_cmd))

    elif not has_cc:
        suggest_cmd = ''
        if sys.platform.lower() == 'darwin':
            xcode_url = "https://developer.apple.com/xcode/downloads/"
            suggest_cmd = " Install XCode from {0}".format(xcode_url)
        elif sys.platform.lower() == 'linux':
            dist = platform.linux_distribution()[0]
            if dist in ('debian', 'ubuntu',):
                suggest_cmd = (" Try `apt-get install gcc'.")
        elif sys.platform.lower() == 'win32':
            suggest_cmd = " Try using linux or osx."
        warnings.warn("No C compiler found ({0}). {1}{2}"
                      .format(cc, msg_nosupport, suggest_cmd))
    else:
        return maybe_requires

    return []

setup(name='x84',
      version='1.2.0',
      description=("Framework for Telnet and SSH BBS or MUD server "
                   "development with example default bbs board"),
      long_description=open(os.path.join(here, readme)).read(),
      author='Jeff Quast',
      author_email='contact@jeffquast.com',
      url='http://x84.rtfd.org/',
      keywords="telnet ssh terminal server ansi bbs mud curses utf8 cp437",
      license='ISC',
      packages=['x84', 'x84.default', 'x84.default.art', 'x84.bbs'],
      package_data={
          '': [readme],
          'x84.default': ['*.ans', '*.txt', ],
          'x84.default.art': ['*.asc', '*.ans', '*.txt',
                              'weather/*',
                              'bulletins/*/*',
                              ],
      },
      install_requires=[
          'requests >=1.1.0',
          'sauce >=0.1.1',
          'sqlitedict >=1.0.8',
          'blessed >=1.9.1',
          'wcwidth >=0.1.1',
          'python-dateutil >=2.2',
          'irc >=8.9.1',
          'web.py >=0.37',
      ] + get_maybe_requires(),
      scripts=['bin/x84'],
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
      )
