"""
 Matrix login screen for X/84 (Formerly, 'The Progressive') BBS,

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

import os


def denied(msg):
    """ Display denied message, pause for input for 1s. """
    from x84.bbs import getterminal, echo, getch
    term = getterminal()
    echo(u'\r\n' + term.bold_red(msg))
    getch(1.0)


def get_username(handle=u''):
    """
    Prompt for a login handle. If unfound, script change to 'nua' when
    allow_apply is enabled (default=yes). Also allow 'anonymous' when enabled
    (default=no). A unicode handle of non-zero length is returned when the
    login handle matches a userbase record.
    """
    # pylint: disable=R0914,R0911
    #         Too many local variables
    #         Too many return statements
    from x84.bbs import getterminal, ini, echo, LineEditor, gosub, goto
    from x84.bbs import find_user, getch
    term = getterminal()
    prompt_user = u'\r\n  user: '
    apply_msg = u'\r\n\r\n  --> Create new account? [ynq]   <--' + '\b' * 5
    allow_apply = ini.CFG.getboolean('nua', 'allow_apply')
    enable_anonymous = ini.CFG.getboolean('matrix', 'enable_anonymous')
    newcmds = ini.CFG.get('matrix', 'newcmds').split()
    byecmds = ini.CFG.get('matrix', 'byecmds').split()
    denied_msg = u'\r\n\r\nfiRSt, YOU MUSt AbANdON YOUR libERtIES.'
    badanon_msg = u"\r\n  " + term.bright_red + u"'%s' login denied."
    max_user = ini.CFG.getint('nua', 'max_user')
    nuascript = ini.CFG.get('nua', 'script')
    topscript = ini.CFG.get('matrix', 'topscript')

    echo(prompt_user)
    handle = LineEditor(max_user, handle).read()
    if handle is None or 0 == len(handle.strip()):
        echo(u'\r\n')
        return u''
    elif handle.lower() in newcmds:
        if allow_apply:
            gosub('nua', u'')
            return u''
        denied(denied_msg)
        return u''
    elif handle.lower() in byecmds:
        goto('logoff')
    elif handle.lower() == u'anonymous':
        if enable_anonymous:
            goto(topscript, 'anonymous')
        denied(badanon_msg % (handle,))
        return u''
    u_handle = find_user(handle)
    if u_handle is not None:
        return u_handle  # matched
    if allow_apply is False:
        denied(denied_msg)
        return u''

    echo(apply_msg)
    ynq = getch()
    if ynq in (u'q', u'Q', term.KEY_EXIT):
        # goodbye
        goto('logoff')
    elif ynq in (u'y', u'Y'):
        # new user application
        goto(nuascript, handle)
    echo(u'\r\n')
    return u''


def try_reset(user):
    """ Prompt for password reset. """
    from x84.bbs import echo, getch, gosub
    prompt_reset = u'RESEt PASSWORD (bY E-MAil)? [yn]'
    echo(prompt_reset)
    while True:
        inp = getch()
        if inp in (u'y', u'Y'):
            return gosub('pwreset', user.handle)
        elif inp in (u'n', u'N'):
            echo(u'\r\n\r\n')
            return False


def try_pass(user):
    """
    Prompt for password and authenticate, returns True if succesfull.
    """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import getsession, getterminal, ini, LineEditor, echo
    session, term = getsession(), getterminal()
    prompt_pass = u'\r\n\r\n  pass: '
    status_auth = u'\r\n\r\n  ' + term.yellow_reverse(u"Encrypting ..")
    badpass_msg = (u'\r\n\r\n' + term.red_reverse +
                   u"'%s' login failed." + term.normal)
    max_pass = int(ini.CFG.get('nua', 'max_pass'))
    # prompt for password, mask input with 'x', and authenticate against
    # user record, performing a script change to topscript if successful.
    echo(prompt_pass)
    lne = LineEditor(max_pass)
    lne.hidden = u'x'
    password = lne.read()
    if password is not None and 0 != len(password):
        echo(status_auth)
        if user.auth(password):
            return True
    denied(badpass_msg % (user.handle,))
    return False


def uname():
    """
    On unix systems with uname, call with -a on connect
    """
    from x84.bbs import Door
    for uname_filepath in ('/usr/bin/uname', '/bin/uname'):
        if os.path.exists(uname_filepath):
            Door(uname_filepath, args=('-a',)).run()
            break


def main():
    """ Main procedure. """
    # pylint: disable=R0914,R0911
    #         Too many local variables
    import logging
    from x84.bbs import getsession, getterminal, ini, echo, get_user, goto
    from x84.bbs import find_user, showart
    from x84.engine import __url__ as url
    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    whoami, port = session.sid.split(':')

    if int(port) == 0:
            from x84.bbs.userbase import User

            if whoami == 'msgserve':
                from x84 import msgserve
                session.user = User(u'x84net server')
                session.activity = u'Processing request'
                msgserve.main()
                return
            elif whoami == 'msgpoll':
                from x84 import msgpoll
                session.user = User(u'x84net client')
                session.activity = u'Polling for messages'
                msgpoll.main()
                return

    session.activity = u'Logging in'
    handle = (session.env.get('USER', '').decode('iso8859-1', 'replace'))
    anon_allowed_msg = u"'%s' login enabled.\r\n" % (
        term.bold_cyan('anonymous',))
    newcmds = ini.CFG.get('matrix', 'newcmds').split()
    apply_msg = u"'%s' to create new account.\r\n" % (
        term.bold_cyan(newcmds[0]),)
    allow_apply = ini.CFG.getboolean('nua', 'allow_apply')
    enable_anonymous = ini.CFG.getboolean('matrix', 'enable_anonymous')
    enable_pwreset = ini.CFG.getboolean('matrix', 'enable_pwreset')
    bbsname = ini.CFG.get('system', 'bbsname')
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'xz-1984.ans')
    topscript = ini.CFG.get('matrix', 'topscript')
    max_tries = 10
    session.flush_event('refresh')
    #uname()
    # display banner with amiga topaz encoding
    echo(u''.join((
        term.normal, u'\r\n',
        u'Connected to %s, see %s for source\r\n' % (bbsname, url),)))
    for line in showart(artfile,'topaz'):
        echo(line)
    echo(term.normal)
    echo (u''.join((
        u'\r\n\r\n',
        term.bold(u'tERM'), u': ',
        term.cyan_underline(session.env['TERM']),
        u'\r\n',
        term.bold(u'diMENSiONs'), u': ', '%s%s%s' % (
            term.bold_cyan(str(term.width)),
            term.cyan(u'x'),
            term.bold_cyan(str(term.height)),),
        u'\r\n',
        term.bold(u'ENCOdiNG'), u': ',
        term.cyan_underline(session.encoding),
        u'\r\n\r\n',
        anon_allowed_msg if enable_anonymous else u'',
        apply_msg if allow_apply else u'',
    )))
    # http://www.termsys.demon.co.uk/vtansi.htm
    # disable line-wrapping
    echo(unichr(27) + u'[7l')

    # http://www.xfree86.org/4.5.0/ctlseqs.html
    # Save xterm icon and window title on stack.
    echo(unichr(27) + u'[22;0t')

    if handle:
        echo('\r\nHello, %s!' % (handle,))
        match = find_user(handle)
        if match is not None:
            handle = match
        else:
            handle = ''

    # prompt for username & password
    for _num in range(0, max_tries):
        handle = get_username(handle)
        if handle != u'':
            session.activity = u'Logging in'
            user = get_user(handle)
            if try_pass(user):
                goto(topscript, user.handle)
            echo(u'\r\n\r\n')
            if enable_pwreset:
                try_reset(user)
            else:
                logger.info('%r failed password', handle)
    logger.warn('maximum tries exceeded')
    goto('logoff')
