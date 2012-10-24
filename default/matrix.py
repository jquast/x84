"""
 Matrix login screen for X/84 (Formerly, 'The Progressive') BBS,

 This script is the session entry point.  Or simply put, the login program.

 In legacy era, a matrix script might be something to fool folk not in the
 know, meant to divert agents from underground boards, require a passcode,
 or even swapping the modem into a strange stop/bit/parity configuration,
 callback mechanisms, etc.. read all about it in old e-zines.
"""
__url__ = u'https://github.com/jquast/x84/'

from bbs import *

def denied(msg):
    term = getterminal()
    echo (msg)
    echo (term.normal + u'\r\n\r\n')
    getch (1.0)


def get_username(handle=u''):
    """
    Prompt for a login handle. If unfound, script change to 'nua' when
    allow_apply is enabled (default=yes). Also allow 'anonymous' when enabled
    (default=no). A unicode handle of non-zero length is returned when the
    login handle matches a userbase record.
    """
    term = getterminal ()
    prompt_user = u'\r\n  user: '
    apply_msg = u'\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5
    allow_apply = ini.CFG.getboolean('nua', 'allow_apply')
    allow_anonymous = ini.CFG.getboolean('matrix', 'enable_anonymous')
    newcmds = ini.CFG.get('matrix', 'newcmds').split()
    topscript = ini.CFG.get('matrix', 'topscript')
    denied_msg = u'\r\n\r\nfiRSt, YOU MUSt AbANdON YOUR libERtIES.'
    badanon_msg = u"\r\n  " + term.bright_red + u"'%s' login denied."
    max_user = ini.CFG.getint('nua', 'max_user')
    nuascript = ini.CFG.get('nua', 'script')
    byecmds = ini.CFG.get('matrix', 'byecmds').split()

    echo (prompt_user)
    handle = LineEditor(max_user, handle).read ()
    if handle is None or 0 == len(handle):
        return u''
    elif handle.lower() in newcmds:
        if allow_apply:
            gosub ('nua', u'')
            return u''
        denied (term.bright_red + denied_msg)
        return u''
    elif handle.lower() in byecmds:
        goto ('logoff')
    elif handle.lower() == u'anonymous':
        if allow_anonymous:
            goto (topscript, 'anonymous')
        denied (badanon_msg % (handle,))
        return u''
    u_handle = find_user(handle)
    if u_handle is not None:
        return u_handle # matched
    if allow_apply is False:
        denied (term.bright_red(denied_msg))
        return u''

    echo (apply_msg)
    ynq = getch ()
    if ynq in (u'q', u'Q', term.KEY_EXIT):
        # goodbye
        goto ('logoff')
    elif ynq in (u'y', u'Y'):
        # new user application
        goto (nuascript, handle)
    echo ('\r\n')
    return u''


def try_pass(user):
    session, term = getsession(), getterminal()
    prompt_pass = u'\r\n\r\n  pass: '
    status_auth = u'\r\n\r\n  ' + term.yellow_reverse(u"Encrypting ..")
    topscript = ini.CFG.get('matrix', 'topscript', 'top')
    badpass_msg = (u'\r\n  ' + term.red_reverse +
            u"'%s' login failed." + term.normal)
    max_pass = int(ini.CFG.get('nua', 'max_pass', '32'))
    # prompt for password, disable input tap during, mask input with 'x',
    # and authenticate against user record, performing a script change to
    # topscript if sucessful.
    echo (prompt_pass)

    chk = session._tap_input # <-- save
    session._tap_input = False
    le = LineEditor(max_pass)
    le.hidden = u'x'
    password = le.read ()
    session._tap_input = chk # restore -->

    if password is None or 0 == len(password):
        return

    echo (status_auth)
    if user.auth (password):
        goto (topscript, user.handle)

    # you failed !
    echo ('\r\n\r\n')
    denied (badpass_msg % (user.handle,))
    return

def uname():
    """
    On unix systems with uname, call with -a on connect
    """
    import os
    for uname_filepath in ('/usr/bin/uname', '/bin/uname'):
        if os.path.exists(uname_filepath):
            Door (uname_filepath, args=('-a',)).run()
            break


def main ():
    session, term = getsession(), getterminal()
    handle = (session.env.get('USER', '') .decode('iso8859-1', 'replace'))
    anon_allowed_msg = u"'anonymous' login enabled.\r\n"
    allow_anonymous = ini.CFG.getboolean('matrix', 'enable_anonymous')
    bbsname = ini.CFG.get('system', 'bbsname')
    max_tries = 10

    flushevent ('refresh')
    echo (term.normal + u'\r\nConnected to %s, see %s for source\r\n' % (
        bbsname, __url__))
    uname ()
    echo (u'\r\n')
    if term.width >= 76:
        for line in open('default/art/1984.asc','r'):
            echo (line.rstrip().center(term.width).rstrip() + u'\r\n')
        echo (u'\r\n')
    if session.env.get('TERM') == 'unknown':
        echo (u'! TERM is unknown\r\n\r\n')
    if allow_anonymous:
        echo (anon_allowed_msg)
    for n in range(0, max_tries):
        handle = get_username(handle)
        if handle != u'':
            user = get_user(handle)
            try_pass (user)
            logger.info ('%r failed password', handle)
    logger.info ('maximum tries exceeded')
    goto ('logoff')
