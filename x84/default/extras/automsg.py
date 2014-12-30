""" Automsg script for x/84 bbs, https://github.com/jquast/x84

 Classic /X style script that enables the user to leave a message/statement
 for the next users logging in.

 Installation instructions:
 ---------------------

 Copy the automsg.ans file from the extras/art folder to your art folder and
 automsg.py to your script folder. Start automsg.py from your top script.
 The script will generate an automsg.txt file in your data folder.
"""

from x84.bbs import getsession, getterminal, echo, LineEditor, showart
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
    echo(term.move(21, 0))
    echo(term.white(msg))
    echo(term.green(u'(') + term.cyan(u'yes/no') + term.green(u')'))


def banner():
    session, term = getsession(), getterminal()
    art_file = os.path.join(os.path.dirname(__file__), 'art', 'automsg.ans')
    echo(term.clear)
    for line in showart(art_file, 'topaz'):
        echo(line)

    if not os.path.exists(get_datafile_path()):
        with codecs.open(get_datafile_path(), 'w', 'utf-8') as fo:
            fo.write('big brother\n')
            fo.write('behave yourselves.\n')
            fo.write('\n\n')

    echo(term.move(12, 10) + term.blue(u'Public message from:'))

    with codecs.open(get_datafile_path(), 'r', 'utf-8') as fo:
        handle = fo.readline().strip()
        echo(term.move(12, 31) + term.bold_white(handle))
        for row in range(1, 4):
            echo(term.move(15 + row, 5) + term.white(fo.readline().strip()))

    ask(u'do you want to write a new public message? ')


def main():
    term = getterminal()
    session = getsession()
    banner()

    while True:
        session.activity = 'Viewing automsg'
        inp = term.inkey()
        if inp.lower() in (u'n', 'q') or inp.code == term.KEY_ENTER:
            return

        if inp.lower() == u'y':
            session.activity = 'Writing automsg'
            echo(term.move(12, 31))
            echo(term.bold_white(session.user.handle))
            echo((u' ' * 7))

            echo(term.move(21, 0) + term.clear_eol)
            for row in range(1, 4):
                echo(term.move(15 + row, 5))
                echo(u' ' * 57)

            msg = []
            for row in range(1, 4):
                echo(term.move(15 + row, 5))
                le = LineEditor(70)
                le.colors['highlight'] = term.white
                msg.append(le.read())

            ask(u'submit your text as a public message? ')

            while 1:
                inp = term.inkey()
                if inp.lower() == u'n':
                    return
                if inp == 'y' or inp == 'Y':
                    echo(term.move(21, 0) + term.clear_eol)
                    with codecs.open(get_datafile_path(), 'w', 'utf-8') as fo:
                        fo.write('\n'.join([session.user.handle] + msg))
                        fo.close()
                    return
