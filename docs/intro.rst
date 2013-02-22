Introduction to x/84
====================

**A python Telnet server for modern UTF-8 and classic network virtual terminals**.

x/84 supplies a scripting engine for developing **MUD** or **BBS** engines.  Technologies used in x/84 are derived from miniboa_ (Apache 2.0 Licensed) for telnet, blessings_ (MIT Licensed) for terminal capabilities, and sqlitedict_ (Public Domain) for persistent data. Recordings of sessions are stored in ttyplay_-compatible format files.

Asynchronous inter-process communication between sessions is provided through an event queuing framework, for scripting of 'shared' experiences. Several examples of these are provided, such as *chat.py*. The default board provides several activities.

A Posix operating system is required. Alternative implementations of python may work. Blowfish encryption of user account passwords is recommended, but requires a C compiler to install the dependent module, *py-bcrypt*. Otherwise, a best-effort sha256 hash is implemented by default.

Portability is as equal to python, and has been tested on Raspberry Pi, Android, Mac, OpenBSD, Solaris, etc.

**ANSI Art**, such as found on ACiD_ *dark domains* DVD, is translated for reasonably accurate reproductions for both UTF-8 and IBM CP437 terminals. This allows classic DOS art to be used on modern terminals such as Terminal.app, or classic emulating terminals such as syncterm_. Artwork with Sauce_ records are also supported.

Telnet to host address 1984.ws_ to preview the default board.

.. _miniboa: https://code.google.com/p/miniboa/
.. _blessings: http://pypi.python.org/pypi/blessings
.. _sqlitedict: http://pypi.python.org/pypi/sqlitedict
.. _ttyplay: http://0xcc.net/ttyrec/index.html.en
.. _ACiD: https://en.wikipedia.org/wiki/ACiD_Productions
.. _syncterm: http://syncterm.bbsdev.net/
.. _Sauce: https://github.com/tehmaze/sauce
.. _1984.ws: telnet://1984.ws
