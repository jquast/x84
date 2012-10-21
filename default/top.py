"""
Post-login screen for X/84 (formerly 'The Progressive') BBS.

When login_handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session. Otherwise the handle passed is assigned.
"""

def main(login_handle=None):
    import time
    session, term = getsession(), getterminal()
    session.activity = 'top'
    if login_handle in (None, 'anonymous'):
        user = User(u'anonymous')
    else:
        user = get_user(login_handle)
    # assign user to session
    session.user = user
    # update call records
    user.calls += 1
    user.lastcall = time.time()
    user.save ()

    upref_enc = user.get('charset', None)
    if upref_enc is not None:
        session.encoding = upref_enc
        echo ("\r\n\r\nYour user-preferred session, '%s' has been set.")

#    broadcastevent ('global', ('login', login_handle))
#
#    # ?quick login
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
