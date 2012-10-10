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
        echo (''.join((term.normal, term.normal_cursor, term.clear, '\rn')))
        showfile ('art/main_alt.asc')
        echo ('\r\n\r\n > ')
    def sorry():
        echo ('\r\n\r\n  ' + term.bright_red + 'Sorry')
        getch (1)
        refresh ()
    def pak():
        echo ('\r\n\r\n  ' + term.normal + 'Press any key...')
        getch ()
        refresh ()

    refresh ()

    while True:
        choice = getch()
        # jojo taught me this
        #if getsession().getuser().handle == 'dingo' and not 'sysop' in \
        #getsession().getuser().groups:
        #  getsession().getuser().groups.append ('sysop')
        if str(choice) == '*':
            goto ('main')
        #elif str(choice) == '/':
        #  m = Msg(handle())
        #  m.recipient = handle()
        #  m.subject = 'test!'
        #  m.body = 'test'
        #  m.tags = ['test']
        #  m.send ()
        elif str(choice).lower () == 'c':
            gosub ('wfc')
            #, getsession().getuser().handle)
            refresh ()
        elif str(choice).lower() == 'f':
            gosub ('xfer')
            refresh ()
            pak ()
            sorry ()
        elif str(choice).lower() == 'n':
            gosub ('chkmsgs')
            pak ()
        elif str(choice).lower() == 'w':
            gosub ('weather')
            refresh ()
        elif str(choice).lower() == 'r':
            gosub ('msgreader', listprivatemsgs(handle()) + listpublicmsgs())
            refresh ()
        elif str(choice) == 'b':
            gosub ('bbslist')
            refresh ()
        elif str(choice) == 'k':
            gosub ('userlist')
            refresh ()
        elif str(choice) == 'l':
            gosub ('lc')
            refresh ()
        elif str(choice) == 'o':
            gosub ('ol')
            refresh ()
        elif str(choice) == 'i':
            gosub ('irc')
            refresh ()
        elif str(choice) == 'e':
            gosub ('viewlog')
            refresh()
        elif str(choice) == 'E':
            gosub ('test.editor')
        elif str(choice) == 'x':
            gosub ('wfc')
            refresh ()
        elif str(choice) == 'u':
            gosub ('ueditor')
            #, getsession().handle)
            refresh ()
        elif str(choice) == 's':
            gosub ('si')
            refresh ()
        elif str(choice) == 't':
            gosub ('games/tetris')
            refresh ()
        elif str(choice) == 'm':
            gosub('games/mastermind')
            refresh()
        elif str(choice) == 'z':
            gosub('news')
            refresh()
        elif str(choice).lower() == 'v':
            gosub ('imgviewer')
            refresh ()
        elif str(choice).lower() == 'g':
            gosub ('logoff')
            refresh ()
        elif str(choice) == '*':
            goto ('main')
        else:
            echo ('\a') # bel
