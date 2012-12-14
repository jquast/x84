"""
 Main menu script for x/84, http://github.com/jquast/x84
"""

import os


def has_speedhack():
    return(os.path.exists(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'speedhack.py')))


def refresh():
    from x84.bbs import getterminal, echo, Ansi, from_cp437
    " refresh main menu screen "
    term = getterminal()
    echo(u''.join((term.normal, term.clear, term.normal_cursor)))
    art = ([Ansi(from_cp437(line)) for line in open(os.path.join(
        os.path.dirname(__file__), 'art', 'main.asc'))])
    max_len = max([line.rstrip().__len__() for line in art])
    if max_len <= term.width:
        for line in art:
            echo(line.rstrip().center(term.width).rstrip() + '\r\n')

    def disp_entry(char, blurb):
        return Ansi(term.bold_blue('(') + term.blue_reverse(char)
                    + term.bold_blue + ')' + term.bright_white(blurb) + u' ')
    echo(term.move(len(art) - 10, term.width / 4) or '\r\n')
    echo(disp_entry('b', 'bs lister').ljust(term.width / 5))
    echo(disp_entry('l', 'ast calls').ljust(term.width / 5))
    echo(disp_entry('o', 'ne liners').ljust(term.width / 5))
    echo(term.move(len(art) - 8, term.width / 4) or '\r\n')
    echo(disp_entry('z', 'news').ljust(term.width / 5))
    echo(disp_entry('g', 'oodbye').ljust(term.width / 5))
    echo(disp_entry('c', 'harset').ljust(term.width / 5))
    echo(term.move(len(art) - 6, term.width / 4) or '\r\n')
    echo(disp_entry('p', '.plan').ljust(term.width / 5))
    echo(disp_entry('x', 'ception').ljust(term.width / 5))
    if has_speedhack():
        echo(disp_entry('s', 'peedhack (game)')
             .ljust(term.width / 5))
    echo(u'\r\n\r\n')
    # os.path.abspath(__file__)


def main():
    from x84.bbs import getsession, getterminal, getch, goto, gosub
    session, term = getsession(), getterminal()

    dirty = True
    while True:
        if session.poll_event('refresh'):
            dirty = True
        if dirty:
            dirty = False
            refresh()
        choice = getch(1)
        if choice == u'*':
            goto('main')
        elif choice == u'b':
            gosub('bbslist')
            dirty = True
        elif choice == u'l':
            gosub('lc')
            dirty = True
        elif choice == u'o':
            gosub('ol')
            dirty = True
        elif choice == u'z':
            gosub('news')
            dirty = True
        elif choice == u'g':
            goto('logoff')
        elif choice == u'c':
            gosub('charset')
            dirty = True
        elif choice == u'p':
            gosub('editor', '.plan')
            dirty = True
        elif choice == u'x':
            assert False, ('exception thrown')
        elif choice == u's' and has_speedhack():
            gosub('speedhack')
            dirty = True
        elif choice == u'H':
            from guppy import hpy
            h = hpy()
            print (h.heap() & str).bysize
            dirty = True
