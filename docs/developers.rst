Developer Environment
=====================

For developing from git, simply clone and execute the ./x84/bin/dev-setup python script with the target interpreter, specifying a ``virtual env`` folder. Source the ``*virtual env*/bin/activate`` file so that subsequent *pip* commands affect only that specific environment. Target environment for x/84 is currently python 2.7.

1. Clone the github repository::

     git clone 'https://github.com/jquast/x84.git'``

2. Use ``dev-setup.py`` to create a target virtualenv (virtualenv provided)::

     python2.7 ./x84/bin/dev-setup.py ./x84-ENV26

3. Launch x/84 using virtualenv::

     ./x84/bin/x84-dev

Tracking head branch with pip
`````````````````````````````

It is possible, without directly using git, to install the latest branch directly from github using pip::

  pip install git+https://github.com/jquast/x84.git

And then subsequently upgrade after any commits have been pushed::

  pip install --upgrade git+https://github.com/jquast/x84.git

You may then start x84 normally as you would if installed using pip::

  sudo privbind -u nobody -g adm x84

Engine internals
================

x/84 is configured as a seperate 'kernel' and 'userland' scripting path to be optionally located at two different filepaths.

Kernel
``````

Any changes to engine internals bump release majors. Scripts are encouraged to require as little modification as possible over time to maintain compatibility with major releases.

engine.py
---------

.. automodule:: x84.engine
   :members:

terminal.py
-----------

.. automodule:: x84.terminal
   :members:

telnet.py
---------

.. automodule:: x84.telnet
   :members:

db.py
-----

.. automodule:: x84.db
   :members:


Userland
````````

Procedures not necessarily exposed that are internal to the child process executed by terminal.py_ on connect. Though most of this is accessible by the child process for scripting, their use or documentation isn't considered very useful to a general audience.

wcswidth.py
-----------

.. automodule:: x84.bbs.wcswidth
  :members:

log.py
------

.. automodule:: x84.bbs.log
  :members:

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
