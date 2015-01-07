API Documentation
=================

.. toctree::
   :maxdepth: 3

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

Please see the general documentation for blessed at
https://pypi.python.org/pypi/blessed

.. autofunction:: x84.bbs.getterminal
.. autofunction:: x84.bbs.showart
.. autofunction:: x84.bbs.encode_pipe
.. autofunction:: x84.bbs.decode_pipe
.. autofunction:: x84.bbs.syncterm_setfont
.. autoclass: blessed.Terminal

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

Configuration
`````````````

.. autofunction:: x84.bbs.get_ini

File Transfers
``````````````

.. autofunction:: x84.bbs.send_modem
.. autofunction:: x84.bbs.recv_modem

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
