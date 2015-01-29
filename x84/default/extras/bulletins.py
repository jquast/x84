""" Bulletins script for x/84. """
# More to be added as soon as we get a filebase going.

from x84.bbs import getsession, getterminal, echo, list_users, get_user
from x84.bbs import gosub, showart, getch
from common import waitprompt
import os

__author__ = 'Hellbeard'
__version__ = 1.1

# ---------------------------------------------------


def showansi(filename):
    for line in showart(
            os.path.dirname(__file__) + '../art/' + filename, 'topaz'):
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

    echo(term.red + u' crunching data..')

    for handle in user_handles:
        user_record = get_user(handle)

        if u'sysop' in user_record.groups:
            continue

        if parameter == 'calls':
            database[user_record.handle.encode('utf8')] = user_record.calls
        if parameter == 'msgs':
            database[user_record.handle.encode('utf8')] = user_record.get(
                'msgs_sent', 0)

    for name in sorted(database, key=database.get, reverse=True):
        username[counter] = name
        user_record = get_user(name)
        location[counter] = user_record.location
        feature[counter] = str(database[name])
        counter = counter + 1

    if counter > 10:
        counter = 10    # we only want to display the top ten users

    echo(term.clear())
    showansi('topten.ans')

    if parameter == 'calls':
        echo(term.yellow + term.move(7, 1) +
             u'[ % ]                                                 - tOP tEN cALLERS  [ % ]')
    if parameter == 'msgs':
        echo(term.yellow + term.move(7, 1) +
             u'[ % ]                                                 - tOP tEN wRITERS  [ % ]')

    echo(term.cyan + term.move(9, 3) + u'username' + term.move_x(27) +
         u'group/location' + term.move_x(67) + parameter + u'\n\n')

    for i in range(0, counter):
        echo(term.white + term.move_x(3) +
             username[i] + term.move_x(27) + location[i] + term.move_x(67) + feature[i] + u'\r\n')

    waitprompt(term)

# --------------------------------------------------------------------------


def main():
    session, term = getsession(), getterminal()
    session.activity = u'bulletins menu'
    dirty = True

    while True:
        if dirty or session.poll_event('refresh'):
            echo(term.clear())
            showansi('bulletinsmenu.ans')
        echo(u'\r\n' + term.normal + term.white +
             u'  [' + term.blue + u'Select bulletin' + term.white + u']: ')
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
