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


Description of sesame configuration options:

- ``{name}``:  The 'basename' name of the door file, with the value of executable
  and arguments used.  It is only included in the main menu of the command exists,
  and may be disabled by using value of ``no``. The command path may access
  information from the bbs session instance, such as ``{session['handle']}``, or
  system-wide configuration such as ``{system['datapath']}``.  The special format
  argument ``{node}`` is also supplied.  If it exists, a unique per-door and
  per-session node is acquired through the bbs global lock system.

- ``{name}_env_{ENVKEY}``: Override any environment variables by ``{ENVKEY}`` and value.

- ``{name}_key``: Command key in the main menu used to launch this door.

- ``{name}_text``: Text displayed for main menu option.

- ``{name}_droptype``: Any of DOORSYS, DOOR32, CALLINFOBBS, or DORINFO. This value
  is only honored if the command path is targets a binary named ``dosemu``.
  The default value is DOORSYS if unspecified.

- ``{name}_droppath``: The linux-local folder where the dropfile is saved.  The
  dropfile will only be saved when this parameter is set..

- ``{name}_nodes``: The number of nodes this door supports.

- ``{name}_cols`` and ``{name}_rows``: Suggest the user to resize their terminal
  to this window size.

- ``{name}_cp437`` (bool): whether or not to decode the program's output as cp437.  

- ``{name}_sysop_only`` (bool): whether this door is limited to only sysops.


Dosemu
======

Doors using dosemu_ are very popular (note: only works on linux).
We can configure a popular game of LORD as follows.  For file
``/etc/dosemu.conf``, we use configuration options::

    $_cpu = "80486"
    $_cpu_emu = "vm86"
    $_external_char_set = "utf8"
    $_internal_char_set = "cp437"
    $_term_updfreq = (8)
    $_layout = "us"
    $_rawkeyboard = (0)

Of note, we use the *vm86* cpu emulator to allow real-mode emulation
on virtual machines, and we use utf8 for the external character and
cp437 for the internal character set, to allow dosemu to perform the
codepage translations on our behalf.

We create an ``X:`` drive folder at ``/DOS/X`` containing an installation
of LORD at ``X:\LORD``, configured for **DORINFO** dropfiles (by running
**LORDCFG.EXE**), and add the program bnu_ to "drive C"
``/DOS/.dosemu/drive_c`` with autoexec.bat contents::

    @echo off
    path d:\bin;d:\gnu;d:\dosemu
    set TEMP=c:\tmp
    prompt $P$G
    C:\BNU\BNU.COM /L0:57600,8N1 /F
    lredir.com x: linux\fs\DOS\X
    unix -e

The ``unix -e`` option allows passing subsequent commands by command line
parameter, which is what we'll use to offer any number of doors with the
same autoexec.bat file.  We also make sure to modify lord's ``START.BAT``
to ensure the folder is changed to ``X:\LORD`` before starting.

Finally, we add lord to the sesame configuration::

    [sesame]
    lord = /usr/bin/dosemu -quiet -f /etc/dosemu/dosemu.conf -I '$_com1 = "virtual"' 'X:\LORD\START.BAT {node}'
    lord_env_HOME = /DOS
    lord_key = lord
    lord_text = play lord
    lord_droptype = DORINFO
    lord_droppath = /DOS/X/lord
    lord_nodes = 32
    lord_cols = 80
    lord_rows = 25

Which then allows us to run this game by typing "lord" in the main menu.

Please note, that there is a 4 second pause before any input is accepted,
(so you may not immediately press return at the <MORE> prompt).  This is
to work around a dosemu bug where input becomes garbaged and bit-shifted
if any keyboard input is received during startup.

.. _dosemu: http://www.dosemu.org/
