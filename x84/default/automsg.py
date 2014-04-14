""" Automsg script for x/84 bbs, https://github.com/jquast/x84 """
from x84.bbs import getsession, getterminal, echo, LineEditor, showcp437
import os
import codecs
__author__ = 'Hellbeard'
__version__ = 1.0


def get_datafile_path():
    from x84.bbs import ini
    folder = os.path.join(ini.CFG.get('system', 'datapath'))
    return os.path.join(folder, 'automsg.txt')


def ask(msg):
    term = getterminal()
    echo(term.move(18, 0))
    echo(term.magenta(msg))
    echo(term.green(u'(') + term.cyan(u'yes/no') + term.green(u')'))


def banner():
    session, term = getsession(), getterminal()
    art_file = os.path.join(os.path.dirname(__file__), 'art', 'automsg.ans')
    echo(term.clear)
    for line in showcp437(art_file):
        echo(line)

    if not os.path.exists(get_datafile_path()):
        with codecs.open(get_datafile_path(), 'w', 'utf-8') as fo:
            fo.write('big brother\n')
            fo.write('behave yourselves.\n')
            fo.write('\n\n')

    echo(term.move(9, 9) + term.white(u'Public message from:'))

    with codecs.open(get_datafile_path(), 'r', 'utf-8') as fo:
        handle = fo.readline().strip()
        echo(term.move(9, 30) + term.blue_on_green(handle))
        for row in range(1, 4):
            echo(term.move(10 + row, 9) + term.yellow(fo.readline().strip()))

    ask(u'do you want to write a new public message? ')


def main():
    term = getterminal()
    session = getsession()
    session.activity = 'automsg'
    banner()

    while True:
        inp = term.inkey()
        if inp.lower() in (u'n', 'q') or inp.code == term.KEY_ENTER:
            return

        if inp.lower() == u'y':
            echo(term.move(9, 30))
            echo(term.blue_on_green(session.user.handle))
            echo((u' ' * 7))

            echo(term.move(18, 0) + term.clear_eol)
            for row in range (1, 4):
                echo(term.move(10 + row, 9))
                echo(u' ' * 57)

            msg = []
            for row in range (1, 4):
                echo(term.move(10 + row, 9))
                le = LineEditor(56)
                le.colors['highlight'] = term.yellow
                msg.append(le.read())

            ask(u'submit your text as a public message? ')

            while 1:
                inp = term.inkey()
                if inp.lower() == u'n':
                    return
                if inp == 'y' or inp == 'Y':
                    echo(term.move(18, 0) + term.clear_eol)
                    with codecs.open(get_datafile_path(), 'w', 'utf-8') as fo:
                        fo.write('\n'.join([session.user.handle] + msg))
                        fo.close()
                    return
