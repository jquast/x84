Requirements
============

A Posix operating system is required, generally something unix-derived.  Alternative implementations of python may work. 

Windows operating systems may not work because of the dependency on curses and a termcap library for detecting terminal capabilities.  A cygwin-based build may cope fine.

Install instructions
====================

1. Install python_ 2.6 or 2.7

2. Install pip_

3. Ensure pip is up-to-date::

     pip install --upgrade pip

4. Install x/84::

     pip install x84

5. Upgrading::

     pip install --upgrade x84

Getting Started
---------------

1. Launch the *x84.engine* python module::

     x84

   *x84* is a ``/bin/sh`` wrapper for launching *python -m x84.engine*.
   If the ``*x84`` helper script fails, try using the python interpreter
   used with ``pip``, for example::

     /usr/local/bin/python2.7 -m x84.engine


2. Telnet to 127.0.0.1 6023, Assuming a *bsd telnet* client::

     telnet localhost 6023


x84 Usage
---------

Optional command line arguments,

   ``--config=`` alternate bbs configuration filepath

   ``--logger=`` alternate logging configuration filepath

UCS4 Support
------------

If you receive this error::

  warn    engine.py:95  - Python not built with wide unicode support!

And you are concerned with very large unicode points, such as used in Thai or emoticons like hamsterface, 🐹, you will need to upgrade or rebuild your python interpreter so that it is build with *UCS4* support.  Otherwise it may only be displayed, but input characters will often be decoded as '??'.

Blowfish Encryption
-------------------

Blowfish encryption of user account passwords is *recommended*, but requires a C compiler to install the dependent module, *py-bcrypt*, thereby reducing the portability.  This will significantly reduce password encryption time on slower systems.

Otherwise, a best-effort sha256 hash is implemented by default. 

Privacy
-------

Telnet is not a secure protocol.

This implementation of x/84 is without any encryption.  You should be aware that absolutely everything you type and read can be read by any intermiediate network between yourself and the server.

You can always bind the telnet board only to localhost, where clients connect through telnet over ssh, creating a *Private* 'members only' board.  You can also use other ssl layering things, such as stunnel.

Previous versions included ssh support through python twisted conch, and can be found in the earliest github revisions as ssh.py.  The twisted dependency was considered too 'heavyweight' and dropped.

Telnet standards exist for encryption.  If bsd telnet provides some trivial level of encryption, patches to support it are welcomed.

.. _python: https://www.python.org/
.. _pip: http://guide.python-distribute.org/installation.html#installing-pip
