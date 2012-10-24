"""
 Main menu script for x/84, http://github.com/jquast/x84
"""

from bbs import *

def main():
    term = getterminal()
    def refresh():
        " refresh main menu screen "
        getsession().activity = 'Main Menu'
        echo (u''.join((term.normal, term.normal_cursor, term.clear, '\r\n')))
        echo (showcp437 ('default/art/main.asc'))
        echo (u'\r\n\r\n > ')
    def sorry():
        echo (u'\r\n\r\n  ' + term.bright_red + u'Sorry')
        getch (1)
        refresh ()
    def pak():
        echo ('\r\n\r\n  ' + term.normal + u'Press any key...')
        getch ()
        refresh ()

    refresh ()

    while True:
        choice = getch()
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
        elif choice == u's':
            gosub ('si')
            refresh ()
        elif choice == u'z':
            gosub('news')
            refresh()
