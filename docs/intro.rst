.. image:: https://landscape.io/github/jquast/x84/master/landscape.svg
    :target: https://landscape.io/github/jquast/x84/master
    :alt: Code Health

.. image:: https://img.shields.io/pypi/v/x84.svg
    :alt: Latest Version
    :target: https://pypi.python.org/pypi/x84

.. image:: https://pypip.in/license/x84/badge.svg
    :alt: License
    :target: http://opensource.org/licenses/MIT

.. image:: https://img.shields.io/pypi/dm/x84.svg
    :alt: Downloads

Introduction
============

**An experimental python Telnet and SSH server framework**

The primary purpose of x/84 is to provide a server framework for building
environments that emulate the feeling of an era that predates the world wide web.
It may be used for developing a classic bulletin board system (BBS) -- one is
provided as the 'default' scripting layer.  It may also be used to develop a MUD,
a text-based game, or a game-hosting server such as done by dgamelaunch.

You may access the "default board" provided by x/84 at telnet host 1984.ws::

    telnet 1984.ws

    # or
    ssh anonymous@1984.ws

    # or
    rlogin 1984.ws


Technologies
------------

x/84 supplies a scripting_ engine for developing character-at a time telnet
or ssh server, such as **MUD** or **BBS** systems.  Technologies used in x/84
are derived from miniboa_ (Apache 2.0 Licensed) for telnet, blessed_
(MIT Licensed) for terminal capabilities, sqlitedict_ (Public Domain) for
persistent data, paramiko_ for ssh and sftp services, and web.py_ for http
service.

Asynchronous inter-process communication between sessions is provided through
an event queuing framework, for scripting of 'shared' experiences. Several
examples of these are provided, such as *chat.py*. The default board
provides several demonstrating activities.

All terminal types supported by curses (the termlib and terminfo) databases are
allowed, with a "pythonic" terminal framework supplied through blessed_.

Portability is as equal to python, and has been tested on Raspberry Pi, Android,
Mac, OpenBSD, Solaris, etc.

**ANSI Art**, such as found on ACiD_ *dark domains* DVD, is translated for
reasonably accurate reproductions for both UTF-8 and IBM CP437 terminals. This
allows classic DOS art to be used on modern terminals such as Terminal.app, or
classic emulating terminals such as syncterm_. Artwork with Sauce_ records are
also supported.

See clients_ for a list of compatible clients.


Quickstart
----------

Note that only Linux, BSD, or OSX is supported, due to the blessed_ dependency on curses.

1. Install python_ 2.7 and pip_. More than likely this is possible through your
   preferred distribution packaging system.

3. Install x/84::

     pip install x84[with_crypto]

   Or, if C compiler and libssl, etc. is not available, simply::
   
     pip install x84

   Please note however that without the ``[with_crypto]`` option, you
   will not be able to run any of the web, ssh, and sftp servers, and
   password hashing (and verification) will be significantly slower.


4. Launch the *x84.engine* python module::

     x84

5. Telnet to 127.0.0.1 6023, Assuming a *bsd telnet* client::

     telnet localhost 6023

All data files are written to ``~/.x84/``.  To create a custom board,
you might copy the ``default`` folder of the *x/84* python module to a
local path, and point the ``scriptpath`` variable of ``~/.x84/default.ini``
to point to that folder.

Simply edit and save changes, and re-login to see them.  Adjust the
``show_traceback`` variable to display any errors directly to your
telnet or ssh client.


Documentation, Support, Issue Tracking
--------------------------------------

See Documentation_ for API and general tutorials, especially the developers_
section for preparing a developer's environment if you wish to contribute
upstream.  Of note, the *Terminal* interface is used for keyboard input
and screen output, and is very well-documented in blessed_.

This project isn't terribly serious (for example, there are no tests), though
contributions (especially fixes and documentation) are welcome.  See the
project on github_ for source tree and issue tracking.  If there are features,
bugs, or changes you would like to see, feel free to open an issue.

If you would like to chat with developers of x/84, we are in channel *#1984*
on *irc.efnet.org*.

.. _miniboa: https://code.google.com/p/miniboa/
.. _sqlitedict: http://pypi.python.org/pypi/sqlitedict
.. _blessed: http://pypi.python.org/pypi/blessed
.. _ttyplay: http://0xcc.net/ttyrec/index.html.en
.. _ACiD: https://en.wikipedia.org/wiki/ACiD_Productions
.. _Sauce: https://github.com/tehmaze/sauce
.. _syncterm: http://syncterm.bbsdev.net/
.. _python: https://www.python.org/
.. _pip: http://guide.python-distribute.org/installation.html#installing-pip
.. _Documentation: http://x84.readthedocs.org/
.. _developers: https://x84.readthedocs.org/en/latest/developers.html
.. _clients: https://x84.readthedocs.org/en/latest/clients.html
.. _scripting: https://x84.readthedocs.org/en/latest/bbs_api.html
.. _github: https://github.com/jquast/x84
.. _web.py: http://webpy.org/
.. _paramiko: http://www.lag.net/paramiko/
