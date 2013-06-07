API Documentation
=================

.. toctree::
   :maxdepth: 2

Listed here are general functions and classes that a script would use to interactive as a bbs board. An example of importing from "Userland" would look be::

  def main():
     from x84.bbs import getsession, getterminal, echo
     session, term = getsession(), getterminal()
     echo((u"Hello, " + session.user.handle).center(term.width))

General functions
`````````````````

.. autofunction:: x84.bbs.goto
.. autofunction:: x84.bbs.gosub
.. autofunction:: x84.bbs.disconnect
.. autofunction:: x84.bbs.getch
.. autofunction:: x84.bbs.echo
.. autofunction:: x84.bbs.timeago

Terminal
````````

.. autofunction:: x84.bbs.getterminal
.. autoclass: x84.blessings.Terminal

Session
```````

.. autofunction:: x84.bbs.getsession
.. autoclass:: x84.bbs.session.Session

userbase
````````

.. automodule:: x84.bbs.userbase
   :members:

messagebase
```````````

.. automodule:: x84.bbs.msgbase
   :members:

Database
````````

.. autoclass:: x84.bbs.DBProxy

Ansi UI Elements
````````````````

Pager
-----

.. autoclass:: x84.bbs.pager.Pager

AnsiWindow
----------

.. autoclass:: x84.bbs.ansiwin.AnsiWindow

LineEditor
----------

.. autoclass:: x84.bbs.LineEditor

ScrollingEditor
---------------

.. autoclass:: x84.bbs.ScrollingEditor

Selector
--------

.. autoclass:: x84.bbs.Selector

Lightbar
--------

.. autoclass:: x84.bbs.Lightbar

Doors
`````

.. automodule:: x84.bbs.door
   :members:

CP437 and ANSI
``````````````

.. autofunction:: x84.bbs.showcp437
.. autofunction:: x84.bbs.from_cp437
.. autofunction:: x84.bbs.ropen
.. autoclass: x84.bbs.Ansi
.. autofunction:: x84.bbs.output.ansiwrap


Keysets, Themes
```````````````

.. autoattribute:: x84.bbs.editor.PC_KEYSET
.. autoattribute:: x84.bbs.pager.VI_KEYSET
.. autoattribute:: x84.bbs.selector.VI_KEYSET
.. autoattribute:: x84.bbs.lightbar.NETHACK_KEYSET
.. autoattribute:: x84.bbs.ansiwin.GLYPHSETS
