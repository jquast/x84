"""
Post-login screen for X/84 (formerly 'The Progressive') BBS.

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session. Otherwise the handle passed is assigned.
"""

def main(handle=None):
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    if handle in (None, 'anonymous'):
        user = User(u'anonymous')
    else:
        user = get_user(handle)

    # 1. assign session property, .user
    session.user = user

    # 2. update call records
    user.calls += 1
    user.lastcall = time.time()
    user.save ()

    # 3. load preferred charset, if any
    upref_enc = user.get('charset', None)
    if upref_enc is not None:
        session.encoding = upref_enc
        echo ("\r\n\r\nYour user-preferred session, '%s' has been set.")

    # 4. ?quick login
    if term.number_of_colors > 0 or session.env.get('TERM') != 'unknown':
        if term.width >= 79
    else:
        echo ('\r\nQuick login? [yn] ')
    else:

#    echo (term.move (0, 0) + term.normal + term.clear)
#    echo (u'\r\nQuick login? [yn] ')
#    while True:
#        k = getch()
#        if k in ('y', 'Y', 'q'):
#            goto ('main')
#        elif k in ('n', 'N'):
#            break
#
#    # check for new messages
#    #gosub('chkmsgs')
#
#    # figure out character set
#    gosub('charset')
#
#    # long login
#    # ... last callers
#    gosub('lc')
#
#    # ... news
#    gosub('news')
#
#    # ... one liners
#    gosub('ol')
#
#    goto('main')
