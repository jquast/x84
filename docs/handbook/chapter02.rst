======================================
Chapter 2: Setting up your environment
======================================

Follow the instructions in the developers_ section

.. _developers: ../developers.rst

Debian / Ubuntu
---------------

You should install the following packages::

    $ sudo apt-get install git python python-pip python-virtualenv virtualenvwrapper

Arch Linux
----------

You should install the following packages::

    $ sudo pacman -S git python2 python2-pip python2-virtualenv python2-virtualenvwrapper


Contributing using git
----------------------

Once you have installed git_, we can get a copy of the repository by *cloning*
the x/84 software repository::

    $ git clone https://github.com/jquast/x84
    Cloning into 'x84'...

If you intend to contribute patches or new mods to the x/84 telnet system, you
should `fork the repository <https://help.github.com/articles/fork-a-repo>`_
and clone over ssh instead.

Then, once you are satisfied with your changes, and you wish to have them
included in the base distribution, you should
`create a pull request <https://help.github.com/articles/creating-a-pull-request>`_.

.. _git: http://git-scm.org/
