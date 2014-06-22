======================================
Chapter 2: Setting up your environment
======================================


Software utilities
==================

First of all, you should get a recent Python_ interpreter installed. At least
version 2.6 is required, although version 2.7 is highly recommended.
Furthermore, the x/84 software repository changes are tracked by git_.


Getting the software
====================


Debian / Ubuntu
---------------

You should install the following packages::

    $ sudo apt-get install git python python-pip


Arch Linux
----------

You should install the following packages::

    $ sudo pacman -S git python2 python2-pip


Getting the source code tree
----------------------------

Once you have installed git_, we can get a copy of the repository by *cloning*
the x/84 software repository::

    $ git clone https://github.com/jquast/x84
    Cloning into 'x84'...
    remote: ...

If you intend to contribute patches or new mods to the x/84 telnet system, you
should `fork the repository <https://help.github.com/articles/fork-a-repo>`_
and clone over ssh in stead. Then, once you are satisfied with your changes,
and you wish to have them included in the base distribution, you should `create
a pull request <https://help.github.com/articles/creating-a-pull-request>`_.


Getting the development dependancies installed
----------------------------------------------

Change into your x/84 BBS source code tree, then use ``pip`` to install all
required dependancies::

    $ cd x84
    x84$ sudo pip install -r requirements.txt


Bonus level: use virtualenv
===========================

If you don't want to pollute your system's Python installation, you can also
use virtualenv_ software suite, to create a local Python environment jail to
hack on without touching any of the privileged system Python directories.

Debian / Ubuntu
---------------

You should install the following packages::

    $ sudo apt-get install python-virtualenv virtualenvwrapper

Arch Linux
----------

You should install the following packages::

    $ sudo pacman -S python2-virtualenv python2-virtualenvwrapper

Setting up your virtual environment
-----------------------------------

You should probably log back in to your system to be able to use virtualenv
after installing it, or re-initialize your shell. After doing so, create a new
virtual environment for x/84::

    $ mkvirtualenv x84
    New python executable in x84/bin/python
    Installing setuptools, pip...done.
    virtualenvwrapper.user_scripts creating /home/bbs/.virtualenvs/x84/bin/predeactivate
    virtualenvwrapper.user_scripts creating /home/bbs/.virtualenvs/x84/bin/postdeactivate
    virtualenvwrapper.user_scripts creating /home/bbs/.virtualenvs/x84/bin/preactivate
    virtualenvwrapper.user_scripts creating /home/bbs/.virtualenvs/x84/bin/postactivate
    virtualenvwrapper.user_scripts creating /home/bbs/.virtualenvs/x84/bin/get_env_details

Now, whenever you want to work on x/84, you can issue::

    $ workon x84
    (x84)$ <install stuff with pip and hack on BBS for great justice>


.. _Python: http://www.python.org/
.. _git: http://git-scm.org/
