"""
 User profile editor script for x/84, http://github.com/jquast/x84
"""


about_dot_plan = (u'The .plan file is a throwback to early Unix '
                  + u'"blogosphere", this is a simple file that is '
                  + u'GLOBALLY shared with all other users. You can '
                  + u'put anything you want here: something about '
                  + u'yourself and your interests, your websites, '
                  + u'greetz, etc.')


def process_keystroke(lightbar, inp, user):
    from x84.bbs import getsession, getterminal, echo, getch, gosub
    from x84.bbs import LineEditor, Ansi
    from x84.default.nua import set_email, set_location
    session, term = getsession(), getterminal()
    invalid = u'\r\niNVAlid.'
    if lightbar is not None:
        echo(lightbar.process_keystroke(inp))
        if lightbar.moved:
            return False
    if inp in (u'c', u'C') or (inp == term.KEY_ENTER and
                               lightbar is not None and
                               lightbar.selection[0] == u'c'):
        gosub('charset')
        return True
    elif inp in (u't', u'T') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u't'):
        echo(term.move(term.height - 1, 0))
        echo(term.bold(u'\r\n\r\nNOTE: ')
             + u'thiS ONlY SEtS ' + term.bold('TERM')
             + u' fOR NEW PROCESSES, SUCh AS dOORS. '
             + u'YOUR BBS SESSiON itSElf diSCOVERS '
             + term.bold('TERM') + u'ONlY ONCE dURiNG '
             + u'NEGOtiAtiON ON-CONNECt.\r\n')
        echo(u'\r\ntERMiNAl tYPE: ')
        TERM = LineEditor(30, session.env.get('TERM')).read()
        echo(u"\r\n\r\nset TERM to '%s'? [yn]" % (TERM,))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                session.env['TERM'] = TERM
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in (u'w', u'W') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'w'):
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
            ch = getch()
            if str(ch).lower() == 'y':
                term.columns = width
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in (u'h', u'H') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'h'):
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
            ch = getch()
            if str(ch).lower() == 'y':
                term.rows = height
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in (u'l', u'L') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'l'):
        echo(term.move(term.height - 1, 0))
        set_location(user)
        echo(u"\r\n\r\nSEt lOCAtiON tO '%s'? [yn]" % (user.location,))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                user.save()
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in (u'e', u'E') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'e'):
        echo(term.move(term.height - 1, 0))
        set_email(user)
        echo(u"\r\n\r\nSEt EMAil tO '%s'? [yn]" % (user.email,))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                user.save()
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in ('.',) or (inp == term.KEY_ENTER and
                           lightbar is not None and
                           lightbar.selection[0] == u'.'):
        echo(term.move(0, 0) + term.normal + term.clear)
        echo(term.move(int(term.height * .8), 0))
        for line in Ansi(about_dot_plan).wrap(term.width / 3).split('\r\n'):
            echo(line.center(term.width) + u'\r\n')
        echo('\r\n\r\nPRESS ANY kEY ...')
        getch()
        gosub('editor', '.plan')
        return True
    elif inp in (u'm', u'M') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'm'):
        mesg = False if user.get('mesg', True) else True
        echo(u"\r\n\r\n%s iNStANt MESSAGiNG? [yn]" % (
            'enable' if mesg else 'disable',))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                user['mesg'] = mesg
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in (u'x', u'X') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'x'):
        expert = not user.get('expert', False)
        echo(u"\r\n\r\n%s EXPERt MOdE? [yn]" % (
            'enable' if expert else 'disable',))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                user['expert'] = expert
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in ('q',) or (inp == term.KEY_ENTER and
                           lightbar is not None and
                           lightbar.selection[0] == u'q'):
        global EXIT
        EXIT = True
    return False


def dummy_pager(user):
    from x84.bbs import getsession, getterminal, echo, Ansi, getch
    session, term = getsession(), getterminal()
    plan = user.get('.plan', False)
    menu = ['(c)%-20s - %s' % (u'hARACtER ENCOdiNG',
                               term.bold(session.encoding),),
            '(t)%-20s - %s' % (u'ERMiNAl tYPE',
                               term.bold(session.env.get('TERM', 'unknown')),),
            '(l)%-20s - %s' % (u'OCAtiON',
                               term.bold(user.location),),
            '(e)%-20s - %s' % (u'-MAil AddRESS',
                               term.bold(user.email),),
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
    echo(term.move(0, 0) + term.normal + term.clear)
    lines = Ansi('\n'.join(menu)).wrap(term.width).split(u'\r\n')
    xpos = max(1, (term.width / 2) - (40 / 2))
    for row, line in enumerate(lines):
        if row and (0 == row % (term.height - 2)):
            echo(term.reverse(u'\r\n-- More --'))
            getch()
        echo(u'\r\n' + ' ' * xpos + line)
    echo(u'\r\n\r\n Enter option [ctle.xq]: ')
    return process_keystroke(None, getch(), user)


def is_dumb(session, term):
    return (session.env.get('TERM') == 'unknown'
            or session.user.get('expert', False)
            or term.width < 60)


def refresh(lightbar):
    from x84.bbs import getsession, getterminal, echo
    session, term = getsession(), getterminal()
    lightbar.update(((u'c', u'ChARACtER ENCOdiNG',),
                     (u't', u'tERMiNAl tYPE',),
                     (u'h', u'tERMiNAl hEiGht',),
                     (u'w', u'tERMiNAl Width',),
                     (u'l', u'lOCAtiON',),
                     (u'e', u'EMAil',),
                     (u'm', u'MESG',),
                     (u'.', u'.PlAN',),
                     (u'x', u'EXPERt MOdE',),
                     (u'q', u'QUit',)))
    echo(u'\r\n\r\n')
    echo(u'art request...'.center(term.width))
    echo(u'\r\n\r\n')
    echo(term.bold_blue_underline(u'// '))
    echo(u'\r\n' * lightbar.height)
    echo(lightbar.refresh())


def main(handle=None):
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import Lightbar, get_user
    session, term = getsession(), getterminal()
    session.activity = 'Editing profile'
    user = session.user if (
            'sysop' not in session.user.groups) or (handle is None
            ) else get_user(handle)
    global EXIT
    EXIT = False
    lightbar = None
    dirty = True
    while not EXIT:
        if session.poll_event('refresh') or dirty:
            wide = min(60, term.width - 5)
            if is_dumb(session, term):
                dirty = dummy_pager(user)
            else:
                lightbar = Lightbar(height=14, width=wide,
                                    yloc=term.height - 14,
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
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    is_self = bool(user.handle == session.user.handle)
    assert 'sysop' in session.user.groups or is_self
    sel = lightbar.selection[0]
    val = u''
    if sel == 'c':
        val = session.encoding if is_self else u'x'
    elif sel == 't':
        val = session.env.get('TERM', 'unknown') if is_self else u'x'
    elif sel == 'h':
        val = str(term.height)
    elif sel == 'w':
        val = str(term.width)
    elif sel == 'l':
        val = user.location.strip()
        if 'sysop' in session.user.groups:
            postal = user.get('location',dict()).get('postal', u'')
            if 0 != len(postal):
                val += ' - %s' % (postal,)
    elif sel == 'e':
        val = user.email
    elif sel == 'm':
        val = 'y' if user.get('mesg', True) else 'n'
    elif sel == '.':
        plan = user.get('.plan', False)
        val = u'%d bytes' % (len(plan),) if plan else u''
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

