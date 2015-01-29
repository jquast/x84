"""
SSH Matrix for x/84.

This script is the default session entry point for all ssh connections.

As our transport is ssh -- we've *already* authenticated the user,
though, when 'anonymous' login is enabled, or the handle is one of
the 'new user handles', we pass the mutually exclusive boolean keyword
arguments 'anonymous' or 'new'.

The argument 'username' is always set as the 'user@' argument of the
connecting ssh client -- it could be 'anonymous' or 'new', or any
case insensitive match of a user handle -- it does not necessarily
guarantee that the user exists!

When set, this is a user that should be found under find_user(username)
who may have already authenticated by some various means.
"""


def main(anonymous=False, new=False, username=''):
    """ Main procedure. """
    from x84.bbs import echo, goto, find_user, ini
    topscript = ini.CFG.get('matrix', 'topscript')
    nuascript = ini.CFG.get('nua', 'script')

    # http://www.termsys.demon.co.uk/vtansi.htm
    # disable line-wrapping
    echo(unichr(27) + u'[7l')

    # http://www.xfree86.org/4.5.0/ctlseqs.html
    # Save xterm icon and window title on stack.
    echo(unichr(27) + u'[22;0t')

    if anonymous:
        # user ssh'd in as anonymous@
        goto(topscript, 'anonymous')
    elif new:
        # user ssh'd in as new@
        goto(nuascript)

    handle = find_user(username)
    assert handle is not None, handle
    goto(topscript, handle=handle)
