"""
 post-login screen for X/84 (formerly 'The Progressive') BBS
"""

def main(login_handle=None):
    import time
    user = User() if login_handle in (None, 'anonymous') \
        else getuser(login_handle)
    user.calls += 1
    user.lastcall = time.time()
    user.save ()


    session = getsession()
    session.activity = 'Intro screen'
    session.user = user
    term = session.terminal

    # rebuild last caller db
    gosub('lc', True)

    # figure out character set
    gosub('charset')

    # check for new messages
    gosub('chkmsgs')

    # ?quick login
    echo ('\r\n\r\nQuick login? [yn] ')
    while True:
        k = getch()
        if k in ('y', 'Y', 'q'):
            goto ('main')
        elif k in ('n', 'N'):
            break

    # long login
    # ... last callers
    gosub('lc')

    # ... news
    gosub('news')

    # ... one liners
    gosub('ol')

    goto('main')
