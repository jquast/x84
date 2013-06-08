"""
Post-login screen for x/84, http://github.com/jquast/x84

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session.
"""

# generated using lolcat ..

BADGE256 = u'\x1b'.join((u'',
                            u'[38;5;49m2', u'[0m', u'[38;5;48m5', u'[0m',
                            u'[38;5;48m6', u'[0m', u'[38;5;48m-', u'[0m',
                            u'[38;5;48mC', u'[0m', u'[38;5;84mO', u'[0m',
                            u'[38;5;83ml', u'[0m', u'[38;5;83mO', u'[0m',
                            u'[38;5;83mr', u'[0m', u'[38;5;83m ', u'[0m',
                            u'[38;5;83mb', u'[0m', u'[38;5;119mA', u'[0m',
                            u'[38;5;118md', u'[0m', u'[38;5;118mG', u'[0m',
                            u'[38;5;118mE', u'[0m', u'[38;5;118m ', u'[0m',
                            u'[38;5;154mA', u'[0m', u'[38;5;154mW', u'[0m',
                            u'[38;5;154mA', u'[0m', u'[38;5;154mR', u'[0m',
                            u'[38;5;154mD', u'[0m', u'[38;5;184mE', u'[0m',
                            u'[38;5;184md', u'[0m', u'[38;5;184m!', u'[0m',))


def display_intro():
    """ Display art, 256-color badge, and '!'encoding help. """
    from x84.bbs import getterminal, showcp437, echo
    import os
    term = getterminal()
    # display random artwork ..
    artfile = os.path.join(os.path.dirname(__file__), 'art',
                           '*.ans' if term.number_of_colors != 0 else '*.asc')
    echo(u'\r\n\r\n')
    for line in showcp437(artfile):
        echo(line)
    if term.number_of_colors == 256 and term.kind.startswith('xterm'):
        echo(u''.join((
            term.normal, '\r\n\r\n',
            BADGE256, u'\r\n',
            u'\r\n')))
    echo(u'! to change encoding\r\n')


def get_ynbar():
    """ Retrieve yes/no bar for quick login. """
    from x84.bbs import getterminal, Selector
    term = getterminal()
    ynbar = Selector(yloc=term.height - 1,
                     xloc=term.width - 31,
                     width=30, left='Yes', right='No')
    ynbar.colors['selected'] = term.green_reverse
    ynbar.keyset['left'].extend((u'y', u'Y',))
    ynbar.keyset['right'].extend((u'n', u'N',))
    return ynbar


def redraw_quicklogin(ynbar):
    """ Redraq yes/no bar for quick login. """
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
    """ Main procedure. """
    # pylint: disable=R0914,R0912,R0915
    #         Too many local variables
    #         Too many branches
    #         Too many statements
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import goto, gosub, User, get_user, DBProxy
    import logging
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    logger = logging.getLogger()

    # 0. just a gimmicky example,
    gosub('productive')

    # 1. determine & assign user record,
    if handle in (None, u'', 'anonymous',):
        logger.info('anonymous login by %s.', session.sid)
        session.user = User(u'anonymous')
    else:
        logger.debug('%r logged in.', handle)
        session.user = get_user(handle)
        timeout = session.user.get('timeout', None)
        if timeout is not None:
            echo(u'\r\n\r\nUsing preferred timeout of %ss.\r\n' % (
                timeout,))
            session.send_event('set-timeout', timeout)

    # 2. update call records
    session.user.calls += 1
    session.user.lastcall = time.time()
    if session.user.handle != 'anonymous':
        session.user.save()

    # record into " last caller " record
    key = (session.user.handle)
    lcall = (session.user.lastcall, session.user.calls, session.user.location)
    db = DBProxy('lastcalls')
    db[key] = lcall

    # 3. if no preferred charset run charset.py selector
    if (session.user.get('charset', None) is None
            or session.user.handle == 'anonymous'):
        gosub('charset')
        session.activity = 'top'
    else:
        # load default charset
        session.encoding = session.user.get('charset')
        fun = term.bold_green(' (EXCEllENt!)')
        if session.encoding != 'utf8':
            fun = term.bold_red(u' (bUMMER!)')
        echo(u'\r\n\r\nUsing preferred charset, %s%s.\r\n' % (
            session.encoding, fun))

    # 4. impress with art, prompt for quick login (goto 'main'),
    if session.user.get('expert', False):
        dirty = True
        while True:
            if session.poll_event('refresh'):
                dirty = True
            if dirty:
                session.activity = 'top'
                display_intro()
                echo(u'\r\n QUiCk lOGiN [yn] ?\b\b')
            dirty = False
            inp = getch(1)
            if inp in (u'y', u'Y'):
                goto('main')
            elif inp in (u'n', u'N'):
                break
            elif inp in (u'!',):
                gosub('charset')
                dirty = True
    else:
        ynbar = get_ynbar()
        dirty = True
        while not ynbar.selected:
            if session.poll_event('refresh'):
                dirty = True
            if dirty:
                # redraw yes/no
                session.activity = 'top'
                swp = ynbar.selection
                ynbar = get_ynbar()
                ynbar.selection = swp
                display_intro()
                echo(redraw_quicklogin(ynbar))
            dirty = False
            inp = getch(1)
            if inp in (u'!',):
                gosub('charset')
                dirty = True
            elif inp is not None:
                echo(ynbar.process_keystroke(inp))
                if ynbar.quit:
                    goto('main')
        if ynbar.selection == ynbar.left:
            goto('main')

    # 5. last callers
    gosub('lc')
    session.activity = 'top'

    # 6. check for new public/private msgs,
    gosub('readmsgs', set())
    session.activity = 'top'

    # 7. news
    gosub('news')
    session.activity = 'top'

    # 8. one-liners
    gosub('ol')
    session.activity = 'top'

    # 9. weather
    if session.user.get('location', None):
        gosub('weather')

    goto('main')
