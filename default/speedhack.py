"""
 time-competitive version of nethack, 'speedhack' is offered as a door game,
 as well as 'dopewars'.  This is really just nao's nethack setup
 (telnet alt.nethack.org), but replacing dgamelaunch with x/84. Similarly,
 we offer ttyrec record & playback functionality...

 This is meant to be used as a 'topscript'.

('speedhack' is a varient that only allows the game to be played for a limited
 time before auto-ascending a character. The goal being to plunder as quickly
 as possible. and a lot of wild luck.)
"""

msg_anon_noedit = "'anonymous' not allowed to edit .nethackrc."
editor = '/usr/local/bin/virus'
hackexe = '/nh343/nethack.343-nao'
xlogfile = '/nh343/var/xlogfile'
pattern_resize = r'\033\[8;(\d+);(\d+)t'

def main(handle=None):
    import os
    import re
    import time
    import glob
    import tempfile
    import textwrap
    import requests
    # when used as a 'top' script, 'handle' is passed in as arg1,
    session, term = getsession(), getterminal()

    # when None or anonymous is used, use a default user record
    if handle in (None, u'anonymous'):
        user = User ()
        handle = user.handle
    else:
        # otherwise retrieve from database
        user = getuser(handle)

    # assign the user to this session .. topscript needs to ..
    session.user = user

    # TODO: allow only 1 login per nick, to avoid a malicious persons from
    # somehow recording the top score, but simultaneously showing a crummy
    # session by abusing time conditions of 2 simultanous nethack games,
    # and assumptions made about the latest 'recording',

    # for last callers, really ..
    user.calls += 1
    user.lastcall = time.time()
    user.save ()

    gosub('lc', True)

    gosub('charset')

    def clear():
        echo (u''.join((term.normal, term.normal_cursor, term.clear, u'\r\n')))

    def prompt():
        echo (u'\r\n\r\n [#eupvcosg] > ')

    def refresh():
        " refresh main menu screen "
        session.activity = u'Main Menu'
        clear ()
        showfile (u'art/speedmain.asc')
        # speak session variables as equivalent os environment values
        echo (u'\r\nTERM: %s' % (term.terminal_type,))
        echo (u', LINES: %d' % (term.rows,))
        echo (u', COLUMNS: %d' % (term.columns,))
        prompt ()

    def pak():
        echo (u'\r\n\r\n' + term.normal + u'Press any key...')
        getch ()
        refresh ()

    refresh ()
    while True:
        event, choice = session.read_events('input', 'refresh',
            timeout=int(ini.CFG.get('session', 'timeout')))
        if (None, None) == (event, choice):
            # timeout
            raise ConnectionTimeout, 'timeout at menu prompt'
        elif event == 'refresh':
            # resized window ...  ^L ...
            refresh ()
        elif event == 'input':
            # edit .nethackrc using vi
            if str(choice).lower() == 'e':
                if session.user.handle == u'anonymous':
                    echo (u''.join((u'\r\n', term.bold_red, msg_anon_noedit, temr.normal)))
                    getch (2)
                    prompt ()
                    continue # denied
                fp, tmppath = tempfile.mkstemp ()
                nethackrc = session.user.get('.nethackrc', '')
                length = len(nethackrc)
                if 0 != length:
                    written = 0
                    while written < length:
                        written += os.write (fp, nethackrc[written:])
                os.close (fp)
                lastmod = os.stat(tmppath).st_mtime
                d = Door(editor, args=(tmppath,))
                d._TAP = True
                if 0 == d.run() and os.stat(tmppath).st_mtime > lastmod:
                    # program exited normaly, file has been modified
                    fp = open(tmppath, 'r')
                    session.user.set('.nethackrc', fp.read())
                    fp.close ()
                    session.user.save ()
                os.unlink (tmppath)
                refresh ()

            # download rc file from alt.org
            elif str(choice).lower() == 'd':
                # download .nethackrc from NAO,
                echo (u'\r\nNAO account name: ')
                echo (term.black_on_red + u' '*15 + u'\b'*15)
                nao = readline (15, handle)
                echo (term.normal)
                url = 'http://alt.org/nethack/userdata/%s/%s/%s.nh343rc'  \
                    % (nao[0], nao, nao,)
                if 0 == len(nao.strip()):
                    continue
                r = requests.get (url)
                if r.status_code == 200:
                    session.user.set('.nethackrc', r.content)
                    echo ('\r\n\r\n%d bytes xfered.' % (len(r.content),))
                    session.user.save ()
                else:
                    echo (u'\r\nrequest failed (%s)%s\r\n' \
                        u'using url %s\r\n' % (r.status_code,
                          u':\r\n%r\r\n' % \
                              (r.content[:1500]) if 0 != len(r.content) else '',
                              url,))
                pak ()
                prompt ()

            # play nethack ..
            elif str(choice).lower() == 'p':
                # begin recording to a ttyrec file .. intention is to somehow
                # parse score files and allow users to playback top score sessions ...
                fname_ttyrec = 'speedhack.%s_%d.ttyrec' % (handle, time.time(),)
                d = Door(hackexe, args=('-u', handle,))
                tmpHome = None
                nethackrc = session.user.get('.nethackrc', '')
                # create temporary $HOME with users' .nethackrc
                tmpHome = tempfile.mkdtemp()
                os.environ['HOME'] = tmpHome
                if 0 != len(nethackrc):
                    fp = open(os.path.join(tmpHome, '.nethackrc',), 'w')
                    fp.write (nethackrc)
                    fp.close ()
                # begin nethack recording
                chk = session.is_recording ()
                if chk:
                    session.stop_recording ()
                # begin nethack recording
                session.start_recording (fname_ttyrec)
                d.run () # begin door
                session.stop_recording () # end nethack recording
                if chk:
                    # resume bbs recording, if it were
                    session.start_recording ()
                if tmpHome is not None:
                    os.unlink (os.path.join(tmpHome, '.nethackrc',))
                    os.rmdir (tmpHome)
                pak ()
                refresh ()

            # view high scores ... (and recordings!)
            elif str(choice).lower() == 'v':
                playerBest = dict()
                fp = open(xlogfile, 'r')
                for record in fp.readlines():
                    # xlogfile format key=value:key=value:(...)
                    attrs = dict([keyval.split('=',1) for keyval in record.split(':')])
                    name = attrs['name']
                    pts = int(attrs['points'])
                    if name in playerBest:
                        cmp_pts, cmp_attrs = playerBest[name]
                        if pts > cmp_pts:
                            playerBest[name] = (pts, attrs)
                    else:
                        playerBest[name] = (pts, attrs)
                byPts = [(pts, (name, attrs,),) \
                    for name, (pts, attrs) in playerBest.items()]
                byPts.sort ()
                byPts.reverse ()
                echo (u'\r\n\r\nNo  Points')
                def find_recording(attrs):
                    cmp_diff = 10
                    ttyrec_folder = abspath(os.path.join('..',session._ttyrec_folder))
                    g_pattern = '%s/speedhack.%s_*.ttyrec.0' % (
                        ttyrec_folder, attrs['name'])
                    r_pattern = re.compile('%s/speedhack.%s_(\d+).ttyrec.0' % ( \
                        ttyrec_folder, attrs['name']))
                    stime = int(attrs['starttime'])
                    l = [] # closest match ... has been ~3s difference ..
                    for fp in glob.glob(g_pattern):
                        x = int(r_pattern.match(fp).groups()[0]) -stime
                        if x < 0: x *= -1
                        l.append ((x, fp,))
                    l.sort()
                    diff, fp = l[0]
                    for diff, rm_fp in l[1:]:
                        logger.info ('removing unused ttyrec: %s', rm_fp)
                        os.unlink (rm_fp) # delete recordings not used in high score ..
                    return fp
                recordings = dict ()
                for n, (points, (name, attrs)) in enumerate(byPts):
                    idx = n +1
                    line_1 = u'%-2d %7d %s%-15s%s' % \
                        (idx, points, term.bold_red, name, term.normal,)
                    parawidth = term.columns - ansilen(line_1) -8
                    paragraph = textwrap.wrap(u'%s-%s-%s-%s %s on level %s%s.\r\n' % (
                        attrs['role'], attrs['race'], attrs['gender'], attrs['align'],
                        attrs['death'].title(), attrs['deathlev'],
                        u' (max %s)'%(attrs['maxlvl']) \
                            if int(attrs['maxlvl']) > int(attrs['deathlev']) \
                            else u'',), parawidth)
                    echo (u'\r\n%s' % (line_1,))
                    echo ((u'\r\n%s' % (u' '*ansilen(line_1))).join \
                        ([p.ljust(parawidth) for p in paragraph]))
                    if idx >= (term.rows/3) -3:
                        break
                    fp = find_recording(attrs)
                    if fp is not None:
                        recordings[idx] = fp
                    data = open(fp).read(100)
                    match = re.search(re.compile(pattern_resize),data)
                    if match is not None:
                        h, w = match.groups()
                        w_color = term.red if int(w) > term.columns else term.bold_white
                        h_color = term.red if int(h) > term.lines else term.bold_white
                        echo (u''.join((term.normal, u'[', w_color, str(w),
                          term.normal, u'x', h_color, str(h), term.normal, u']',)))

                if 0 == len(recordings):
                    pak ()
                    continue # no recordings; refresh
                echo (u'\r\nEnter No. to playback recording: ')
                idx = readline (3, )
                if 0 == len(idx):
                    refresh ()
                    continue # no input; refresh
                try:
                    idx = int(idx)
                except ValueError:
                    refresh ()
                    continue # invalid entry; refresh
                if not idx in recordings:
                    refresh ()
                    continue # not found; refresh
                Door('/usr/bin/ttyplay', args=(recordings[idx],)).run ()
                pak ()
                refresh ()

            # play dopewars!
            elif str(choice) == '#':
                # check if server is already running ...
                pidfile = ini.CFG.get('dopewars', 'pidfile')
                running = False
                if os.path.exists(pidfile):
                    # str->int->str, sanitize input
                    pid = str(int(open(pidfile).read().strip()))
                    d = Door('/bin/ps', args=('-p', pid,))
                    running = bool(0 == d.run())
                if running == False:
                    scorefile = ini.CFG.get('dopewars', 'scorefile')
                    logfile = ini.CFG.get('dopewars', 'logfile')
                    echo (u'\r\n\r\nLaunching dopewars server,\r\n')
                    os.spawnl(os.P_NOWAIT, '/usr/local/bin/dopewars',
                            'dopewars',
                            '--private-server',
                            '--hostname=127.0.0.1',
                            '--port=60387',
                            '--scorefile=%s' % (scorefile,),
                            '--pidfile=%s' % (pidfile,),
                            '--logfile=%s' % (logfile,),)
                else:
                    echo (u'\r\n\r\ndopewars server already running,\r\n')
                if session.user.is_sysop:
                    pak ()
                echo (u'\r\n\r\nLaunching dopewars client,\r\n')
                # HACK -- send input to program game; avoids requiring .cfg file :P
                # anykey;connect;accept localhost;accept port
                session.enable_keycodes = False
                session._buffer_event('input', 'Xc\015\015')
                d = Door('/usr/local/bin/dopewars', args=( \
                    '--scorefile=%s' % (ini.CFG.get('dopewars', 'scorefile'),),
                    '--hostname=127.0.0.1', '--port=60387',
                    '--text-client', '--player=%s' % (handle,),))
                res = d.run ()
                session.enable_keycodes = True
                if (0 != res):
                    echo (u'\r\nExit: %s' % (res,))
                    pak ()
                refresh ()

            # change TERM type ...
            elif str(choice).lower() == 'u':
                gosub ('charset')
                pak ()
                refresh ()

            # change TERM type ...
            elif str(choice).lower() == 'c':
                echo (u'\r\n TERM: ')
                TERM = readline (30).strip()
                echo (u"\r\n set TERM to '%s'? [yn]" % (TERM,))
                while True:
                    ch = getch()
                    if str(ch).lower() == 'y':
                        term.terminal_type = TERM
                        break
                    elif str(ch).lower() == 'n':
                        break
                prompt ()

            elif str(choice).lower() == 'l':
                gosub ('default/lc')
                refresh ()

            elif str(choice).lower() == 'o':
                gosub ('default/ol')
                refresh ()

            elif str(choice).lower() == 's':
                gosub ('default/si')
                refresh ()

            elif str(choice).lower() == 'g':
                goto ('default/logoff')

            elif str(choice) == '*' and session.user.is_sysop:
                # debug: reload self
                goto ('default/speedhack', handle)

            elif str(choice) == '/':
                gosub ('default/torus')
                refresh ()

            elif str(choice) == 'x':
                gosub ('bbslist')
                refresh ()
