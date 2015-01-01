Developers
==========

The x/84 telnet system is written in the Python_ programming language. With
prior programming experience you should be able to pick up the language quickly
by looking at the provided sample mods in the ``x84/default`` folder. If you
are completely new to Python_, it's recommended to read more about the
language, like provided by the free `Dive Into Python`_ book by Mark Pilgrim.

Requirements
------------

The following is step-by-step instructions for creating a developer environment
for making your own customizations of x/84's engine and api and building your
own ``'scriptpath'`` (defined by ``~/.x84/default.ini``).  You may also simply
install x/84 using pip_.

**Debian / Ubuntu**

You should install the following packages::

    $ sudo apt-get install git python python-pip python-virtualenv virtualenvwrapper

**Arch Linux**

You should install the following packages::

    $ sudo pacman -S git python2 python2-pip python2-virtualenv python2-virtualenvwrapper

Virtualenv
``````````

Optional but recommended, using virtualenv and virtualenvwrapper_ ensures
you can install x/84 and its dependencies without root access and quickly
activate the environment at any time.

1. Install virtualenvwrapper_::

      pip install virtualenvwrapper

2. Load virtualenvwrapper_::

      . `which virtualenvwrapper.sh`

   There are techniques to automatically load virtualenvwrapper
   from your shell profile, or to active a virtualenv when
   you change to a project folder. See `virtualenv tips and tricks`_
   if you're interested.

3. Finally, make a virtualenv (named 'x84') using python version 2.7::

      mkvirtualenv -p `which python2.7` x84

4. Anytime later that you want to load the x/84 environment, use command::

      workon x84

Run setup.py develop
--------------------

::

   ./setup.py develop

Starting x/84
-------------

1. Active your virtualenv if you haven't already::

   workon x84

2. And Launch x/84 server::

   x84

x84 Usage
`````````

Optional command line arguments,

    ``--config=`` alternate bbs configuration filepath

    ``--logger=`` alternate logging configuration filepath

Contributing using git
----------------------

If you intend to contribute patches or new mods to the x/84 telnet system, you
should `fork the repository <https://help.github.com/articles/fork-a-repo>`_
and clone over ssh.

Features should be developed into a branch, pushed to github, and when satisfied
with your changes and you wish to have them included in the base distribution,
you should
`create a pull request <https://help.github.com/articles/creating-a-pull-request>`_.

.. _git: http://git-scm.org/
.. _virtualenvwrapper: https://pypi.python.org/pypi/virtualenvwrapper
.. _`virtualenv tips and tricks`: http://virtualenvwrapper.readthedocs.org/en/latest/tips.html#automatically-run-workon-when-entering-a-directory
.. _pip: http://guide.python-distribute.org/installation.html#installing-pip
.. _Python: http://www.python.org/
.. _Dive Into Python: http://www.diveintopython.net/
