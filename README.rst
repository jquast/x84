x/84
====

**A python Telnet server for modern UTF-8 and classic network virtual terminals**.

x/84 supplies a scripting engine for developing **MUD** or **BBS** engines.  Technologies used in x/84 are derived from miniboa_ (Apache 2.0 Licensed) for telnet, blessings_ (MIT Licensed) for terminal capabilities, and sqlitedict_ (Public Domain) for persistent data. Recordings of sessions are stored in ttyplay_-compatible format files.

Asynchronous inter-process communication between sessions is provided through an event queuing framework, for scripting of 'shared' experiences. Several examples of these are provided, such as *chat.py*. The default board provides several activities.

A Posix operating system is required. Alternative implementations of python may work. Blowfish encryption of user account passwords is recommended, but requires a C compiler to install the dependent module, *py-bcrypt*. Otherwise, a best-effort sha256 hash is implemented by default.

Portability is as equal to python, and has been tested on Raspberry Pi, Android, Mac, OpenBSD, Solaris, etc.

**ANSI Art**, such as found on ACiD_ *dark domains* DVD, is translated for reasonably accurate reproductions for both UTF-8 and IBM CP437 terminals. This allows classic DOS art to be used on modern terminals such as Terminal.app, or classic emulating terminals such as syncterm_. Artwork with Sauce_ records are also supported.

Telnet to host address 1984.ws_ to preview the default board.

Install
=======

1. Install python_ 2.6 or 2.7

2. Install pip_

3. Ensure pip is up-to-date,

``pip install --upgrade pip``

4. Install x/84

``pip install x84``

5. Upgrading

``pip install --upgrade x84``

Getting Started
===============

1. Launch the *x84.engine* python module:

``x84``

failing that, try more directly:

``python -m x84.engine``

2. Telnet to 127.0.0.1 6023:

Assuming a *bsd telnet* client,

``telnet -L localhost 6023``

(argument ``-L`` indicates utf-8 capabilities with *BINARY* 8-bit input).

*Customizing your board*

See default_README.rst_ for documentation of the distributed default telnet bbs. Files ``~/.x84/default.ini`` and ``~/.x84/logging.ini`` were created on first launch. System-wide files of the same name can be deployed to ``/etc/x84/`` for privilege-separated launch.

x84 Usage
=========
``x84`` is a wrapper for launching ``python -m x84.engine``

Which takes optional command line arguments,

``--config=`` alternate bbs configuration filepath

``--logger=`` alternate logging configuration filepath

Compatible Clients
==================

Any UTF-8 client is compatible. For Apple systems, *Andale Mono* works wonderfully. When using BSD telnet, use command line argument ``-L`` to enable *BINARY* 8-bit mode for utf-8 input.

Other utf-8 terminals:

* PuTTy: Under preference item *Window -> Translation*, option *Remote character set*, change *iso8859-1* to *UTF-8*.
* iTerm: Menu item *iTerm -> Preferences*, section *Profiles*, select tab *Text*, chose *Andale Mono* font.
* Terminal.app: Menu item *Terminal -> Preferences*, chose profile *Pro*, select Font *Andale Mono*, and enable *use bright colors for bold text*.
* uxterm or other utf-8 rxvt and xterm variants: urxvt, dtterm.

Other than UTF-8, only IBM CP437 encoding is supported. Any 8-bit telnet client with CP437 font is supported.

Examples of these include PuTTy, SyncTerm, mtel, netrunner, linux/bsd console + bsd telnet.

Some non-DOS terminal emulators may require installing a fontset, such as *Terminus_* to provide CP437 art.

Binding to port 23
==================

X/84 does not require privileged access, and its basic configuration binds to port 6023. Multi-user systems do not typically allow non-root users to bind to port 23. Alternatively, you can always use port forwarding on a NAT firewall.

**Linux** using privbind_, run the BBS as user 'bbs', group 'adm'.

``sudo privbind -u bbs -g adm x84``

**Solaris** 10, grant net_privaddr privilege to user 'bbs'.

``usermod -K defaultpriv=basic,net_privaddr bbs``

**BSD**, redirection using pf(4).

``pass in on egress inet from any to any port telnet rdr-to 192.168.1.11 port 6023``

**Other**, Usingirect socat_, listen on 192.168.1.11 and for each connection, fork as 'nobody', and pipe the connection to 127.0.0.1 port 6023. This has the disadvantage that x84 is unable to identify the originating IP.

``sudo socat -d -d -lmlocal2 TCP4-LISTEN:23,bind=192.168.1.11,su=nobody,fork,reuseaddr TCP4:127.0.0.1:6023``

Developer Environment
=====================

For developing from git, simply clone and execute the ./x84/bin/dev-setup python script with the target interpreter, specifying a ``virtual env`` folder. Source the ``*virtual env*/bin/activate`` file so that subsequent *pip* commands affect only that specific environment. Target environment for x/84 is currently python 2.7.

1. Clone the github repository,

``git clone 'https://github.com/jquast/x84.git'``

2. Use ``dev-setup.py`` to create a target virtualenv (virtualenv provided):

``python2.7 ./x84/bin/dev-setup.py ./x84-ENV26``

3. Launch x/84 using virtualenv:

``./x84/bin/x84-dev``

Other BBS Software
==================

Listed here is software known in the "bbs-scene" as still being actively used.

* enthral_: C++ open source.
* synchronet_: C formerly commercial, now open source.
* daydream_: C open source.
* mystic_: Pascal, closed source.
* citadel_: Ancient history.

  Many more systems can be found on WikiPedia https://en.wikipedia.org/wiki/List_of_BBS_software

Support
=======

An irc channel, *#prsv* on efnet, is available for development discussion.

.. _1984.ws: telnet://1984.ws
.. _syncterm: http://syncterm.bbsdev.net/
.. _python: https:/www.python.org/
.. _dgamelaunch: http://nethackwiki.com/wiki/Dgamelaunch
.. _miniboa: https://code.google.com/p/miniboa/
.. _blessings: http://pypi.python.org/pypi/blessings
.. _sqlitedict: http://pypi.python.org/pypi/sqlitedict
.. _multiprocessing: http://docs.python.org/library/multiprocessing.html
.. _ttyplay: http://0xcc.net/ttyrec/index.html.en
.. _pip: http://guide.python-distribute.org/installation.html#installing-pip
.. _bbs-scene: http://bbs-scene.org/
.. _dopewars: http://dopewars.sourceforge.net
.. _nethack: http://nethack.org/
.. _enthral: http://enthralbbs.com/
.. _synchronet: http://www.synchro.net/
.. _daydream: da
.. _mystic: http://mysticbbs.com/
.. _Python: http://www.python.org/
.. _ACiD: https://en.wikipedia.org/wiki/ACiD_Productions
.. _Terminus: http://terminus-font.sourceforge.net/
.. _socat: http://www.dest-unreach.org/socat/
.. _default_README.rst: https://github.com/jquast/x84/blob/master/x84/default/README.rst
.._Sauce: https://github.com/tehmaze/sauce
.._citadel: https://en.wikipedia.org/wiki/Citadel_%28software%29
