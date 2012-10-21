"""
 Main menu script for X/84, http://1984.ws
 $Id: main.py,v 1.12 2010/01/02 07:35:27 dingo Exp $

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']

def main():
    term = getterminal()
    def refresh():
        " refresh main menu screen "
        getsession().activity = 'Main Menu'
        echo (u''.join((term.normal, term.normal_cursor, term.clear, '\rn')))
        echo (showcp437 ('art/main_alt.asc'))
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
