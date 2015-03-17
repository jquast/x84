======================
Customizing your board
======================

The ``default.ini`` file option, *scriptpath*, of section *[system]*, defines folder ``'default/'``, containing the scripts documented in this section. *scriptpath* accepts a comma delimited list of directories in which to store your customizations. Noting that the left most entry is of the highest preference. 

For example.

    scriptpath = /opt/bbs/scripts,/usr/local/src/x84/x84/default

x84 searches for scripts in ``/opt/bbs/scripts`` first and then ``/usr/local/src/x84/x84/default``. This allows you to keep any customizations outside of the main source tree and then fall back to x84 defaults if they're not present in your customizations directory.

Additional scripts can be found at https://github.com/x84-extras

This folder may be changed to a folder of your own choosing, and populated with your own scripts. A good start would be to copy the default/ folder, or even perform a checkout from github.

By default, *matrix.py* is called on-connect, with variations for sftp and ssh as *matrix_sftp.py* and *matrix_ssh.py* set by the ``default.ini`` file option *script* of section *[matrix]*. This script calls out to *nua.py* for new account creation, *top.py* when authenticated, and *main.py* for a main menu.

main(), gosub, and goto
=======================

All scripts to be called by ``goto`` or ``gosub`` must supply a ``main`` function.  Keyword and positional arguments are allowed.

If a script fails due to import or runtime error, the exception is caught, (optionally displayed by ``default.ini`` option ``show_traceback``), and the previous script is re-started.

If a script returns, and was called by ``gosub``, the return value is returned by ``gosub``.

If a script returns, and was called by ``goto``, the session ends and the client is disconnected.

Basic example
=============

Let's start with a bare minimum mod, that just shows a *hello world*-style
welcome to the user::

    def main():
        from x84.bbs import echo, getterminal
        term = getterminal()
        echo(term.bold_red(u'Hello, scene!\r\n'))
        echo(u'Press a key to continue...')
        term.inkey()

So what happens here?

``def main():``
---------------

This is the main entry point for your mod, as called by the previous gosub_ or
goto_ call. If you supply additional arguments to either of the two, they will
be passed as-is to the function invocation. We have no arguments in this
example.

.. _goto: ../api/bbs/index.html#x84.bbs.goto
.. _gosub: ../api/bbs/index.html#x84.bbs.gosub


``from x84.bbs import ...``
---------------------------

x/84 encourages to do runtime imports, so you can change most parts of the
system at runtime, without having the need to restart the whole system. Also,
some of the logic is available to the local thread only, and should not leak
into the global Python scope.

``echo(...)``
-------------

As you may have guessed, the ``echo`` function prints text on the user's
terminal. Notice that we use *unicode* strings here. The BBS engine knows a lot
about the user's terminal capabilities, including its encoding. So offering
everything encoded as unicode, the engine can translate to the correct
encoding for each client.

``term.bold_red(...)``
----------------------

We use blessed_ to display the given text in bold_red using whichever special
terminal attributes are defined by the clients ``TERM`` setting.

``term.inkey()``
----------------

Retrieves a single keystroke from the user's terminal. If the key stroke was a
normal alphanumeric key, you will receive a single character that was typed as
unicode, otherwise you'll get the full multibyte string, such as ``\x1b[A`` for
the up arrow -- a ``code`` attribute is available that can be compared with
complimentary attributes of the ``term`` instance. See blessed_ for details.

.. _blessed: http://pypi.python.org/pypi/blessed
