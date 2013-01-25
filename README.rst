x/84
====

x/84 is a python-languaged telnet daemon for modern utf8 terminals. Based on miniboa_, blessings_, sqlitedict_, and multiprocessing_. recordings of sessions are stored in ttyplay_-compatible format files.

**ANSI Art**, (such as you would find on the ACiD "dark domains" DVD) is translated for reasonably accurate reproductions on utf8 and cp437 terminals. Plenty of example ansi art is provided in the default 'bbs board', as well as scripts for bbs-scene_.org's 'one liners' and 'bbs list' APIs.

Installation
============

1. Install pip_

2. Install x84 from git using pip

``pip install git+https://github.com/jquast/x84.git``
or, without ssl,
``pip install git+http://github.com/jquast/x84.git``


Getting Started
===============

1. Execute 'x84',

``x84``

Optional command line arguments,
``--config=`` alternate bbs configuration filepath
``--logger=`` alternate logging configuration filepath

Developers
==========

Use ./bin/x84-dev-setup.py [install path] to create a target virtualenv, installing an 'x84' program in that environment that uses the source tree in the current folder.

Connecting
==========

``telnet localhost 6023``

``python local.py``


Compatible Clients
==================

Any UTF-8 client is compatible, but some fonts do art better than others. For mac systems, 'Andale Mono' works flawlessly. Other than utf8, only cp437 (IBM-US PC-DOS) is supported.

* iTerm: Menu item iTerm -> Preferences, section Profiles, select 'Text' tab, chose 'Andale Mono' font.
* PuTTy: Under preference item Window -> Translation, option 'Remote character set', change 'iso8859-1' to 'UTF-8'.
* Terminal.app: Menu item Terminal -> Preferences, chose profile 'Pro', (Font Andale Mono), enable 'use bright colors for bold text'.
* uxterm: XXX todo.. bright blink?
* SyncTerm, mtel: Select cp437 when prompted by the bbs system (charset.py).
* others: Select cp437 when prompted by the bbs system (charset.py).  Use a font of cp437 encoding, such as *Terminus*.

Customizing your board
======================

The ``default.ini`` option, *scriptpath*, of section *system*, defines folder ``'default/'``. This can be changed to a folder of your own chosing.

By default, matrix.py_ is called on-connect, which chains to nua.py_ for new account creation, top.py_ when authenticated, and main.py_ for a main menu.

Copy this to a new folder, change the .ini file to point to the new folder, and you can begin customizing your matrix, topscripts, and art files.

matrix.py
---------

The ``default.ini`` option, *script*, of section *matrix*, defines the path of a python program that is loaded when a telnet connection is complete. The purpose of this script is to otherwise approve connection for continuation to *topscript*, and is generally used for authentication.

When the ``default.ini`` option, *enable_anonymous*, of section *matrix* is ``True`` (default is ``False``), users may login with name 'anonymous', and top.py_ is called with a handle value of ``None``, and the user is presumed 'anonymous'

nua.py
------

The ``default.ini`` option, *allow_apply*, of section *nua* is ``True`` by default, and users may create a new account by executing the *nua* script. The default nua.py_ script allows all new accounts without approval, and adds the first new user to the ``u'sysop'`` group.

top.py
------

After passing new account creation in nua.py_, or authentication in matrix.py_, the *topscript*, of section *matrix* is called. This script generally checks for new messages, sets character encoding and preferences.

charset.py
----------

Generally called from top.py_, provides an interface for the user to select a session encoding of ``u'utf8'`` or ``u'cp437'``.

lc.py
-----

A simple pager displaying artwork and a scrolling window of the most recent BBS callers.

logoff.py
---------

A simple logoff script that allows users to leave a message for the next user.


main.py
-------

Displays artwork and provides a hotkey interface to ``gosub()`` various scripts.

news.py
-------
Displays artwork and a scrolling window of a ``data/news.txt``.

ol.py
-----
A oneliners script. To configure intra-BBS one-liners for use with bbs-scene_.org's API, create a new section, *bbs-scene* in ``defaults.ini``, with two options, *user* and *pass*.

si.py
-----
Displays information about the BBS system ...

speedhack.py
------------
An example door games menu interface.

bbslist.py
----------
Users post and vote and leave comments for other bbs systems. Also allows this system to be used as a gateway to other systems, using telnet.py_.

weather.py
----------

An example of using the various user interface elements to display the local weather report.


Monitoring
==========

Sessions are recorded to ``ttyrecordings/`` folder, and can be played with
ttyplay_ or compatible utility. The ``-p`` option can be used to monitor
live sessions, analogous to ``tail -f``.


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

A development-based bbs board is planned.

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
