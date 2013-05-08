"""
 User profile editor script for x/84, http://github.com/jquast/x84
"""


ABOUT_DOT_PLAN = (u'The .plan file is a throwback to early Unix '
                  + u'"blogosphere", this is a simple file that is '
                  + u'GLOBALLY shared with all other users. You can '
                  + u'put anything you want here: something about '
                  + u'yourself and your interests, your websites, '
                  + u'greetz, etc.')

ABOUT_TERM = (u'This only sets TERM for new processes, such as doors. '
              + u'Your bbs session itself discovers TERM only once during '
              + u'telnet negotiation on-connect.')

EXIT = False


def process_keystroke(inp, user):
    """ Process keystroke, ``inp``, for target ``user``. """
    # pylint: disable=R0914,R0912,R0915,R0911,W0603
    #         Too many local variables
    #         Too many branches
    #         Too many statements
    #         Too many return statements
    #         Using the global statement
    # ^ lol, this is one of those things that should be
    #   refactored into smaller subroutines =)
    from x84.bbs import getsession, getterminal, echo, getch, gosub
    from x84.bbs import LineEditor, Ansi
    from x84.default.nua import set_email, set_location
    from x84.bbs.ini import CFG
    def_timeout = CFG.getint('system', 'timeout')
    global EXIT
    session, term = getsession(), getterminal()
    is_self = bool(user.handle == session.user.handle)
    invalid = u'\r\niNVAlid.'
    assert is_self or 'sysop' in session.user.groups

    if is_self and inp in (u'c', u'C'):
        gosub('charset')

    elif is_self and inp in (u't', u'T'):
        echo(term.move(term.height - 1, 0))
        echo(ABOUT_TERM + u'\r\n')
        echo(u'\r\ntERMiNAl tYPE: ')
        term = LineEditor(30, session.env.get('TERM')).read()
        echo(u"\r\n\r\nset TERM to '%s'? [yn]" % (term,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                session.env['TERM'] = term
                break
            elif inp2 in (u'n', u'N'):
                break

    elif is_self and inp in (u'w', u'W'):
        echo(u'\r\ntERMiNAl Width: ')
        width = LineEditor(3, str(term.width)).read()
        try:
            width = int(width)
        except ValueError:
            echo(invalid)
            return True
        if width < 0 or width > 999:
            echo(invalid)
            return True
        echo(u"\r\n\r\nset COLUMNS=%d? [yn]" % (width,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                term.columns = width
                break
            elif inp2 in (u'n', u'N'):
                break

    elif is_self and inp in (u'h', u'H'):
        echo(u'\r\ntERMiNAl hEiGht: ')
        height = LineEditor(3, str(term.height)).read()
        try:
            height = int(height)
        except ValueError:
            echo(invalid)
            return True
        if height < 0 or height > 999:
            echo(invalid)
            return True
        echo(u"\r\n\r\nset LINES=%d? [yn]" % (height,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                term.rows = height
                break
            elif inp2 in (u'n', u'N'):
                break

    elif 'sysop' in session.user.groups and inp in (u'd', u'D',):
        echo(u"\r\n\r\ndElEtE %s ? [yn]" % (user.handle,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user.delete()
                break
            elif inp2 in (u'n', u'N'):
                break
        EXIT = True

    elif 'sysop' in session.user.groups and inp in (u's', u'S',):
        sysop = not 'sysop' in user.groups
        echo(u"\r\n\r\n%s SYSOP ACCESS? [yn]" % (
            'ENAblE' if sysop else 'diSAblE',))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                if sysop:
                    user.groups.add('sysop')
                else:
                    user.groups.remove('sysop')
                user.save()
                break
            elif inp2 in (u'n', u'N'):
                break
    elif inp in (u'p', u'P'):
        from x84.default.nua import set_password
        set_password(user)
        echo(u"\r\n\r\nSEt PASSWORd ? [yn]")
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user.save()
                break
            elif inp2 in (u'n', u'N'):
                break
    elif inp in (u'.',):
        echo(term.move(0, 0) + term.normal + term.clear)
        echo(term.move(int(term.height * .8), 0))
        for line in Ansi(ABOUT_DOT_PLAN).wrap(
                term.width / 3).splitlines():
            echo(line.center(term.width).rstrip() + u'\r\n')
        echo(u'\r\n\r\nPRESS ANY kEY ...')
        getch()
        if is_self:
            gosub('editor', '.plan')
        else:
            tmpkey = '%s-%s' % (user.handle, user.plan)
            draft = user.get('.plan', u'')
            session.user[tmpkey] = draft
            gosub('editor', tmpkey)
            if session.user.get(tmpkey, u'') != draft:
                echo(u"\r\n\r\nSEt .PlAN ? [yn]")
                while True:
                    inp2 = getch()
                    if inp2 in (u'y', u'Y'):
                        user['.plan'] = session.user[tmpkey]
                        break
                    elif inp2 in (u'n', u'N'):
                        break
    elif inp in (u'l', u'L'):
        echo(term.move(term.height - 1, 0))
        set_location(user)
        echo(u"\r\n\r\nSEt lOCAtiON tO '%s'? [yn]" % (user.location,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user.save()
                break
            elif inp2 in (u'n', u'N'):
                break
    elif inp in (u'e', u'E'):
        echo(term.move(term.height - 1, 0))
        set_email(user)
        echo(u"\r\n\r\nSEt EMAil tO '%s'? [yn]" % (user.email,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user.save()
                break
            elif inp2 in (u'n', u'N'):
                break
    elif inp in (u'i', u'I'):
        echo(u'\r\ntiMEOUt (0=NONE): ')
        timeout = LineEditor(6, str(user.get('timeout', def_timeout))).read()
        try:
            timeout = int(timeout)
        except ValueError:
            echo(invalid)
            return True
        if timeout < 0:
            echo(invalid)
            return True
        echo(u"\r\n\r\nSet tiMEOUt=%s? [yn]" % (
            timeout if timeout else 'None',))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user['timeout'] = timeout
                session.send_event('set-timeout', timeout)
                break
            elif inp2 in (u'n', u'N'):
                break

    elif inp in (u'm', u'M'):
        mesg = False if user.get('mesg', True) else True
        echo(u"\r\n\r\n%s iNStANt MESSAGiNG? [yn]" % (
            'ENAblE' if mesg else 'DiSAblE',))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user['mesg'] = mesg
                break
            elif inp2 in (u'n', u'N'):
                break
    elif inp in (u'x', u'X'):
        expert = not user.get('expert', False)
        echo(u"\r\n\r\n%s EXPERt MOdE? [yn]" % (
            'ENAblE' if expert else 'DiSAblE',))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user['expert'] = expert
                break
            elif inp2 in (u'n', u'N'):
                break
    elif inp in (u'q', u'Q',):
        EXIT = True
    else:
        return False
    return True


def dummy_pager(user):
    """ A dummy selector for profile attributes """
    from x84.bbs import getsession, getterminal, echo, Ansi, getch
    session, term = getsession(), getterminal()
    plan = user.get('.plan', False)
    from x84.bbs.ini import CFG
    def_timeout = CFG.getint('system', 'timeout')
    menu = ['(c)%-20s - %s' % (u'hARACtER ENCOdiNG',
                               term.bold(session.encoding),),
            '(t)%-20s - %s' % (u'ERMiNAl tYPE',
                               term.bold(session.env.get('TERM', 'unknown')),),
            '(h)%-20s - %s' % (u'ERMiNAl hEiGht',
                               term.bold(str(term.height)),),
            '(w)%-20s - %s' % (u'ERMiNAl WidtH',
                               term.bold(str(term.width)),),
            '(l)%-20s - %s' % (u'OCAtiON',
                               term.bold(user.location),),
            '(p)%-20s - %s' % (u'ASSWORd',
                               term.bold_black(u'******'),),
            '(e)%-20s - %s' % (u'-MAil AddRESS',
                               term.bold(user.email),),
            (term.bold('t') +
                '(i)%-19s - %s' % (u'MEOUt', term.bold(
                    str(user.get('timeout', def_timeout))),)),
            '(s)%-20s - %s' % (u'YSOP ACCESS',
                               term.bold(u'ENAblEd'
                                         if 'sysop' in user.groups
                                         else 'diSAblEd')),
            '(m)%-20s - %s' % (u'ESG',
                               term.bold(u'[%s]' % ('y'
                                   if user.get(
                                       'mesg', True) else 'n',),)),
            '(.)%-20s - %s' % (u'PlAN filE', '%d bytes' % (
                len(plan),) if plan else '(NO PlAN.)'),
            '(x)%-20s - %s' % (u'PERt MOdE',
                               term.bold(u'ENAblEd'
                                         if user.get('expert', False)
                                         else 'diSAblEd')),
            '(q)Uit', ]
    echo(term.normal + u'\r\n\r\n')
    lines = Ansi('\n'.join(menu)).wrap(term.width).splitlines()
    xpos = max(1, int(term.width / 2) - (40 / 2))
    for row, line in enumerate(lines):
        if row and (0 == row % (term.height - 2)):
            echo(term.reverse(u'\r\n-- More --'))
            getch()
        echo(u'\r\n' + ' ' * xpos + line)
    echo(u'\r\n\r\n Enter option [ctle.xq]: ')
    return process_keystroke(getch(), user)


def main(handle=None):
    """ Main procedure. """
    # pylint: disable=W0603
    #         Using the global statement
    from x84.bbs import getsession, getterminal
    from x84.bbs import get_user
    session, term = getsession(), getterminal()
    user = session.user if ('sysop' not in session.user.groups
            ) or (handle is None) else get_user(handle)
    global EXIT
    while not EXIT:
        session.activity = 'User profile editor'
        dummy_pager(user)
