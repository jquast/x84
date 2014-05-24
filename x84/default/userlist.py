""" Userlister for x/84 bbs, https://github.com/jquast/x84 """
__version__ = 1.0
__author__ = 'Hellbeard'

from x84.bbs import getsession, getterminal, echo
from x84.bbs import list_users, get_user, timeago, showcp437
import time
import os

# actually ansi height + prompt length
BANNER_HEIGHT = 12


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
    echo('\r\n')

def main():
    session, term = getsession(), getterminal()
    session.activity = 'Viewing Userlist'
    banner()
    firstpage = True
    handles = sorted(list_users(), key=lambda s: s.lower())
    for counter, handle in enumerate(handles, 1):
        user = get_user(handle)
        origin = user.location
        ago = timeago(time.time() - user.lastcall)
        echo(u' '*4)
        echo(term.ljust(term.white(handle), 12))
        echo(term.ljust(term.green(origin), 28))
        echo(term.bright_white(ago))
        echo(u'\r\n')
        # first page only, prompt stops at height - BANNER_HEIGHT
        if (firstpage and counter == term.height - BANNER_HEIGHT or
                counter % (term.height - 1) == 0):
            waitprompt()
            echo(term.move_x(0) + term.clear_eol + term.move_up)
            firstpage = False

    waitprompt()
