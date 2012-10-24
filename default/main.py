"""
 Main menu script for x/84, http://github.com/jquast/x84
"""

from bbs import *

def pak():
    term = getterminal()
    echo ('\r\n\r\n  ' + term.normal + u'Press any key...')
    getch ()

def refresh():
    " refresh main menu screen "
    term = getterminal ()
    echo (u''.join((term.normal, term.normal_cursor, term.clear, '\r\n')))
    art = ([Ansi(from_cp437(line)) for line in open('default/art/main.asc')])
    max_len = max([line.__len__() for line in art])
    if max_len <= term.width:
        for line in art:
            echo (line.center(term.width - max_len).rstrip() + '\r\n')
    def disp_entry(char, blurb):
        return (term.bold_blue('(') + term.blue_reverse(char)
                + term.bold_blue + ')' + term.bright_white (' '+blurb))
    echo (term.move(len(art) + 3, max(1, (term.width/2) - 20)))
    echo (disp_entry ('b', 'bbs lister'))
    echo (disp_entry ('l', 'last calls'))
    echo (disp_entry ('o', 'one liners'))
    echo (term.move(len(art) + 4, max(1, (term.width/2) - 20)))
    echo (disp_entry ('z', 'news'))
    echo (disp_entry ('g', 'goodbye'))
    echo (disp_entry ('c', 'charset'))
    echo ('\r\n\r\n')

def main():
    session, term = getsession(), getterminal()

    while True:
        if pollevent('refresh'):
            refresh ()
        choice = getch(1)
        if choice == u'*':
            goto ('main')
        elif choice == u'b':
            gosub ('bbslist')
            refresh ()
        elif choice == u'l':
            gosub ('lc')
            refresh ()
        elif choice == u'o':
            gosub ('ol')
            refresh ()
        elif choice == u'z':
            gosub('news')
            refresh()
        elif choice == u'g':
            goto('logoff')
        elif choice == u'c':
            gosub('charset')
