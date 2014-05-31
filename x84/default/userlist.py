""" Userlister for x/84 bbs, https://github.com/jquast/x84 """
__version__ = 1.1
__author__ = 'Hellbeard'

from x84.bbs import getsession, getterminal, echo, getch
from x84.bbs import list_users, get_user, timeago, showcp437
import time
import os

# actually ansi height + prompt length
BANNER_HEIGHT = 12


def banner():
    """ Display banner """
    term = getterminal()
    echo(term.clear)
    artfile = os.path.join(os.path.dirname(__file__), 'userlist.ans')
    for line_no, line in enumerate(showcp437(artfile)):
        echo(line)
    else:
        line_no = 0
    echo(u'\r\n')
    return line_no


def waitprompt():
    """ Display "press enter" prompt and returns key input """
    term = getterminal()
    echo(u''.join(u'\r\n',
                  term.magenta(u'('),
                  term.green(u'..'),
                  term.white(u' press any key to continue '),
                  term.green(u'..'),
                  term.magenta(u')')))
    keypressed = getch()
    echo(u''.join(term.move_x(0),
                  term.clear_eol,
                  term.move_up,
                  term.green(u'-' * (term.width - 1)),
                  u'\r\n'))
    return keypressed


def main():
    session, term = getsession(), getterminal()
    session.activity = 'Viewing Userlist'
    banner_height = banner()
    firstpage = True
    handles = sorted(list_users(), key=str.lower)

    at_first_page = lambda counter: (
        firstpage and counter == term.height - banner_height)
    at_next_page = lambda counter: (
        0 == counter % (term.height - 2))

    for counter, handle in enumerate(handles, 1):
        user = get_user(handle)
        origin = user.location
        ago = timeago(time.time() - user.lastcall)
        echo(u' '*4)
        echo(term.ljust(term.white(handle), 28))
        echo(term.ljust(term.green(origin), 27))
        echo(term.bright_white(ago))
        echo(u'\r\n')
        if at_first_page(counter) or at_next_page(counter):
            if waitprompt() in (term.KEY_ESCAPE, 'q', 'Q'):
                return
            firstpage = False
    waitprompt()
