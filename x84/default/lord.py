import tempfile
import logging
import shutil
import shlex
import time
import os

# example dosemu.conf
#  $_cpu = "80486"
#  $_cpu_emu = "vm86"
#  $_external_char_set = "utf8"
#  $_internal_char_set = "cp437"
#  $_term_updfreq = (8)
#  $_layout = "us"
#  $_rawkeyboard = (0)

# example <dosemu_home>/.dosemu/drive_c/autoexec.bat
#  @echo off
#  path d:\bin;d:\gnu;d:\dosemu
#  set TEMP=c:\tmp
#  prompt $P$G
#  C:\BNU\BNU.COM /L0:57600,8N1 /F
#  lredir.com x: linux\fs\DOS\X
#  unix -e

# notes:
# bnu.com is a fossil driver


# doorfiles configured for DORINFOn.DEF support in LORDCFG.exe

def main():
    from x84.bbs import getsession, getterminal, echo, ini
    from x84.bbs import DOSDoor, Dropfile

    assert ini.CFG.getboolean('dosemu', 'enabled'), (
        'lord.py called but dosemu not enabled in configuration')
    logger = logging.getLogger()
    session, term = getsession(), getterminal()

    # dosemu is a bear; as the BBS typically runs as user 'nobody', the $HOME
    # path is often unset or '/', by exporting an ENV variable 'HOME' to
    # '/DOS', we can manipulate the bbs door dosemu environment with the
    # auto-created /DOS/.dosemu folder.
    dosemu_bin = ini.CFG.get('dosemu', 'bin')
    dosemu_home = ini.CFG.get('dosemu', 'home')
    lord_path = ini.CFG.get('dosemu', 'lord_path')
    lord_dropfile = ini.CFG.get('dosemu', 'lord_dropfile').upper()

    # "lord_args" is the dosemu arguments to execute the lord game. The special
    # sequence '%#' is replaced with the Node Number (ala synchronet).
    lord_args = ini.CFG.get('dosemu', 'lord_args').replace('%#', str(session.node))


    assert lord_path != 'no'
    assert os.path.exists(lord_path)
    assert os.path.exists(dosemu_bin)
    assert os.path.exists(dosemu_home)

    Dropfile(getattr(Dropfile, lord_dropfile)).save(lord_path)
    door = DOSDoor(dosemu_bin, args=shlex.split(lord_args), env_home=dosemu_home)
    door.run()
