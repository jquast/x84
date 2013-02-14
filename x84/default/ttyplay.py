""" ttyplay door for x/84, https://github.com/jquast/x84 """

def main(ttyfile=u'', peek=False):
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import Door, ScrollingEditor, Ansi, ini
    import os, re
    TTYPLAY = ini.CFG.get('ttyplay', 'exe')
    if not os.path.exists(TTYPLAY):
        echo(u'\r\n%s not installed.\r\n' % (TTYPLAY,))
        getch()
        return
    session, term = getsession(), getterminal()
    if 'sysop' in session.user.groups:
        folder = os.path.dirname(ttyfile) or session._ttyrec_folder
        se = ScrollingEditor(term.width - 18, term.height - 3, 9)
        se.content = os.path.basename(ttyfile)
        se.enable_scrolling = True
        se.colors['highlight'] = term.blue_reverse
        files = Ansi(u', '.join([fn
            for fn in os.listdir(session._ttyrec_folder)
            if fn.endswith('.ttyrec')])).wrap(term.width)
        echo(u'\r\n\r\n')
        echo(files)
        echo(u'\r\n\r\n')
        echo(term.move(term.height, 1))
        while True:
            echo(term.bold_blue(u'ttyplay: '))
            echo(u'\r\n')
            ttyfile = se.read()
            if (ttyfile is None
                    or 0 == len(ttyfile.strip())
                    or os.path.sep in ttyfile):
                print 'x'
                return
            if not (os.path.exists(os.path.join(folder, ttyfile))
                    and os.path.isfile(os.path.join(folder, ttyfile))):
                echo(term.bold_red('\r\npath not found.\r\n\r\n'))
                continue
            ttyfile = os.path.join(folder, ttyfile)
            break
    if not (os.path.exists(ttyfile) and os.path.isfile(ttyfile)):
        echo(term.bold_red('\r\npath not found: %s\r\n' % (ttyfile,)))
        getch()
        return
    # .. we could look for and write various information headers..
    # .. esp. at EOF, about session.user.handle & connect_time & etc.
    data = open(ttyfile, 'rb').read(64)
    size_pattern = re.compile(r'\[8;\(\d+\);\(\d+\)t')
    match = size_pattern.match(data)
    if match:
        echo(u'\r\n\r\nheight, width: %s, %s' % match.groups())
    args=tuple()
    if peek:
        args += ('-p',)
    args += (ttyfile,)
    print args
    d = Door(TTYPLAY, args=args)
    session.activity = u'playing tty recording'
    resume_rec = session._record_tty and session.is_recording
    if resume_rec:
        session.stop_recording()
        session._record_tty = False
    # press any key prompt, instructions for quitting (^c) ..
    echo(u'\r\n\r\n lOAd CASSEttE ANd PRESS %s. PRESS %s tO %s.\r\n' % (
        term.green_reverse(u'PlAY'),
        term.green_underline('bREAk'),
        term.red_reverse(u'StOP'),))
    getch()
    with term.fullscreen():
        d.run()
        echo(u'\r\n\r\n')
        echo(u'PRESS ANY kEY.')
        getch()
    if not session.is_recording and resume_rec:
        session._record_tty = True
        session.start_recording()
