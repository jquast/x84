import shlex
import os

# example dosemu.conf
#  $_cpu = "80486"
#  $_cpu_emu = "vm86"
#  $_external_char_set = "utf8"
#  $_internal_char_set = "cp437"
#  $_term_updfreq = (8)
#  $_layout = "us"
#  $_rawkeyboard = (0)

# example <home>/.dosemu/drive_c/autoexec.bat
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
    session, term = getsession(), getterminal()

    # dosemu is a bear; as the BBS typically runs as user 'nobody',
    # the $HOME path is often unset or '/'; by exporting an ENV
    # variable 'HOME' to '/DOS', we can manipulate the bbs door
    # dosemu environment with the /DOS/.dosemu folder, and test with
    # 'sudo su - nobody', then launching 'dosemu'
    bin = ini.CFG.get('dosemu', 'bin')
    home = ini.CFG.get('dosemu', 'home')
    lord_path = ini.CFG.get('dosemu', 'lord_path')
    lord_dropfile = ini.CFG.get('dosemu', 'lord_dropfile').upper()
    lord_args = ini.CFG.get('dosemu', 'lord_args')

    assert lord_path != 'no'
    assert os.path.exists(lord_path)
    assert os.path.exists(bin)
    assert os.path.exists(home)

    store_width, store_height = None, None
    want_width, want_height = 80, 25
    if want_width != term.width or want_height != term.height:
        echo(u'\x1b[8;%d;%dt' % (want_height, want_width,))
    disp = 1
    while not (term.width == want_width
            and term.height == want_width):
        if disp:
            echo('^\r\n')
            echo(term.bold_blue('\r\n'.join([u'|'] * (want_height - 3))))
            echo(term.bold_blue(u'|' + (u'=' * 78) + u'|\r\n'))
            echo(u'\r\nfor best "screen draw" emulating, please '
                'resize your window to %s x %s, (or press return).\r\n' % (
                    want_width, want_height,))
            disp = 0
        ret = term.inkey(2)
        if ret in (term.KEY_ENTER, u'\r', u'\n'):
            break

    if term.width != want_width or term.height != want_height :
        echo('Your dimensions: %s by %s; emulating %s by %s' % (
            term._width, term._height, want_width, want_height,))
        # hand-hack, its ok ... really
        store_width, store_height = term._width, term._height
        term._width, term._height = want_width, want_height

    session.activity = 'Playing LORD'
    lord_args = lord_args.replace('%#', str(session.node))
    Dropfile(getattr(Dropfile, lord_dropfile)).save(lord_path)
    door = DOSDoor(bin, args=shlex.split(lord_args),
            env_home=home)
    door.run()
    if store_width is not None and store_height is not None:
        term._width, term._height = store_width, store_height
