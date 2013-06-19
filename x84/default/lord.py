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

    store_cols, store_rows = None, None
    want_cols, want_rows = 80, 25
    if want_cols != term.width or want_rows != term.height:
        echo(u'\x1b[8;%d;%dt' % (want_rows, want_cols,))
    disp = 1
    while not (term.width == want_cols
            and term.height == want_cols):
        if disp:
            echo(term.bold_blue('\r\n^\r\n'))
            echo(term.bold_blue('\r\n'.join([u'|'] * (want_rows - 3))))
            echo('\r\n')
            echo(term.bold_blue(u'|' + (u'=' * 78) + u'|\r\n'))
            echo(u'for best "screen output", please '
                'resize window to %s x %s (or press return).' % (
                    want_cols, want_rows,))
            disp = 0
        ret = term.inkey(2)
        if ret in (term.KEY_ENTER, u'\r', u'\n'):
            break

    if term.width != want_cols or term.height != want_rows:
        echo('Your dimensions: %s by %s; emulating %s by %s !' % (
            term.width, term.height, want_cols, want_rows,))
        # hand-hack, its ok ... really
        store_cols, store_rows = term.width, term.height
        term.columns, term.rows= want_cols, want_rows
        term.inkey(1)

    session.activity = 'Playing LORD'
    lord_args = lord_args.replace('%#', str(session.node))
    Dropfile(getattr(Dropfile, lord_dropfile)).save(lord_path)
    door = DOSDoor(bin, args=shlex.split(lord_args),
            env_home=home)
    door.run()
    echo(term.clear)
    if not (store_cols is None and store_rows is None):
        echo('Restoring dimensions to %s by %s !' % (store_cols, store_rows))
        term.rows, term.columns = store_rows, store_cols
    echo ('\r\n')
    term.inkey(0.5)
