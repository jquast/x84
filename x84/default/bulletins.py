""" Bulletins script for x/84 bbs, https://github.com/jquast/x84 """

# More to be added as soon as we get a filebase going.

from x84.bbs import getsession, getterminal, echo, list_users, get_user
from x84.bbs import  LineEditor, gosub, showart, getch
import os

__author__ = 'Hellbeard'
__version__ = 1.0

# --------------------------------------------------------------------------

def waitprompt():
    term = getterminal()
    echo (term.normal+'\n\r'+term.magenta+'('+term.green+'..'+term.white+' press any key to continue '+term.green+'..'+term.magenta+')')
    getch()
    echo(term.normal_cursor)

# ---------------------------------------------------

def showansi(filename):
    for line in showart(os.path.dirname(__file__)+ '/art/'+filename, 'topaz'):
        echo(line)

# ---------------------------------------------------

def toplist(parameter):
    session, term = getsession(), getterminal()
    handle = session.user.handle

    counter = 0
    user_handles = list_users()
    username = {}
    feature = {}
    location = {}
    database = {}

    for handle in user_handles:

       user_record = get_user(handle)
       if parameter == 'calls':
           database[str(user_record.handle)] = user_record.calls
       if parameter == 'msgs':
           database[str(user_record.handle)] = user_record.get('msgs_sent',0)

    for name in sorted(database, key=database.get, reverse=True):
       if name != 'sysopname': # write your handle here if you dont want to be included
           username[counter] = name
 
           user_record = get_user(name)
           location[counter] = user_record.location

           feature[counter] = str(database[name])
           counter = counter + 1

    if counter > 10:
        counter = 10    # we only want to display top ten users

    echo(term.clear())
    showansi('topten.ans')

    if parameter == 'calls':
        echo(term.yellow+term.move(7,1)+'[ % ]                                                 - tOP tEN cALLERS  [ % ]')
    if parameter == 'msgs':
        echo(term.yellow+term.move(7,1)+'[ % ]                                                 - tOP tEN wRITERS  [ % ]')

    echo(term.cyan+term.move(9,3)+'username'+term.move_x(27)+'group/location'+term.move_x(67)+parameter+'\n\n')

    for i in range (0, counter):
        echo(term.white+term.move_x(3)+username[i]+term.move_x(27)+location[i]+term.move_x(67)+feature[i]+'\r\n')

    waitprompt()

# --------------------------------------------------------------------------

def main():
    session, term = getsession(), getterminal()
    dirty = True

    while True:
        if dirty or session.poll_event('refresh'):
            echo(term.clear())
            showansi('bulletinsmenu.ans')
        echo ('\r\n'+term.normal+term.white+'  ['+term.blue+'Select bulletin'+term.white+']: ')
        inp = getch()

        dirty = True
        if inp == u'1':
            toplist('calls')
        elif inp == u'2':
            toplist('msgs')
        elif inp == u'3':
            gosub('textbrowse')
        else:                      # any other key will return to main menu
            return
