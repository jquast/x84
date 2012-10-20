"""
 post-login screen for X/84 (formerly 'The Progressive') BBS
"""

def main(login_handle=None):
    import time
    session, term = getsession(), getterminal()
    session.activity = 'Intro screen'

    user = User() if login_handle in (None, 'anonymous') \
        else getuser(login_handle)
    user.calls += 1
    user.lastcall = time.time()
    user.save ()
    upref_enc = user.get('charset', None)
    if upref_enc is not None:
        session.encoding = upref_enc
    session.user = user

    broadcastevent ('global', ('login', login_handle))

    # ?quick login
    echo (term.move (0, 0) + term.normal + term.clear)
    echo (u'\r\nQuick login? [yn] ')
    while True:
        k = getch()
        if k in ('y', 'Y', 'q'):
            goto ('main')
        elif k in ('n', 'N'):
            break

    # check for new messages
    #gosub('chkmsgs')

    # figure out character set
    gosub('charset')

    # long login
    # ... last callers
    gosub('lc')

    # ... news
    gosub('news')

    # ... one liners
    gosub('ol')

    goto('main')
