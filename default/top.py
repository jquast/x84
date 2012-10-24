"""
Post-login screen for x/84, http://github.com/jquast/x84

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session.

Otherwise the user record of the handle passed is retreived and assigned.
"""
from bbs import *

# generated using lolcat ..
BADGE256 = (u'\033[38;5;20m2\033[0m\033[38;5;40m5\033[0m\033[38;5;42m6\033[0m'
             '\033[38;5;44m-\033[0m\033[38;5;60mC\033[0m\033[38;5;74mO\033[0m'
             '\033[38;5;78ml\033[0m\033[38;5;80mO\033[0m\033[38;5;84mr\033[0m'
             '\033[38;5;88m \033[0m\033[38;5;98mb\033[0m\033[38;5;108mA\033[0m'
             '\033[38;5;110md\033[0m\033[38;5;114mG\033[0m\033[38;5;118mE\033[0m'
             '\033[38;5;118m \033[0m\033[38;5;124mA\033[0m\033[38;5;128mW\033[0m'
             '\033[38;5;150mA\033[0m\033[38;5;152mR\033[0m\033[38;5;154mD\033[0m'
             '\033[38;5;180mE\033[0m\033[38;5;182md\033[0m\033[38;5;184m!\033[0m')

def display_intro():
    session, term = getsession(), getterminal()
    rstr = u''
    if not session.user.get('expert', False):
        rstr += term.move (0, 0) + term.clear
        if session.env.get('TERM') != 'unknown':
            if term.width >= 79:
                rstr += showcp437('default/art/top/*.ans')
        else:
            if term.width >= 76:
                rstr += showcp437('default/art/top/*.asc')

        if term.number_of_colors == 256:
            rstr += '\r\n\r\n' + BADGE256
    return rstr

def get_ynbar():
    term = getterminal()
    rstr = u''
    ynbar = Selector(yloc=term.height - 1, xloc=term.width - 30, width=30,
            left='Yes', right='No')
    if term.number_of_colors:
        ynbar.colors['selected'] = term.green_reverse
    ynbar.keyset['left'].extend ((u'y', u'Y',))
    ynbar.keyset['right'].extend ((u'n', u'N',))
    return ynbar

def redraw_quicklogin(ynbar):
    term = getterminal()
    rstr = u''
    rstr += term.move(ynbar.yloc-1, ynbar.xloc) + term.normal
    rstr += term.blue_reverse(u' QUiCk lOGiN ?! '.center(ynbar.width))
    rstr += ynbar.refresh()
    return rstr

def main(handle=None):
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    # 1. determine user record,
    if handle in (None, 'anonymous'):
        logger.warn ('anonymous login (source=%s).', session.source)
        user = User(u'anonymous')
    else:
        logger.info ('%r logged in.', handle)
        user = get_user(handle)
    # 2. assign session user
    session.user = user

    # 3. update call records
    session.user.calls += 1
    session.user.lastcall = time.time()
    if session.user.handle != 'anonymous':
        session.user.save ()

    # 4. if no preferred charset run charset.py selector
    if session.user.get('charset', None) is None:
        logger.warn (session.user.get('charset', None))
        gosub ('charset')
    else:
        # load default charset
        session.encoding = session.user.get('charset')
        echo ('\r\nUsing user-preferred charset %s%s.', session.encoding,
                '(EXCEllENt!)' if session.encoding == 'utf8' else 'bUMMER!')

    # 5. impress with art, prompt for quick login (goto 'main'),
    echo (display_intro())
    if session.env.get('TERM') == 'unknown':
        echo (u'\r\n QUiCk lOGiN? [yn]')
        while True:
            yn = getch(1)
            if yn in (u'y', u'Y'):
                goto ('main')
            elif yn in (u'n', u'N'):
                break
            if pollevent('refresh'):
                echo (u'\r\n QUiCk lOGiN? [yn]')
    else:
        ynbar = get_ynbar()
        echo (redraw_quicklogin(ynbar))
        while not ynbar.selected:
            inp = getch(1)
            if inp is not None:
                echo (ynbar.process_keystroke (inp))
            if pollevent('refresh'):
                # redraw yes/no
                swp = ynbar.selection
                ynbar = get_ynbar()
                ynbar.selection = swp
                echo (display_intro ())
                echo (redraw_quicklogin(ynbar))
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
