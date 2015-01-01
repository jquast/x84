Engine and Internals
====================

x/84 is designed in three distinct parts: The Engine_, Userland_, and
the default 'bbs board'.

Userland
````````

The following are helper modules used by the internal API but are not
published as such. Their use or documentation isn't considered very
useful to a general audience.

ipc.py
------

.. automodule:: x84.bbs.ipc
  :members:

ini.py
------

.. automodule:: x84.bbs.ini
  :members:

exception.py
------------

.. automodule:: x84.bbs.exception
   :members:

Engine
``````

The engine launches the configured servers and begins the subprocess
for connecting sessions. Its internal structure should not be of concern
for most customizations, but contributions welcome!

engine.py
---------

.. automodule:: x84.engine
   :members:

terminal.py
-----------

.. automodule:: x84.terminal
   :members:

Servers
```````
.. automodule:: x84.client
   :members:
.. automodule:: x84.server
   :members:
.. automodule:: x84.telnet
   :members:
.. automodule:: x84.ssh
   :members:
.. automodule:: x84.webserve
   :members:
.. automodule:: x84.sftp
   :members:
.. automodule:: x84.rlogin
   :members:

Database
````````
.. automodule:: x84.db
   :members:

fail2ban
````````
.. automodule:: x84.fail2ban
   :members:
