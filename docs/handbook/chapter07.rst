======================
Chapter 7: custom mods
======================

So before jumping onto this topic directly, make sure you understand the
concepts laid out in the `previous chapter`_. If you are looking for
inspiration, take a look at some of the default mods' internals.

.. _previous chapter: chapter06.html

Hello, scene!
=============

Let's start with a bare minimum mod, that just shows a *hello world*-style
welcome to the user::

    def main():
        from x84.bbs import echo, getch
        echo(u'Hello, scene!\r\n')
        echo(u'Press a key to continue...')
        getch()

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
everything encoded as UTF-8 unicode, the engine can translate to the correct
character set for the client. This greatly simplifies dealing with all sorts of
clients.

``getch()``
-----------

Retrieves a single key stroke from the user's terminal. If the key stroke was a
normal key, you will receive the character that was typed, otherwise you'll get
the keyboard scan code in decimal form
