"""
Default matrix (login) script for x/84.

This script is the default session entry point for all connections.

Or simply put, the login program. It is configured in default.ini file,
under section 'matrix'. Alternative matrices may be considered by their
connection type, using script_{telnet,ssh}

In legacy era, a matrix script might be something to fool folk not in the
know, meant to divert agents from underground boards, require a passcode,
or even swapping the modem into a strange stop/bit/parity configuration,
callback mechanisms, etc..

Read all about it in old e-zines.
"""
# std
import logging
import random
import time
import os

from x84.bbs import getterminal, get_ini, goto, gosub
from x84.bbs import echo, showart, syncterm_setfont, LineEditor
from x84.bbs import find_user, get_user, User
from x84.engine import __url__

log = logging.getLogger()
here = os.path.dirname(__file__)

#: name of bbs
system_bbsname = get_ini(
    section='system', key='bbsname'
) or 'Unnamed'

#: whether new user accounts are accepted
new_allowed = get_ini(
    section='nua', key='allow_apply', getter='getboolean'
) or False

#: which login names trigger new user account script
new_usernames = get_ini(
    section='matrix', key='newcmds', split=True
) or ['new']

#: which script to execute to apply for new account
new_script = get_ini(
    section='nua', key='script'
) or 'nua'

#: which script to execute on successful login
top_script = get_ini(
    section='matrix', key='topscript'
) or 'top'

#: whether anonymous login is allowed
anonymous_allowed = get_ini(
    section='matrix', key='enable_anonymous', getter='getboolean'
) or False

#: which login names that trigger anonymous login.
anonymous_names = get_ini(
    section='matrix', key='anoncmds', split=True
) or ['anonymous']

#: whether password resets are allowed
reset_allowed = get_ini(
    section='matrix', key='enable_pwreset', getter='getboolean'
) or False

reset_script = get_ini(
    section='matrix', key='reset_script'
) or 'pwreset'

bye_usernames = get_ini(
    section='matrix', key='byecmds', split=True
) or ['bye', 'logoff', 'exit', 'quit']

#: maximum length of user handles
username_max_length = get_ini(
    section='nua', key='max_user', getter='getint'
) or 10

#: maximum length of password
password_max_length = get_ini(
    section='nua', key='max_pass', getter='getint'
) or 15

#: random maximum time to artificially sleep for unknown user.
unknown_sleep = get_ini(
    section='matrix', key='unknown_sleep', getter='getfloat'
) or 2.0

#: maximum failed logins before disconect
login_max_attempts = get_ini(
    section='matrix', key='max_login_attemps', getter='getint'
) or 5

#: on-connect fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='matrix', key='syncterm_font'
) or 'topaz'

#: on-connect banner
art_file = get_ini(
    section='matrix', key='art_file'
) or os.path.join(here, 'art', 'matrix.ans')

#: encoding on banner
art_encoding = get_ini(
    section='matrix', key='art_encoding'
) or 'cp437'

#: primary color (highlight)
color_primary = get_ini(
    section='matrix', key='color_primary'
) or 'red'

#: secondary color (lowlight)
color_secondary = get_ini(
    section='matrix', key='color_secondary'
) or 'green'

#: password hidden character
hidden_char = get_ini(
    section='nua', key='hidden_char'
) or u'\u00f7'


def display_banner(term):
    """ Display on-connect banner and set a few sequences. """

    # reset existing SGR attributes
    echo(term.normal)

    # set syncterm font, if any
    if syncterm_font and term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    # http://www.termsys.demon.co.uk/vtansi.htm
    # disable line-wrapping (SyncTerm does not honor, careful!)
    echo(u'\x1b[7l')

    if term.kind.startswith('xterm'):
        # http://www.xfree86.org/4.5.0/ctlseqs.html
        # Save xterm icon and window title on stack.
        echo(u'\x1b[22;0t')

    # move to beginning of line and clear, in case syncterm_setfont
    # has been mis-interpreted, as it follows CSI with space, which
    # causes most terminal emulators to receive literally after CSI.
    echo(term.move_x(0) + term.clear_eol)

    # display name of bbs and url to sourcecode.
    highlight = getattr(term, color_primary)
    sep = getattr(term, color_secondary)(u'::')

    echo(u'{sep} Connected to {name}.\r\n'.format(
        sep=sep, name=highlight(system_bbsname)))
    echo(u'{sep} See {url} for source code.\r\n'.format(
        sep=sep, url=highlight(__url__)))

    # display on-connect banner (`art_file`)
    map(echo, showart(art_file, encoding=art_encoding, center=True))

    # display various ini-configured login username aliases.
    if new_allowed:
        echo(u"   Login as '{0}' to create an account."
             .format(highlight(new_usernames[0])))
    if anonymous_allowed:
        echo(u"\r\n   Login as '{0}' is allowed."
             .format(highlight(anonymous_names[0])))
    if reset_allowed:
        echo(u"\r\n   Forgot password? Login as '{0}'."
             .format(highlight('reset')))


def authenticate_user(handle, password):
    """ Return True if the given handle and password are correct. """

    # artificial delay -- this ensures people cannot guess
    # for user accounts, where existing ones would delay a
    # long while, but unknown users are quickly denied.
    artificial_delay = max(1.0, random.randrange(0, unknown_sleep * 100) / 100)

    matching_handle = find_user(handle)
    if matching_handle is None:
        log.debug('Failed login for {handle}: no such user.'
                  .format(handle=handle))
        time.sleep(artificial_delay)
        return False

    elif not password.strip():
        log.debug('Failed login for {handle}: password not provided.'
                  .format(handle=handle))
        time.sleep(artificial_delay)
        return False

    user = get_user(matching_handle)
    if user.auth(password):
        # success !
        log.debug('Login succeeded for {handle}.'
                  .format(handle=handle))
        return user

    log.debug('Failed login for {handle}: wrong password.'
              .format(handle=handle))
    return False


def do_login(term):
    sep_ok = getattr(term, color_secondary)(u'::')
    sep_bad = getattr(term, color_primary)(u'::')
    colors = {'highlight': getattr(term, color_primary)}
    for _ in range(login_max_attempts):
        echo(u'\r\n\r\n{sep} Login: '.format(sep=sep_ok))
        handle = LineEditor(username_max_length, colors=colors
                            ).read() or u''

        if handle.strip() == u'':
            continue

        # user says goodbye
        if handle.lower() in bye_usernames:
            return

        # user applies for new account
        if new_allowed and handle.lower() in new_usernames:
            gosub(new_script)
            display_banner(term)
            continue

        # user wants to reset password
        if reset_allowed and handle.lower() == 'reset':
            gosub(reset_script)
            display_banner(term)
            continue

        # user wants to login anonymously
        if anonymous_allowed and handle.lower() in anonymous_names:
            user = User('anonymous')
        else:
            # authenticate password
            echo(u'\r\n\r\n{sep} Password: '.format(sep=sep_ok))
            password = LineEditor(password_max_length,
                                  colors=colors,
                                  hidden=hidden_char
                                  ).read() or u''

            user = authenticate_user(handle, password)
            if not user:
                echo(u'\r\n\r\n{sep} Login failed.'.format(sep=sep_bad))
                continue

        goto(top_script, handle=user.handle)

    echo(u'\r\n\r\n{sep} Too many authentication attempts.\r\n'
         .format(sep=sep_bad))


def main(anonymous=False, new=False):
    """
    Script entry point.

    This is the default login matrix for the bbs system.

    It takes no arguments or keyword arguments, because it assumes
    the user should now be authenticated, such as occurs for example
    on telnet.
    """
    term = getterminal()

    display_banner(term)

    if anonymous:
        # user rlogin'd in as anonymous@
        goto(top_script, 'anonymous')
    elif new:
        # user rlogin'd in as new@
        goto(new_script)

    # do_login will goto/gosub various scripts, if it returns, then
    # either the user entered 'bye', or had too many failed attempts.
    do_login(term)

    log.debug('Disconnecting.')

    # it is necessary to provide sufficient time to send any pending
    # output across the transport before disconnecting.
    term.inkey(1.5)
