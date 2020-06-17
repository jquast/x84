Introduction
============

**An experimental python 2 Telnet (and SSH) BBS**

**this project is abandoned**, so please don't get too excited! Maybe you
would be more interested in ENiGMA½_

The primary purpose of x/84 is to provide a server framework for building
environments that emulate the feeling of an era that predates the world wide web.

It may be used for developing a classic bulletin board system (BBS) -- one is
provided as the 'default' scripting layer.  It may also be used to develop a MUD,
a text-based game, or a game-hosting server such as done by dgamelaunch.

You may access the "default board" provided by x/84 at telnet host 1984.ws::

    telnet 1984.ws

See clients_ for a list of compatible clients, though any terminal should be just fine.

Quickstart
----------

Note that only Linux, BSD, or OSX is supported. Windows might even work, but hasn't been tested.

1. Install python_ **2.7** and pip_. More than likely this is possible through your
   preferred distribution packaging system.

3. Install x/84::

     pip install x84[with_crypto]

   Or, if C compiler and libssl, etc. is not available, simply::
   
     pip install x84

   Please note however that without the ``[with_crypto]`` option, you
   will not be able to run any of the web, ssh, and sftp servers, and
   password hashing (and verification) will be significantly slower.

   If you receive an error about ``setuptools_ext`` not being found, you
   may need to upgrade your installed version of setuptools and try again::

     pip install -U setuptools pip


4. Launch the *x84.engine* python module::

     x84

5. Telnet to 127.0.0.1 6023, Assuming a *bsd telnet* client::

     telnet localhost 6023

All data files are written to ``~/.x84/``.  To create a custom board,
you might copy the ``default`` folder of the *x/84* python module to a
local path, and point the ``scriptpath`` variable of ``~/.x84/default.ini``
to point to that folder.

Simply edit and save changes, and re-login to see them.  Adjust the
``show_traceback`` variable to display any errors directly to your
telnet or ssh client.


Documentation, Support, Issue Tracking
--------------------------------------

See Documentation_ for API and general tutorials, especially the developers_
section for preparing a developer's environment if you wish to contribute
upstream.  Of note, the *Terminal* interface is used for keyboard input
and screen output, and is very well-documented in blessed_.

This project isn't terribly serious (for example, there are no tests).  See the project on github_
for source tree. Please note that this project is **abandoned**.  Feel free to do whatever the heck
you want with it, though, it is Open Source and ISC licensed!

.. _miniboa: https://code.google.com/p/miniboa/
.. _sqlitedict: http://pypi.python.org/pypi/sqlitedict
.. _blessed: http://pypi.python.org/pypi/blessed
.. _ttyplay: http://0xcc.net/ttyrec/index.html.en
.. _ACiD: https://en.wikipedia.org/wiki/ACiD_Productions
.. _Sauce: https://github.com/tehmaze/sauce
.. _syncterm: http://syncterm.bbsdev.net/
.. _python: https://www.python.org/
.. _pip: http://guide.python-distribute.org/installation.html#installing-pip
.. _Documentation: http://x84.readthedocs.org/
.. _developers: https://x84.readthedocs.org/en/latest/developers.html
.. _clients: http://x84.readthedocs.org/en/latest/project_details.html#compatible-clients
.. _scripting: https://x84.readthedocs.org/en/latest/api/userland.html
.. _github: https://github.com/jquast/x84
.. _web.py: http://webpy.org/
.. _paramiko: http://www.lag.net/paramiko/
.. _ENiGMA½: https://enigma-bbs.github.io/
