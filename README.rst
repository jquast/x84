x/84
====

**x/84 is a python telnet server for modern UTF-8 terminals**.

x/84 supplies a scripting engine for developing **MUD** or **BBS** engines, dgamelaunch_-style servers with CLI telnet interfaces, or communications development for packet radio networks.

Technologies used in x/84 are derived from miniboa_ (Apache 2.0 Licensed) for telnet, `blessings`_ (MIT Licensed) for terminal capabilities, and sqlitedict_ (Public Domain) for database. Recordings of sessions are stored in ttyplay_-compatible format files.

Asynchronous inter-process communication between sessions is provided through a simple event queueing framework, allowing simple user scripting of 'shared' experiences between unix processes, using the multiprocessing_ module.

Only python is required, but **requires a posix** operating system. Alternative implementations of python may also work. Blowfish encryption of user account passwords is recommended for low cpu systems, but requires a C/cPython environment to install the dependent module, py-bcrypt. Otherwise, a slow best-effort sha256 hash is implemented by default. x/84 is meant to be highly portable, and has been used on Raspberry Pi, Android, Mac, OpenBSD, etc.

**ANSI Art**, (such as you would find on the ACiD "dark domains" DVD) is translated for reasonably accurate reproductions for both UTF-8 and IBM CP437 terminals. This allows classic DOS art to be used on modern terminals such as Terminal.app, or classic emulating terminals such as SyncTerm. Sauce records are also transcribed.

Telnet to address **1984.ws** to preview the default board.

Install
=======

**X/84 has not yet been released to pypi**. This process simulates the basic pip installation procedure, ('pip install x84') using the github repository as a source. Pre-requisite modules must be installed manually.

1. Install python_ 2.6 or 2.7

2. Install pip_

3. Ensure pip is up-to-date,

``pip install --upgrade pip``

4. Install python dependencies (xmodem, requests, sqllite, etc.)

``pip install `wget -O /dev/stdout 'https://raw.github.com/jquast/x84/master/requirements.txt'|xargs echo```

5. **Optionally**, Install bcrypt (requires gcc, python-dev):

``pip install py-bcrypt``

6. Install x/84

``pip install git+https://github.com/jquast/x84.git``

If 'https' is not a supported scheme, try git+**http**:// instead.

7. Upgrading

``pip install --upgrade git+https://github.com/jquast/x84.git``


Getting Started
===============

1. Launch the x84.engine python module:

``x84``

2. Telnet to 127.0.0.1 6023:

``telnet localhost 6023``

**TODO**: supply local.py script for a simple pure-python telnet client.

Customizing your board
======================

See default_README.rst_ for documentation of the distributed default telnet bbs.

x84 Usage
=========
'x84' is a wrapper for,

``python -m x84.engine``

Which takes optional command line arguments,

``--config=`` alternate bbs configuration filepath
``--logger=`` alternate logging configuration filepath

Compatible Clients
==================

Any UTF-8 client is compatible. For Apple systems, 'Andale Mono' works flawlessly. Other utf-8 terminals:

* PuTTy: Under preference item Window -> Translation, option 'Remote character set', change 'iso8859-1' to 'UTF-8'.
* iTerm: Menu item iTerm -> Preferences, section Profiles, select 'Text' tab, chose 'Andale Mono' font.
* Terminal.app: Menu item Terminal -> Preferences, chose profile 'Pro', (Font Andale Mono), enable 'use bright colors for bold text'.
* uxterm or other utf-8 rxvt and xterm variants. classic rxvt, xterm, dtterm.

Other than UTF-8, only IBM CP437 encoding is supported. Any 8-bit telnet client with CP437 font is supported.

Examples of these include PuTTy, SyncTerm, mtel, linux/bsd cons+bsd telnet. Some non-DOS terminal emulators may require installing a fontset, such as *Terminus* to provide CP437 art.

Binding to port 23
==================

X/84 does not require privileged access, and its basic configuration binds to port 6023. Multi-user systems do not typically allow non-root users to bind to port 23. Alternatively, you can always use port forwarding on a NAT firewall.

**Linux** using privbind_, run the BBS as user 'bbs', group 'adm'::

``sudo privbind -u bbs -g adm x84``

**Solaris** 10, grant net_privaddr privilege to user 'bbs'::

``usermod -K defaultpriv=basic,net_privaddr bbs``

**BSD**, redirection using pf(4)::

``pass in on egress inet from any to any port telnet rdr-to 192.168.1.11 port 6023``

**Other**, Usingirect socat_, listen on 192.168.1.11 and for each connection, fork as 'nobody', and pipe the connection to 127.0.0.1 port 6023. This has the disadvantage that x84 is unable to identify the originating IP.

``sudo socat -d -d -lmlocal2 TCP4-LISTEN:23,bind=192.168.1.11,su=nobody,fork,reuseaddr TCP4:127.0.0.1:6023``

Developer Environment
=====================

For developing from git, simply clone and execute the ./x84/bin/dev-setup python script with the target interpreter (2.6, 2.7) and specify a 'virtual env' folder. Simply source the 'virtual env'/bin/activate file so that subsequent pip commands affect only that specific environment. Target environment for x/84 is currently python 2.7.

1. Clone the github repository,

``git clone 'https://github.com/jquast/x84.git'``

2. Use dev-setup.py_ to create a target virtualenv_:

``python2.7 ./x84/bin/dev-setup.py ./x84-ENV26``

3. Launch x/84 using virtualenv:

``./x84/bin/x84-dev``

Other BBS Software
==================

* enthral_: C++ open source, still in slow development
* synchronet_: C formerly commercial, now open source. Sortof like wildcat.
* daydream_: C open source. 10+ years out of maitenance.
* mystic_: Pascal, closed source. Sortof like Renegade.

  Many more archiac systems you can't acquire or run any longer:
  
* https://en.wikipedia.org/wiki/List_of_BBS_software

Support
=======

An irc channel, '#prsv' on efnet, is available for development discussion.

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
.. _Terminus:
.. _virtualenv:
.. _dev-setup.py:
.. _socat: http://www.dest-unreach.org/socat/
.. _default_README.rst: https://github.com/jquast/x84/blob/master/x84/default/README.rst
