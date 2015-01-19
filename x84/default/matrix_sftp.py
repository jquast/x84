"""
SFTP Matrix for x/84.

This script is the default session entry point for all sftp connections.

Nothing especially cute going on here yet.  Ultimately we'd like
a single-directioned communication from x84.sftp.StubSFTPServer
so that we can be notified of the user activity.  We need to make
sure to ensure certain kinds of events are ignored or not handled,
also.

It is *especially* important *never* to echo anything to the
client.  We are still able to push bytes through, though we should
not and allow the sftp subsystem handler to do that for us.

Also, anonymous and new users are not well-handled, here.
"""

# std imports
import logging


def main(anonymous=False, new=False, username=''):
    """ Main procedure. """
    from x84.bbs import (
        getsession,
        getterminal,
        find_user,
        get_user,
        User,
    )

    session, term = getsession(), getterminal()
    session.activity = 'sftp'

    if anonymous:
        user = User(u'anonymous')
    else:
        assert not new, ("new@ user not supported by SFTP.")

        # ProperCase user-specified handle
        handle = find_user(username)
        assert handle is not None, handle

        # fetch user record
        user = get_user(handle)

    # assign session user, just as top.py function login()
    session.user = user

    while True:
        inp = term.inkey()  # should block indefinately
        log = logging.getLogger(__name__)
        log.warn('Got inkey: {0!r}'.format(inp))
