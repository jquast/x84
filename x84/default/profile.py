"""
 User profile editor script for x/84, http://github.com/jquast/x84
"""


about_dot_plan = (u'The .plan file is a throwback to early Unix '
                  + u'"blogosphere", this is a simple file that is '
                  + u'GLOBALLY shared with all other users. You can '
                  + u'put anything you want here: something about '
                  + u'yourself and your interests, your websites, '
                  + u'greetz, etc.')


def process_keystroke(lightbar, inp):
    from x84.bbs import getsession, getterminal, echo, getch, gosub
    from x84.bbs import LineEditor, Ansi
    from x84.default.nua import set_email, set_location
    session, term = getsession(), getterminal()
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
    elif inp in (u'l', u'L') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'l'):
        echo(term.move(term.height - 1, 0))
        set_location(session.user)
        echo(u"\r\n\r\nSEt lOCAtiON tO '%s'? [yn]" % (session.user.location,))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                session.user.save()
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in (u'e', u'E') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'e'):
        echo(term.move(term.height - 1, 0))
        set_email(session.user)
        echo(u"\r\n\r\nSEt EMAil tO '%s'? [yn]" % (session.user.email,))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                session.user.save()
                break
            elif str(ch).lower() == 'n':
                break
        return True
    elif inp in ('.',) or (inp == term.KEY_ENTER and
                           lightbar is not None and
                           lightbar.selection[0] == u'.'):
        echo(term.move(0, 0) + term.normal + term.clear)
        echo(term.move((term.height / 3), 0))
        for line in Ansi(about_dot_plan).wrap(term.width / 2).split('\r\n'):
            echo(line.center(term.width) + u'\r\n')
        echo('\r\n\r\nPRESS ANY kEY ...')
        getch()
        gosub('editor', '.plan')
        return True
    elif inp in (u'x', u'X') or (inp == term.KEY_ENTER and
                                 lightbar is not None and
                                 lightbar.selection[0] == u'x'):
        expert = not session.user.get('expert', False)
        echo(u"\r\n\r\n%s EXPERt MOdE? [yn]" % (
            'enable' if expert else 'disable',))
        while True:
            ch = getch()
            if str(ch).lower() == 'y':
                session.user['expert'] = expert
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


def dummy_pager():
    from x84.bbs import getsession, getterminal, echo, Ansi, getch
    session, term = getsession(), getterminal()
    plan = session.user.get('.plan', False)
    menu = ['(c)%-20s - %s' % (u'hARACtER ENCOdiNG',
                               term.bold(session.encoding),),
            '(t)%-20s - %s' % (u'ERMiNAl tYPE',
                               term.bold(session.env.get('TERM', 'unknown')),),
            '(l)%-20s - %s' % (u'OCAtiON',
                               term.bold(session.user.location),),
            '(e)%-20s - %s' % (u'MAil AddRESS',
                               term.bold(session.user.email),),
            '(.)%-20s - %s' % (u'PlAN filE', '%d bytes' % (
                len(plan),) if plan else '(NO PlAN.)'),
            '(x)%-20s - %s' % (u'PERt MOdE',
                               term.bold(u'ENAblEd'
                                         if session.user.get('expert', False)
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
    return process_keystroke(None, getch())


def is_dumb(session, term):
    return (session.env.get('TERM') == 'unknown'
            or session.user.get('expert', False)
            or term.width < 78 or term.height < 20)


def refresh(lightbar):
    from x84.bbs import getsession, getterminal, echo
    session, term = getsession(), getterminal()
    echo(term.move(0, 0) + term.normal + term.clear)
    echo(u'\r\n\r\n')
    echo(u'USER PROfilE EditOR'.center(term.width))
    echo(u'\r\n\r\n')
    lightbar.update(((u'c', u'ChARACtER ENCOdiNG',),
                     (u't', u'tERMiNAl tYPE',),
                     (u'l', u'lOCAtiON',),
                     (u'e', u'EMAil',),
                     (u'.', u'.PlAN',),
                     (u'x', u'EXPERt MOdE',),
                     (u'q', u'QUit',)))
    lightbar.colors['border'] = term.bold_green
    echo(lightbar.border() + lightbar.refresh())


def main():
    from x84.bbs import getsession, getterminal, Lightbar, getch
    session, term = getsession(), getterminal()
    global EXIT
    EXIT = False
    lightbar = Lightbar(9, 25,
                        (term.height / 2) - (9 / 2),
                        (term.width / 2) - (20 / 2))
    lightbar.alignment = 'center'
    dirty = True
    inp = None
    while not EXIT:
        if dirty or session.poll_event('refresh'):
            if is_dumb(session, term):
                dirty = dummy_pager()
            else:
                refresh(lightbar)
                dirty = False
            continue
        inp = getch(1)
        if inp is not None:
            dirty = process_keystroke(
                lightbar if not is_dumb(session, term) else None,
                inp)
