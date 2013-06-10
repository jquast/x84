""" ttyplay door for x/84, https://github.com/jquast/x84 """
import os

def playfile(ttyplay_exe, ttyfile, peek=False):
    from x84.bbs import getsession, getterminal, echo, getch, Door
    import re
    session, term = getsession(), getterminal()
    echo(term.move(term.height, 0) + '\r\n' * term.height)
    if not (os.path.exists(ttyfile) and os.path.isfile(ttyfile)):
        echo(term.bold_red('PAth NOt fOUNd: %s\r\n' % (ttyfile,)))
        getch()
        return

    # .. we could look for and write various information headers..
    # .. esp. at EOF, about session.user.handle & connect_time & etc.
    data = open(ttyfile, 'rb').read(64)
    size_pattern = re.compile(r'\[8;(\d+);(\d+)t')
    match = size_pattern.findall(data)
    for height, width in match:
        echo(u'height, width: %s, %s' % (height, width,))
        break
    args = tuple()
    if peek:
        args += ('-p',)
    elif 'sysop' in session.user.groups:
        echo("\r\nPRESS '%s' tO PEEk (2)\b\b" % (
            (term.green_underline(u'p'),)))
        if getch(2) in (u'p', u'P'):
            peek = True
    args += (ttyfile,)
    door = Door(ttyplay_exe, args=args)
    session.activity = u'playing tty recording'
    # press any key prompt, instructions for quitting (^c) ..
    echo(u'\r\n\r\n lOAd CASSEttE ANd PRESS %s. PRESS %s tO %s.\r\n' % (
        term.green(u'PlAY'),
        term.red_reverse('^c'),
        term.red_underline(u'StOP'),))
    getch(2)
    with term.fullscreen():
        door.run()
        echo(u'\r\n' * term.height)
        echo(u'PRESS ' + term.green_underline('q') + u'.')
        while not getch() in (u'q', u'Q'):
            pass

def main(ttyfile=u'', peek=False):
    """ Main procedure. """
    from x84.bbs import Lightbar, getch, getsession, getterminal, ini, echo
    # pylint: disable=R0914,R0915
    #         Too many local variables
    #         Too many statements
    ttyplay_exe = ini.CFG.get('ttyplay', 'exe')
    if not os.path.exists(ttyplay_exe):
        echo(u'\r\n%s NOt iNStAllEd.\r\n' % (ttyplay_exe,))
        getch()
        return
    session, term = getsession(), getterminal()
    # pylint: disable=W0212
    #         Access to a protected member _record_tty of a client class
    resume_rec = session._record_tty and session.is_recording
    if resume_rec:
        session.stop_recording()
        session._record_tty = False

    if 'sysop' in session.user.groups and ttyfile == u'':
        # pylint: disable=W0212
        #         Access to a protected member _ttyrec_folder of a client class
        folder = os.path.dirname(ttyfile) or session._ttyrec_folder
        pos = None
        while True:
            files = sorted([fn for fn in os.listdir(session._ttyrec_folder)
                            if fn.endswith('.ttyrec')])
            echo(u'\r\n' * term.height)
            sel = Lightbar(term.height - 1, term.width - 1, 0, 0)
            sel.colors['border'] = term.bold_green
            echo(sel.border() + sel.title('-  SElECt A RECORdiNG  -'))
            sel.update([(fname, fname) for fname in files])
            if pos is not None:
                sel.position = pos

            x_ttyfile = sel.read()
            if x_ttyfile is None or sel.quit:
                break
            pos = sel.position
            ttyfile = os.path.join(folder, x_ttyfile)
            playfile(ttyplay_exe, ttyfile, peek)
    else:
        playfile(ttyplay_exe, ttyfile, peek)

    if not session.is_recording and resume_rec:
        session._record_tty = True
        session.start_recording()

    echo(term.move(term.height, 0))
    echo(u'\r\n')

