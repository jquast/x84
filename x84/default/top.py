"""
Post-login screen for x/84, http://github.com/jquast/x84

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session.

Otherwise the user record of the handle passed is retreived and assigned.
"""

import os
from x84.bbs import echo, getsession, getterminal, showcp437, Selector, User
from x84.bbs import get_user, gosub, getch, goto

# generated using lolcat ..
BADGE256 = (
    u'\033[38;5;49m2\033[0m\033[38;5;48m5\033[0m\033[38;5;48m6\033[0m'
    u'\033[38;5;48m-\033[0m\033[38;5;48mC\033[0m\033[38;5;84mO\033[0m'
    u'\033[38;5;83ml\033[0m\033[38;5;83mO\033[0m\033[38;5;83mr\033[0m'
    u'\033[38;5;83m \033[0m\033[38;5;83mb\033[0m\033[38;5;119mA\033[0m'
    u'\033[38;5;118md\033[0m\033[38;5;118mG\033[0m\033[38;5;118mE\033[0m'
    u'\033[38;5;118m \033[0m\033[38;5;154mA\033[0m\033[38;5;154mW\033[0m'
    u'\033[38;5;154mA\033[0m\033[38;5;154mR\033[0m\033[38;5;154mD\033[0m'
    u'\033[38;5;184mE\033[0m\033[38;5;184md\033[0m\033[38;5;184m!\033[0m')


def display_intro():
    # try to display something impressive, yet compatible
    session, term = getsession(), getterminal()
    rstr = u''
    if not session.user.get('expert', False) and (
            session.env.get('TERM') != 'unknown'):
        rstr += term.move(0, 0) + term.clear

    # color terminal gets art
    if (session.env.get('TERM') != 'unknown'
            and term.number_of_colors != 0):
        if term.width >= 79:
            rstr += showcp437(os.path.join(
                os.path.dirname(__file__), 'art', 'top', '*.ans'))
        elif term.width >= 76:
            rstr += showcp437(os.path.join(
                os.path.dirname(__file__), 'art', 'top', '*.asc'))
        elif term.width >= 40:
            if term.number_of_colors >= 256:
                rstr += showcp437(os.path.join(
                    os.path.dirname(__file__), 'art', 'plant-256.ans'))
            else:
                rstr += showcp437(os.path.join(
                    os.path.dirname(__file__), 'art', 'plant.ans'))
        else:
            rstr += u'[top]\r\n'

    # non-color terminal gets ascii
    else:
        if term.width >= 76:
            rstr += showcp437(os.path.join(
                os.path.dirname(__file__), 'art', 'top', '*.asc'))
    if term.number_of_colors == 256:
        rstr += '\r\n\r\n' + BADGE256
    return rstr


def get_ynbar():
    term = getterminal()
    ynbar = Selector(yloc=term.height - 1,
                     xloc=term.width - 30,
                     width=30, left='Yes', right='No')
    if term.number_of_colors:
        ynbar.colors['selected'] = term.green_reverse
    ynbar.keyset['left'].extend((u'y', u'Y',))
    ynbar.keyset['right'].extend((u'n', u'N',))
    return ynbar


def redraw_quicklogin(ynbar):
    prompt_ql = u' QUiCk lOGiN ?! '
    term = getterminal()
    rstr = u''
    rstr += term.move(ynbar.yloc - 1, ynbar.xloc) + term.normal
    rstr += term.bold_blue(prompt_ql)
    rstr += ynbar.refresh()
    return rstr


def main(handle=None):
    import logging
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    logger = logging.getLogger()
    # 1. determine user record,
    if handle in (None, 'anonymous'):
        logger.warn('anonymous login (source=%s).', session.source)
        user = User(u'anonymous')
    else:
        logger.info('%r logged in.', handle)
        user = get_user(handle)
    # 2. assign session user
    session.user = user

    # 3. update call records
    session.user.calls += 1
    session.user.lastcall = time.time()
    if session.user.handle != 'anonymous':
        session.user.save()

    # 4. if no preferred charset run charset.py selector
    if session.user.get('charset', None) is None:
        gosub('charset')
    else:
        # load default charset
        session.encoding = session.user.get('charset')
        fun = (term.bold_green('(EXCEllENt!)')
               if session.encoding == 'utf8'
               else term.bold_red(u'bUMMER!'))
        echo(u'\r\nUsing preferred charset %s%s.' % (session.encoding, fun))

    # 5. impress with art, prompt for quick login (goto 'main'),
    echo(display_intro())
    if (session.env.get('TERM') == 'unknown'
            or session.user.get('expert', False)):
        echo(u'\r\n QUiCk lOGiN? [yn]')
        while True:
            yn = getch(1)
            if yn in (u'y', u'Y'):
                goto('main')
            elif yn in (u'n', u'N'):
                break
            if session.poll_event('refresh'):
                echo(u'\r\n QUiCk lOGiN? [yn]')
    else:
        ynbar = get_ynbar()
        echo(redraw_quicklogin(ynbar))
        while not ynbar.selected:
            inp = getch(1)
            if inp is not None:
                echo(ynbar.process_keystroke(inp))
            if session.poll_event('refresh'):
                # redraw yes/no
                swp = ynbar.selection
                ynbar = get_ynbar()
                ynbar.selection = swp
                echo(display_intro())
                echo(redraw_quicklogin(ynbar))
            if ynbar.quit:
                goto('main')
        if ynbar.selection == ynbar.left:
            goto('main')

    # 5. check for new msgs,
    # gosub('chkmsgs')

    # 6. last callers
    gosub('lc')

    # 7. news
    gosub('news')

    # 8. one-liners
    gosub('ol')

    goto('main')
