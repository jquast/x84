==========
Developers
==========

The x/84 telnet system is written in the Python_ programming language. With
prior programming experience you should be able to pick up the language quickly
by looking at the provided sample mods in the ``x84/default`` folder. If you
are completely new to Python_, it's recommended to read more about the
language, maybe browse the free `Dive Into Python`_ book by Mark Pilgrim.

Requirements
============

The following is step-by-step instructions for creating a developer environment
for making your own customizations of x/84's engine and api and building your
own ``'scriptpath'`` (defined by ``~/.x84/default.ini``).  You may also simply
install x/84 using pip_.

**Debian, Ubuntu, Mint**

You should install the following packages::

    $ sudo apt-get install build-essential git libffi-dev libssl-dev python-dev python-setuptools python-pip python-virtualenv virtualenvwrapper

And please make sure you're using an up-to-date version of pip::

    $ sudo pip-2.7 --upgrade pip

**Arch Linux**

You should install the following packages::

    $ sudo pacman -S gcc git libffi python2 python2-pip python2-virtualenv python-virtualenvwrapper python2-pyopenssl

And please make sure you're using an up-to-date version of pip::

    $ sudo pip-2.7 --upgrade pip

Virtualenv
----------

Optional but recommended, using virtualenv and/or virtualenvwrapper_ ensures
you can install x/84 and its dependencies without root access and quickly
activate the environment at any time, but without affecting system libraries
or other python projects.

1. Load virtualenvwrapper_::

      . `which virtualenvwrapper.sh`

   There are techniques to automatically load virtualenvwrapper
   from your shell profile, or to active a virtualenv when
   you change to a project folder. See `virtualenv tips and tricks`_
   if you're interested.

2. Make a virtualenv (named 'x84') using python version 2.7::

      mkvirtualenv -p `which python2.7` x84

Anytime you want to load x/84 environment in a new login shell,
source ``virtualenvwrapper.sh`` (as in step #2) and activate using
command::

      workon x84

Install editable version
------------------------

Instead of installing x84 as a complete package, we use ``pip`` to install
an *editable* version -- this is so that when a modification is done to the
files in our local project directory, they are immediately reflected in the
``x84`` server anytime the virtualenv is activated::

   pip install --editable .[with_crypto]


Starting x/84
-------------

::

      x84


As another user
---------------

When installing x84 as an *editable* version inside a virtualenv, some
care must be taken in regards to using sudo and privbind.  This is the
method used by the default board::

    PYTHON_EGG_CACHE=/tmp/.python-eggs sudo privbind -u nobody -g nogroup `which python` -mx84.engine

The ``\`which python\``` ensures the vitualenv-activated python version
of the current user is used, and instead of running the ``x84`` script
which would be not be found in the system path of target user *nobody*,
we instead load the *x84.engine* module directly.


x84 Usage
---------

Optional command line arguments,

    ``--config=`` alternate bbs configuration filepath

    ``--logger=`` alternate logging configuration filepath

By default these are, in order of preference: ``/etc/x84/default.ini``
and ``/etc/x84/logging.ini``, or ``~/.x84/default.ini`` and
``~/.x84/logging.ini``.


.. _git: http://git-scm.org/
.. _virtualenvwrapper: https://pypi.python.org/pypi/virtualenvwrapper
.. _`virtualenv tips and tricks`: http://virtualenvwrapper.readthedocs.org/en/latest/tips.html#automatically-run-workon-when-entering-a-directory
.. _pip: http://guide.python-distribute.org/installation.html#installing-pip
.. _Python: http://www.python.org/
.. _Dive Into Python: http://www.diveintopython.net/
