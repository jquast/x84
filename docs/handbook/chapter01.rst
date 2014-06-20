=============================================
Chapter 1: Introduction to x/84 telnet system
=============================================


Before you get started
======================

The x/84 telnet system is written in the Python_ programming language. With
prior programming experience you should be able to pick up the language quicky
by looking at the provided sample mods in the ``x84/default`` folder. If you
are completely new to Python_, it's recommended to read more about the
language, like provided by the free `Dive Into Python`_ book by Mark Pilgrim.

.. _Python: http://www.python.org/
.. _Dive Into Python: http://www.diveintopython.net/


History
=======

Starting in 2007, Johannes "jojo" Lundberg started hacking on the Progressive
BBS (prsv) system in Python. Not long after, Jeff "dingo" Quast joined
development of the board, which was meant to be a more general purpose telnet
framework to build **BBS** and **MUD** style systems.

Somewhere $YEAR, dingo forked the prsv code base to the x/84 telnet system
project, and development took off from there.


Current days
============

The x/84 went through a lot of iterations and is now using async I/O
communications based on the miniboa_ (Apache 2.0 licensed) framework offering
full telnet support. The blessed_ library (based on blessings_) is used for
terminal capabilities and sqlitedict_ (Public Domain) is used to store
persistent data. Recording of sessions are stored in ttyplay_-compatible
format.

Asynchronous inter-process communication between sessions is provided through
an event queuing framework, for scripting of ‘shared’ experiences. Several
examples of these are provided, such as chat.py. The default board provides
several activities.

A POSIX compatible operating system is required. Alternative implementations of
Python may work. Portability is as equal to Python, and has been tested on
Raspberry Pi, Android, Mac, OpenBSD, Solaris, etc.

.. _miniboa: https://code.google.com/p/miniboa/
.. _blessed: https://github.com/jquast/blessed/
.. _blessings: http://pypi.python.org/pypi/blessings/
.. _sqlitedict: http://pypi.python.org/pypi/sqlitedict/
.. _ttyplay: http://0xcc.net/ttyrec/index.html.en
