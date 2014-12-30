Developer Environment
=====================

If you're new to python, the following is step-by-step instructions for
creating a developer environment for making your own customizations of
x/84's engine and api.  You may also simply install x/84 using pip_ or
easy_install_.

Virtualenv
``````````

Optional but recommended. Using virtualenv and virtualenvwrapper_ ensures
you can install x/84 and its dependencies without root access, and quickly
activate the environment at any time.

1. Install virtualenvwrapper_::

      pip install virtualenvwrapper

2. Load virtualenvwrapper_::

      . `which virtualenvwrapper.sh`

3. And add the following to your ``~/.profile`` to make this automatic for all
  login shells::

      [ ! -z `which virtualenvwrapper.sh` ] && . `which virtualenvwrapper.sh`

4. Finally, make a virtualenv (named 'x84') using python version 2.7::

      mkvirtualenv -p `which python2.7` x84

5. Anytime you want to develop x/84, use the command::

      workon x84

There are techniques to automatically load the x84 virtualenv when
you change to the project's folder. See `virtualenv tips and tricks`_
if you're interested.

Clone from Github
`````````````````

Clone the latest master branch from the github repository::

  git clone 'https://github.com/jquast/x84.git'``
  cd x84

Run setup.py develop
````````````````````

Run 'setup.py develop'::

   ./setup.py develop

Starting x/84
`````````````

1. Active your virtualenv if you haven't already::

   workon x84

2. And Launch x/84 server::

   x84

.. _virtualenvwrapper: https://pypi.python.org/pypi/virtualenvwrapper
.. _`virtualenv tips and tricks`: http://virtualenvwrapper.readthedocs.org/en/latest/tips.html#automatically-run-workon-when-entering-a-directory
.. _pip: https://pypi.python.org/pypi/pip
.. _easy_install: https://pypi.python.org/pypi/setuptools
