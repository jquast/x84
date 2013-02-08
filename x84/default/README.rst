Customizing your board
======================

The ``default.ini`` option, *scriptpath*, of section *system*, defines folder ``'default/'``, containing the scripts found here. This can be changed to a folder of your own chosing.

By default, matrix.py_ is called on-connect, which chains to nua.py_ for new account creation, top.py_ when authenticated, and main.py_ for a main menu.

Copy the contents of the ``'default/'`` folder to a new folder, change the .ini file to point to it, and you can begin customizing your matrix, topscripts, and art files.

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

