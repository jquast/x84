""" Userlister for x/84 bbs, https://github.com/jquast/x84 """
__version__ = 1.0
__author__ = 'Hellbeard'

from x84.bbs import getsession, getterminal, echo
from x84.bbs import list_users, get_user, timeago, showcp437
import time
import os


def banner():
    """ Display banner """
    term = getterminal()
    echo(term.clear)
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'userlist.ans')
    for line in showcp437(artfile):
        echo(line)
    echo(u'\r\n')


def waitprompt():
    term = getterminal()
    echo(u'\n\r')
    echo(term.magenta(u'(') + term.green(u'..'))
    echo(term.white(u' press any key to continue ') + term.green(u'..'))
    echo(term.magenta(u')'))
    term.inkey()
    echo(term.normal_cursor)
    return

def main():
    session, term = getsession(), getterminal()
    session.activity = 'userlist'
    banner()
    firstpage = True
    handles = sorted(list_users(), key=lambda s: s.lower())
    for counter, handle in enumerate(handles):
        user = get_user(handle)
        origin = user.location
        ago = timeago(time.time() - user.lastcall)
        echo(term.move_x(4) + term.white(handle))
        echo(term.move_x(32) + term.green(origin))
        echo(term.move_x(59) + term.bright_white(ago))
        if (firstpage and counter % (term.height - 12) == 0 or
                counter % (term.height - 2) == 0):
            firstpage = False
            waitprompt()
            echo(term.move_x(0) + term.clear_eol + term.move_up)

    waitprompt()
