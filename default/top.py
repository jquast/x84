"""
Post-login screen for x/84, http://github.com/jquast/x84

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session.

Otherwise the user record of the handle passed is retreived and assigned.
"""
# generated using lolcat ..
BADGE256 = (u'\033[38;5;49m2\033[0m\033[38;5;48m5\033[0m\033[38;5;48m6\033[0m'
             '\033[38;5;48m-\033[0m\033[38;5;48mC\033[0m\033[38;5;84mO\033[0m'
             '\033[38;5;83ml\033[0m\033[38;5;83mO\033[0m\033[38;5;83mr\033[0m'
             '\033[38;5;83m \033[0m\033[38;5;83mb\033[0m\033[38;5;119mA\033[0m'
             '\033[38;5;118md\033[0m\033[38;5;118mG\033[0m\033[38;5;118mE\033[0m'
             '\033[38;5;118m \033[0m\033[38;5;154mA\033[0m\033[38;5;154mW\033[0m'
             '\033[38;5;154mA\033[0m\033[38;5;154mR\033[0m\033[38;5;154mD\033[0m'
             '\033[38;5;184mE\033[0m\033[38;5;184md\033[0m\033[38;5;184m!\033[0m')


def main(handle=None):
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    if handle in (None, 'anonymous'):
        logger.warn ('anonymous login (source=%s).', session.source)
        user = User(u'anonymous')
    else:
        logger.info ('%r logged in.', handle)
        user = get_user(handle)

    # 1. assign session property, .user
    session.user = user

    # 2. update call records
    user.calls += 1
    user.lastcall = time.time()
    if user.handle != 'anonymous':
        user.save ()

    # 3. if no preferred charset run charset.py selector
    if user.get('charset', None) is None:
        logger.warn (user.get('charset', None))
        gosub ('charset')
    else:
        # load default charset
        session.encoding = user.get('charset')
        echo ('\r\nUsing user-preferred charset %s%s.', session.encoding,
                '(EXCEllENt!)' if session.encoding == 'utf8' else 'bUMMER!')

    # 4. impress with art, prompt for quick login,
    if session.env.get('TERM') == 'unknown':
        if not user.get('expert', False):
            echo (term.move (0, 0) + term.clear)
            echo (showcp437('default/art/top/*.asc'))
        echo (u'\r\n QUiCk lOGiN? [n]')

        # simply hotkey y/n; our terminal is too dumb for lightbar
        while True:
            yn = getch()
            if yn in (u'y', u'Y'):
                goto ('main')
            elif yn in (u'n', u'N'):
                break
    else:
        echo (term.move (0, 0) + term.clear)
        if not user.get('expert', False):
            if term.number_of_colors == 256:
                echo (showcp437('default/art/top/*.256'))
                echo (BADGE256)
            else:
                echo (showcp437('default/art/top/*.ans'))

        # lightbar left/right, just like the priginal blood island ..
        ynbar = Selector(yloc=term.height - 1, xloc=term.width - 30, width=30,
                left='Yes', right='No')
        if term.number_of_colors:
            ynbar.colors['selected'] = term.green_reverse
        echo (term.move(ynbar.yloc-1, ynbar.xloc) + term.normal)
        echo (u' QUiCk lOGiN ?! '.center(ynbar.width))
        echo (ynbar.refresh())
        while not ynbar.selected:
            inp = getch()
            echo (ynbar.process_keystroke (inp))
            if ynbar.quit:
                goto ('main')
        if ynbar.selection == ynbar.left:
            goto ('main')

    # 5. check for new msgs,
    #gosub('chkmsgs')

    # 6. last callers
    gosub('lc')

    # 7. news
    gosub('news')

    # 8. one-liners
    gosub('ol')

    goto('main')
