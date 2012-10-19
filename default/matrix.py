"""
 Matrix login screen for X/84 (Formerly, 'The Progressive') BBS,

    https://github.com/jquast/x84/

 This script is the session entry point.

 In legacy era, a matrix script might be something to fool folk not in the
 know, meant to divert agents from underground boards, require a passcode,
 or even swapping the modem into a strange stop/bit/parity configuration,
 callback mechanisms, etc.. read all about it in old e-zines.

 Or simply, "login" program. thats what we do here.
"""
__url__ = u'https://github.com/jquast/x84/'
TIMEOUT = 45
CH_MASK_PASSWD = u'x'

def main ():
    import sys
    import os

    session, term = getsession(), getterminal()

    denied_msg = u'\r\n\r\nfiRSt, YOU MUSt AbANdON YOUR libERtIES.'
    apply_msg = u'\r\n\r\n  --> Create new account? [ynq]   <--' + '\b'*5
    prompt_user = u'\r\n  user: '
    prompt_pass = u'\r\n\r\n  pass: '
    badpass_msg = u"\r\n  " + term.red_reverse + u"'%s' login failed."
    badanon_msg = u"\r\n  " + term.bright_red + u"'%s' login denied."
    anon_allowed_msg = u"'anonymous' login enabled.\r\n"
    # NEW_ENVIRON negotiation with telnetd often succeeds to get USER
    handle = (session.env.get('USER', '')
            .decode('iso8859-1', 'replace'))
    byecmds = ini.cfg.get('matrix', 'byecmds', 'bye').split()
    newcmds = ini.cfg.get('matrix', 'newcmds', 'new apply').split()
    max_user = int(ini.cfg.get('nua', 'max_user', '8'))
    max_pass = int(ini.cfg.get('nua', 'max_pass', '32'))
    allow_apply = ini.cfg.get('nua', 'allow_apply') in ('yes',)
    allow_anonymous = ini.cfg.get('matrix', 'enable_anonymous') == 'yes'
    topscript = ini.cfg.get('matrix', 'topscript', 'top')
    nuascript = ini.cfg.get('nua', 'script', 'nua')
    bbsname = ini.cfg.get('system', 'bbsname', 'x/84')
    # this 'animation' displayed while authenticating password ..
    # ( which takes a long time )
    status_auth = ''.join((
        term.move (0, 0) + term.clear + term.bright_cyan + u'\033#8',
        term.move (max(0, (term.height / 2) - 1),
            max(0, (term.width / 2) - 10),), u' ' * 20,
        term.move (max(0, (term.height / 2)),
            max(0, (term.width / 2) - 10),), 'encrypting ...'.center (20),
        term.move (max(0, (term.height / 2) + 1),
            max(0, (term.width / 2) - 10),), u' ' * 20,))

    def redraw ():
        flushevent ('refresh')
        echo (term.normal)
        echo (u'\r\nConnected to %s, see %s for source\r\n' % (
            bbsname, __url__))
        for uname in ('/usr/bin/uname', '/bin/uname'):
            if os.path.exists(uname):
                Door (uname, args=('-a',)).run()
                break
        echo (u'\r\n')
        showfile('art/1984.asc')
        echo (u'\r\n')
        if allow_anonymous:
            echo (anon_allowed_msg)
        echo (term.normal_cursor)

    def denied(msg):
        echo (msg)
        echo (term.normal + u'\r\n\r\n')
        getch (1.0)

    redraw ()
    tries = 0
    while tries < 10:
        tries += 1
        session.activity = u'logging in'
        echo (prompt_user)
        handle = LineEditor(max_user).read ()
        if handle is None or 0 == len(handle):
            continue

        if handle.lower() in newcmds:
            if allow_apply:
                # 'new' in your language ..
                gosub ('nua', u'')
                redraw ()
                continue
            else:
                # applications are denied
                denied (term.bright_red + denied_msg)
                handle = u''
                continue

        elif handle in byecmds:
            goto ('logoff')

        if handle.lower() == 'anonymous':
            if allow_anonymous:
                goto (topscript, 'anonymous')
            denied (badanon_msg % (handle,))
            getch (0.8)
            handle = ''
            continue

        if not DBProxy('userbase').has_key (handle):
            # who are you?
            if allow_apply is False:
                # applications are denied
                denied (term.bright_red + denied_msg)
                getch (0.8)
                handle = u''
                continue
            echo (apply_msg)
            ynq = getch ()
            if ynq in (u'q', u'Q', term.KEY_EXIT):
                # goodbye
                goto ('logoff')
            elif ynq in (u'y', u'Y'):
                # new user application
                goto (nuascript, handle)
            continue

        # authenticate, disable input tap during password input.
        echo (prompt_pass)
        chk = session._tap_input # <-- save
        session._tap_input = False
        le = LineEditor(max_pass)
        le.hidden = u'x'
        password = le.read ()
        session._tap_input = chk # restore -->

        # check password
        if password is None or 0 == len(password):
            continue
        echo (status_auth)
        if authuser(handle, password):
            goto (topscript, handle)

        # you failed !
        echo (term.clear + '\r\n')
        denied (badpass_msg % (handle,))
        redraw ()

    # maximum tries, goodbye. this is used to prevent some simple dos
    # such as netcat host port < /dev/urandom
    goto ('logoff')
