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
    yield unicode sequences for any given ANSI Art (of cp437 encoding). Effort
    is made to strip SAUCE data, translate cp437 to unicode, and trim artwork
    too large to display. If keyboard input is pressed, 'msg_cancel' is
    returned as the last line of art
    """
    import sauce
    session, term = getsession(), getterminal()
    msg_cancel = u''.join((term.normal,
        term.bold_blue(u'--'),
        u'CANCEllEd bY iNPUt ',
        term.bold_blue(u'--'),))
    msg_notfound = u''.join((
        term.bold_red(u'--'),
        u'no files matching %s' % (filepattern,),
        term.bold_red(u'--'),))
    fobj = (ropen(filepattern)
            if '*' in filepattern or '?' in filepattern
            else open(filepattern, 'rb'))
    if fobj is None:
        yield msg_notfound + u'\r\n'
        return
    # allow slow terminals to cancel by pressing a keystroke
    for line in from_cp437(sauce.SAUCE(fobj).__str__()).splitlines():
        if session.poll_event('input'):
            yield u'\r\n' + msg_cancel + u'\r\n'
            return
        yield line + u'\r\n'
