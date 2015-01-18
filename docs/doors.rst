=====
Doors
=====

Of the default board, a "sesame.py"  script is provided (``x84/default/sesame.py``)
along with dynamic addition of doors by the main menu (``x84/default/main.py``)
for any scripts defined by a special notation of the ``default.ini``
configuration file.

A very simple unix door of /bin/bash, which is accessible only for
users that are a member of the 'sysop' group is as follows::

   [sesame]
   bash = /bin/bash
   bash_key = bash
   bash_text = bash shell
   bash_sysop_only = yes
   bash_env_PATH = /bin:/usr/bin:/usr/local/bin


Lord
====

Doors using dosemu_ are very popular, we can configure a game of LORD as follows.

For file /etc/dosemu.conf::

    $_cpu = "80486"
    $_cpu_emu = "vm86"
    $_external_char_set = "utf8"
    $_internal_char_set = "cp437"
    $_term_updfreq = (8)
    $_layout = "us"
    $_rawkeyboard = (0)

We create an 'X' drive at ``/DOS/X`` containing an installation of LORD,
configured for DORINFO-style dropfile, and add the program bnu_ to
"drive C" ``/DOS/.dosemu/drive_c`` with autoexec.bat contents::

    @echo off
    path d:\bin;d:\gnu;d:\dosemu
    set TEMP=c:\tmp
    prompt $P$G
    C:\BNU\BNU.COM /L0:57600,8N1 /F
    lredir.com x: linux\fs\DOS\X
    unix -e

Finally, we add lord to the sesame configuration::

    [sesame]
    lord = /usr/bin/dosemu -quiet -f /etc/dosemu/dosemu.conf -I '$_com1 = "virtual"' 'X:\LORD\START.BAT {node}'
    lord_env_HOME = /DOS
    lord_key = lord
    lord_text = play lord
    lord_dropfile = dorinfo
    lord_droppath = /DOS/X/lord
    lord_nodes = 4
    lord_cols = 80
    lord_rows = 25

The special argument ``%%#`` is used to dynamically allocate a unique "node
number", which is required to emulate legacy bulletin-board systems.

#Sesame is a wrapper for the :class:`x84.bbs.door.Door` class.
#
#It takes care of resizing the users' terminal to the correct dimensions or
#otherwise emulate the correct terminal size.
#
#The suffixes for the configuration keys are as follows:
#
# * `_key`, character that gives access to the door from the BBS menu.
# * `_cols`, the minimal number of terminal columns required by the door.
# * `_rows`, the minimal number of terminal rows required by the door.
# * `_env_*`, additional environment settings required by the door.
#
#The value of the `_env_*` configuration settings are passed to a Python
#string formatting function. The session is available as `session` and
#the configuration items from the `system` configuration section are
#exposed.

.. _dosemu: http://www.dosemu.org/
