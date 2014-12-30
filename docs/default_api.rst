.. toctree::
   :maxdepth: 2

Customizing your board
======================

The ``default.ini`` file option, *scriptpath*, of section *[system]*, defines folder ``'default/'``, containing the scripts documented in this section.

This folder may be changed to a folder of your own chosing, and populated with your own scripts. A good start would be to copy the default/ folder, or even perform a checkout from github.

By default, matrix.py_ is called on-connect, with variations for sftp and ssh as matrix_sftp.py and matrix_ssh.py set by the ``default.ini`` file option *script* of section *[matrix]*. This script calls out to nua.py_ for new account creation, top.py_ when authenticated, and main.py_ for a main menu.

main(), gosub, and goto
-----------------------

All scripts to be called by ``goto`` or ``gosub`` must supply a ``main`` function.  Keyword and positional arguments are allowed.

If a script fails due to import or runtime error, the exception is caught, (optionally displayed by ``default.ini`` option ``show_traceback``), and the previous script is re-started.

If a script returns, and was called by ``gosub``, the return value is returned by ``gosub``.

If a script returns, and was called by ``goto``, the session ends and the client is disconnected.

The default 'bbs board'
=======================

matrix.py
---------

The ``default.ini`` option, *script*, of section *matrix*, defines the path of a python program that is loaded when a telnet connection is complete. The purpose of this script is to otherwise approve connection for continuation to *topscript*, and is generally used for authentication.

When the ``default.ini`` option, *enable_anonymous*, of section *matrix* is ``True`` (default is ``False``), users may login with name 'anonymous', and top.py_ is called with a handle value of ``None``, and the user is presumed 'anonymous'

Users may optionally reset their passwords by email, using the pwreset.py_ script.

.. automodule:: x84.default.matrix
   :members:

nua.py
------

The ``default.ini`` option, *allow_apply*, of section *nua* is ``True`` by default, and users may create a new account by executing the *nua* script. The default nua.py_ script allows all new accounts without approval, and adds the first new user to the ``u'sysop'`` group.

.. automodule:: x84.default.nua
   :members:

top.py
------

After passing new account creation in nua.py_, or authentication in matrix.py_, the *topscript*, of section *matrix* is called. This script generally checks for new messages, sets character encoding and preferences.

.. automodule:: x84.default.top
   :members:

logoff.py
---------

A simple logoff script that allows users to leave a message for the next user, also known as 'automsg'.

.. automodule:: x84.default.logoff
   :members:

charset.py
----------

Generally called from top.py_, provides an interface for the user to select a session encoding of ``u'utf8'`` or ``u'cp437'`` while displaying ansi art.

.. automodule:: x84.default.charset
   :members:

lc.py
-----

A simple pager displaying artwork and a scrolling window of the most recent BBS callers. This is also generally an interface for listing all bbs users, and provides edit user gosub routine to profile.py_  for sysop, and ability for users to view each other's .plan files.

.. automodule:: x84.default.lc
   :members:

main.py
-------

Displays artwork and provides a hotkey interface to ``gosub()`` the various scripts offered in this folder.

.. automodule:: x84.default.main
   :members:

news.py
-------
Displays utf-8 text file ``news.txt`` in a scrolling window. The sysop is allowed to edit this by a gosub to editor.py_.

.. automodule:: x84.default.news
   :members:

ol.py
-----
A oneliners script. Allows users to post a persistently stored 'one liner'.

To configure intra-BBS one-liners for use with bbs-scene_.org's API, create a new section, *[bbs-scene]* in ``defaults.ini``, with two options, *user* and *pass*.

.. automodule:: x84.default.ol
   :members:

si.py
-----

Displays System Information, about the BBS system, and its authors.

.. automodule:: x84.default.si
   :members:

weather.py
----------

An example of using the various user interface elements to display the local weather report in an artful fashion.

.. automodule:: x84.default.weather
   :members:

.. _bbs-scene: http://bbs-scene.org/


chat.py
-------

This script demonstrates use of global broadcasts by creating a chat interface over the intra-process event system.

.. automodule:: x84.default.chat
   :members:

debug.py
--------

This script demonstrates the ability for a sysop to run maintenance scripts or to test new code.

.. automodule:: x84.default.debug
   :members:

editor.py
---------

This script combines the Lightbar and ScrollingEditor UI elements to provide a relatively intuitive multi-line editor. See the "?" help command or *editor.txt* option for its features.

Most notable is its UTF-8 compatibility and ANSI pipe encoding and decoding. It also features various vi-like features, and similarly provides a "command" vs "edit" mode, switched using the Escape key.

.. automodule:: x84.default.editor
   :members:

online.py
---------

By using various event subsystems, global "are you there?" pings are sent to all other sessions, and their responses are parsed to provide an iostat-like interface to session activity.

Each time an activity change is discovered, the display is refreshed. This provides a "waiting for callers" screen for sysops or users, with a scroll buffer indicating the previous days activities.

Gosub routines are provided to page other users for chat.py_ and writemsg.py_ to online recipients.

.. automodule:: x84.default.online
   :members:

profile.py
----------

Provide an interface to user-editable fields. Also provides sysop ability to view and edit users.

.. automodule:: x84.default.profile
   :members:

pwreset.py
----------

Provide an interface to e-mail a user a reset key. If that user can correctly verify that key, they may set a new password.

.. automodule:: x84.default.pwreset
   :members:

readmsgs.py
-----------

A message scanning and browsing interface. Analogous to mutt.

.. autoattribute:: x84.default.readmsgs.TIME_FMT
.. automodule:: x84.default.readmsgs
   :members:

telnet.py
---------

A telnet client within the bbs, may be used to gateway to other hosts.

.. automodule:: x84.default.telnet
   :members:

tetris.py
---------

A terminal game of tetris with ANSI art blocks by jojo. High scores are persisted and compared with other players. This script helps demonstrate low intra-process latency, good tcp response, and proper telnet supress go-ahead negotiation.

.. autofunction:: x84.default.tetris.main

writemsg.py
-----------

Provides an interface to popular a Msg record, and gosub the editor.py_ script to construct and send a message to the messagebase.

.. automodule:: x84.default.writemsg
   :members:
