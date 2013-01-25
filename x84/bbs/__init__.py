"""
x/84 bbs module, https://github.com/jquast/x84
"""

from x84.bbs.userbase import list_users, get_user, find_user, User, Group
from x84.bbs.exception import Disconnected, Goto
from x84.bbs.editor import LineEditor, ScrollingEditor
from x84.bbs.output import echo, timeago, Ansi
from x84.bbs.ansiwin import AnsiWindow
from x84.bbs.selector import Selector
from x84.bbs.lightbar import Lightbar
from x84.bbs.cp437 import from_cp437
from x84.bbs.dbproxy import DBProxy
from x84.bbs.pager import Pager
from x84.bbs.door import Door


def goto(*args):
    """
    Change bbs script. Does not return.
    """
    import x84.bbs.exception
    raise x84.bbs.exception.Goto(args)


def disconnect(reason=u''):
    """
    Disconnect session. Does not return.
    """
    raise Disconnected('disconnect%s',
                       ': %s' % (reason,) if 0 != len(reason) else u'')


def getsession():
    """
    Returns Session of calling process.
    """
    import x84.bbs.session
    return x84.bbs.session.getsession()


def getterminal():
    """
    Returns Terminal of calling process.
    """
    import x84.bbs.session
    return x84.bbs.session.getterminal()


def getch(timeout=None):
    """
    Retrieve a keystroke from 'input' queue, blocking forever or, when
    specified, None when timeout has elapsed.
    """
    return getsession().read_event('input', timeout)


def gosub(*arg):
    """
    Call bbs script with optional arguments, Returns value.
    """
    # pylint: disable=W0142
    #        Used * or ** magic
    return getsession().runscript(*(arg[0],) + arg[1:])


def ropen(filename, mode='rb'):
    """
    Open random file using wildcard (glob)
    """
    import glob
    import random
    files = glob.glob(filename)
    return open(random.choice(files), mode) if len(files) else None


def showcp437(filepattern):
    """
    Display a cp437 artfile relative to current script path, trimming SAUCE
    data and translating cp437 to utf8. A glob pattern can be used, such as
    'art/login*.ans'
    """
    import sauce
    fobj = ropen(filepattern, 'rb') \
        if '*' in filepattern or '?' in filepattern \
        else open(filepattern, 'rb')
    if fobj is None:
        return (u'\r\n<no files matching %s>\r\n' % (
            filepattern,))
    term = getterminal()
    return Ansi(from_cp437(sauce.SAUCE(fobj).__str__())).wrap(80) + term.normal
