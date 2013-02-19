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

def process_keystroke(lightbar, inp, user):
    """ Process keystroke, ``inp``, for target ``user``. """
    # pylint: disable=R0914,R0912,R0915,R0911,W0603
    #         Too many local variables
    #         Too many branches
    #         Too many statements
    #         Too many return statements
    #         Using the global statement
    from x84.bbs import getsession, getterminal, echo, getch, gosub
    from x84.bbs import LineEditor, Ansi
    from x84.default.nua import set_email, set_location
    global EXIT
    session, term = getsession(), getterminal()
    is_self = bool(user.handle == session.user.handle)
    invalid = u'\r\niNVAlid.'
    if lightbar is not None:
        echo(lightbar.process_keystroke(inp))
        if lightbar.moved:
            return False
    assert is_self or 'sysop' in session.user.groups
    if is_self and (
        inp in (u'c', u'C') or (inp == term.KEY_ENTER and
                                   lightbar is not None and
                                   lightbar.selection[0] == u'c')):
            gosub('charset')
    elif is_self and (
        inp in (u't', u'T') or (inp == term.KEY_ENTER and
                                     lightbar is not None and
                                     lightbar.selection[0] == u't')):
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
    elif is_self and (
        inp in (u'w', u'W') or (inp == term.KEY_ENTER and
                                     lightbar is not None and
                                     lightbar.selection[0] == u'w')):
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
    elif is_self and (
            inp in (u'h', u'H') or (inp == term.KEY_ENTER and
                lightbar is not None and
                lightbar.selection[0] == u'h')):
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
    elif ('sysop' in session.user.groups and (
                inp in (u'd', u'D',) or (inp == term.KEY_ENTER and
                    lightbar is not None and
                    lightbar.selection[0] == u'd'))):
        echo(u"\r\n\r\ndElEtE %s ? [yn]" % (user.handle,))
        while True:
            inp2 = getch()
            if inp2 in (u'y', u'Y'):
                user.delete()
                break
            elif inp2 in (u'n', u'N'):
                break
        EXIT = True
    elif 'sysop' in session.user.groups and (
            inp in (u's', u'S',) or (inp == term.KEY_ENTER and
                lightbar is not None and
                lightbar.selection[0] == u's')):
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
    elif inp in (u'p',) or (inp == term.KEY_ENTER and
                           lightbar is not None and
                           lightbar.selection[0] == u'p'):
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
    elif inp in (u'.',) or (inp == term.KEY_ENTER and
                           lightbar is not None and
                           lightbar.selection[0] == u'.'):
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
    elif inp in (u'l', u'L') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'l'):
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
    elif inp in (u'e', u'E') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'e'):
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
    elif inp in (u'm', u'M') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'm'):
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
    elif inp in (u'x', u'X') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'x'):
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
    elif inp in (u'q', u'Q',) or (inp == term.KEY_ENTER and
                           lightbar is not None and
                           lightbar.selection[0] == u'q'):
        EXIT = True
    else:
        return False
    return True


def dummy_pager(user):
    """ A dummy selector for profile attributes """
    from x84.bbs import getsession, getterminal, echo, Ansi, getch
    session, term = getsession(), getterminal()
    plan = user.get('.plan', False)
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
            '(s)%-20s - %s' % (u'YSOP ACCESS',
                               term.bold(u'ENAblEd'
                                         if 'sysop' in user.groups
                                         else 'diSAblEd')),
            '(m)%-20s - %s' % (u'ESG',
                                term.bold(u'[%s]' % ('y'
                                    if user.get('mesg', True) else 'n',),)),
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
    return process_keystroke(None, getch(), user)


def is_dumb(session, term):
    """ Returns true if a dummy pager should be used. """
    return (session.env.get('TERM') == 'unknown'
            or session.user.get('expert', False)
            or term.width < 60)


def refresh(lightbar):
    """ Refresh display. """
    from x84.bbs import getterminal, echo
    term = getterminal()
    lightbar.update(((u'c', u'C.hARACtER ENCOdiNG',),
                     (u't', u't.ERMiNAl tYPE',),
                     (u'h', u'h.EiGht',),
                     (u'w', u'W.idth',),
                     (u'l', u'l.OCAtiON',),
                     (u'p', u'p.ASSWORd',),
                     (u'e', u'E.MAil',),
                     (u's', u'S.YSOP ACCESS',),
                     (u'm', u'M.ESG',),
                     (u'.', u'..PlAN',),
                     (u'x', u'X.PERt MOdE',),
                     (u'q', u'Q.Uit',)))
    echo(u'\r\n\r\n')
    echo(u'art ?!?'.center(term.width))
    echo(u'\r\n\r\n')
    echo(term.bold_blue_underline(u'// '))
    echo(u'\r\n' * lightbar.height)
    echo(lightbar.refresh())


def main(handle=None):
    """ Main procedure. """
    # pylint: disable=W0603
    #         Using the global statement
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import Lightbar, get_user
    session, term = getsession(), getterminal()
    user = session.user if (
            'sysop' not in session.user.groups) or (handle is None
            ) else get_user(handle)
    lightbar = None
    dirty = True
    global EXIT
    EXIT = False
    while not EXIT:
        if session.poll_event('refresh') or dirty:
            session.activity = 'User profile editor'
            wide = min(40, term.width - 5)
            height = 15
            if is_dumb(session, term):
                dirty = dummy_pager(user)
            else:
                lightbar = Lightbar(height=height,
                        width=wide,
                        yloc=term.height - height,
                        xloc=(term.width / 2) - (wide / 2))
                lightbar.alignment = 'center'
                lightbar.ypadding = 2
                lightbar.glyphs['right-vert'] = u''
                lightbar.glyphs['left-vert'] = u''
                lightbar.colors['border'] = term.bold_blue
                lightbar.colors['highlight'] = term.blue_reverse
                refresh(lightbar)
                echo(lborder(lightbar, user))
                dirty = False
        inp = getch(1)
        if inp is not None:
            if is_dumb(session, term):
                dirty = process_keystroke(None, inp, user)
            else:
                dirty = process_keystroke(lightbar, inp, user)
                if lightbar.moved:
                    echo(lborder(lightbar, user))

def lborder(lightbar, user):
    """ Display value of ``lightbar`` selection in border region. """
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    is_self = bool(user.handle == session.user.handle)
    assert 'sysop' in session.user.groups or is_self
    sel = lightbar.selection[0]
    val = u''
    if sel == 'c':
        val = session.encoding if is_self else user.get('charset', u'x')
    elif sel == 't':
        val = session.env.get('TERM', 'unknown') if is_self else u'x'
    elif sel == 'h':
        val = str(term.height) if is_self else u'x'
    elif sel == 'w':
        val = str(term.width) if is_self else u'x'
    elif sel == 'l':
        val = user.location.strip()
        if 'sysop' in session.user.groups:
            postal = user.get('location', dict()).get('postal', u'')
            if 0 != len(postal):
                val += ' - %s' % (postal,)
    elif sel == 'e':
        val = user.email
    elif sel == 'm':
        val = u'y' if user.get('mesg', True) else 'n'
    elif sel == '.':
        plan = user.get('.plan', False)
        val = u'%d bytes' % (len(plan),) if plan else u''
    elif sel == 's':
        val = u'ENAblEd' if 'sysop' in user.groups else (u'diSABlEd')
    elif sel == 'x':
        val = u'ENAblEd' if user.get('expert', False) else (
                u'diSABlEd')
    return u''.join((lightbar.border(),
            lightbar.title(u'- USER PROfilE EditOR -'),
            lightbar.footer(''.join((
                u'- ',
                val[:lightbar.visible_width - 4],
                u' -',))),
            ))
