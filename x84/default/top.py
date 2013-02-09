"""
Post-login screen for x/84, http://github.com/jquast/x84

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session.
"""

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
    from x84.bbs import getsession, getterminal, showcp437, echo
    import os
    session, term = getsession(), getterminal()
    # display random artwork ..
    artfile = os.path.join(os.path.dirname(__file__), 'art',
            '*.ans' if term.number_of_colors != 0 else '*.asc')
    echo(u'\r\n\r\n')
    for line in (showcp437(artfile)):
        echo(line)
    if term.number_of_colors == 256:
        echo(u''.join((
            term.normal, '\r\n\r\n',
            BADGE256, u'\r\n')))


def get_ynbar():
    from x84.bbs import getterminal, Selector
    term = getterminal()
    ynbar = Selector(yloc=term.height - 1,
                     xloc=term.width - 31,
                     width=30, left='Yes', right='No')
    if term.number_of_colors:
        ynbar.colors['selected'] = term.green_reverse
    ynbar.keyset['left'].extend((u'y', u'Y',))
    ynbar.keyset['right'].extend((u'n', u'N',))
    return ynbar


def redraw_quicklogin(ynbar):
    from x84.bbs import getterminal
    prompt_ql = u' QUiCk lOGiN ?! '
    term = getterminal()
    return u''.join((
            term.move(ynbar.yloc - 1, ynbar.xloc),
            term.normal,
            term.bold_blue(prompt_ql),
            ynbar.refresh(),
            ))


def main(handle=None):
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import goto, gosub, User, get_user
    import logging
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    logger = logging.getLogger()
    # 1. determine & assign user record,
    if handle in (None, u'', 'anonymous',):
        logger.warn('anonymous login by %s.', session.sid)
        session.user = User(u'anonymous')
    else:
        logger.info('%r logged in.', handle)
        session.user = get_user(handle)

    # 2. update call records
    session.user.calls += 1
    session.user.lastcall = time.time()
    if session.user.handle != 'anonymous':
        session.user.save()

    # 3. if no preferred charset run charset.py selector
    if (session.user.get('charset', None) is None
            or session.user.handle == 'anonymous'):
        gosub('charset')
    else:
        # load default charset
        session.encoding = session.user.get('charset')
        fun = term.bold_green(' (EXCEllENt!)')
        if session.encoding != 'utf8':
            fun = term.bold_red(u' (bUMMER!)')
        echo(u'\r\n\r\nUsing preferred charset, %s%s.\r\n' % (
            session.encoding, fun))

    # 4. impress with art, prompt for quick login (goto 'main'),
    display_intro()
    if session.user.get('expert', False):
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
                display_intro()
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
