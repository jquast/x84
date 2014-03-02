""" logoff script with 'automsg' for x/84, https://github.com/jquast/x84 """


def main():
    """ Main procedure. """
    # pylint: disable=R0914,R0912
    #         Too many local variables
    #         Too many branches
    from x84.bbs import DBProxy, getsession, getterminal, echo
    from x84.bbs import ini, LineEditor, timeago, Ansi, showcp437
    from x84.bbs import disconnect, getch
    import time
    import os
    session, term = getsession(), getterminal()
    session.activity = 'logging off'
    handle = session.handle if (
        session.handle is not None
    ) else 'anonymous'
    max_user = ini.CFG.getint('nua', 'max_user')
    prompt_msg = u'[spnG]: ' if session.user.get('expert', False) else (
        u'%s:AY SOMEthiNG %s:REViOUS %s:EXt %s:Et thE fUCk Off !\b' % (
        term.bold_blue_underline(u's'), term.blue_underline(u'p'),
        term.blue_underline(u'n'), term.red_underline(u'Escape/g'),))
    prompt_say = u''.join((term.bold_blue(handle),
                           term.blue(u' SAYS WhAt'), term.bold(': '),))
    boards = (('1984.ws', 'x/84 dEfAUlt bOARd', 'dingo',),
              ('htc.zapto.org', 'Haunting the Chapel', 'Mercyful',),
              ('pharcyde.ath.cx', 'Pharcyde BBS', 'Access Denied',),
              ('bloodisland.ph4.se', 'Blood Island', 'xzip',),
              ('ssl.archaicbinary.net', 'Archaic Binary', 'Wayne Smith',),
              ('bbs.godta.com', 'godta', 'sk-5',)
              ,)
    board_fmt = u'%25s %-30s %-15s\r\n'
    goodbye_msg = u''.join((
        term.move(term.height, 0),
        u'\r\n' * 10,
        u'tRY ANOthER fiNE bOARd', term.bold(u':'), u'\r\n\r\n',
        board_fmt % (
            term.underline('host'.rjust(25)),
            term.underline('board'.ljust(30)),
            term.underline('sysop'.ljust(15)),),
        u'\r\n'.join([board_fmt % (
            term.bold(host.rjust(25)),
            term.reverse(board.center(30)),
            term.bold_underline(sysop),)
            for (host, board, sysop) in boards]),
        u'\r\n\r\n',
        term.bold(
            u'back to the mundane world...'),
        u'\r\n',))
    commit_msg = term.bold_blue(
        u'-- !  thANk YOU fOR YOUR CONtRibUtiON, bROthER  ! --')
    write_msg = term.red_reverse(
        u'bURNiNG tO ROM, PlEASE WAiT ...')
    db_firstrecord = ((time.time() - 1984,
                       u'B. b.', u'bEhAVE YOURSElVES ...'),)
    automsg_len = 40
    artfile = os.path.join(os.path.dirname(__file__), 'art', '1984.asc')

    def refresh_prompt(msg):
        """ Refresh automsg prompt using string msg. """
        echo(u''.join((u'\r\n\r\n', term.clear_eol, msg)))

    def refresh_automsg(idx):
        """ Refresh automsg database, display automsg of idx, return idx. """
        session.flush_event('automsg')
        autodb = DBProxy('automsg')
        automsgs = sorted(autodb.values()) if len(autodb) else db_firstrecord
        dblen = len(automsgs)
        # bounds check
        if idx < 0:
            idx = dblen - 1
        elif idx > dblen - 1:
            idx = 0
        tm_ago, handle, msg = automsgs[idx]
        asc_ago = u'%s ago' % (timeago(time.time() - tm_ago))
        disp = (u''.join(('\r\n\r\n',
                          term.bold(handle.rjust(max_user)),
                          term.bold_blue(u'/'),
                          term.blue(u'%*d' % (len('%d' % (dblen,)), idx,)),
                          term.bold_blue(u':'),
                          term.blue_reverse(msg.ljust(automsg_len)),
                          term.bold(u'\\'),
                          term.blue(asc_ago),)))
        echo(u''.join((
            u'\r\n\r\n',
            Ansi(disp).wrap(term.width),
        )))
        return idx

    def refresh_all(idx=None):
        """
        refresh screen, database, and return database index
        """
        echo(u''.join((u'\r\n\r\n', term.clear_eol,)))
        for line in showcp437(artfile):
            echo(line)
        idx = refresh_automsg(-1 if idx is None else idx)
        refresh_prompt(prompt_msg)
        return idx

    idx = refresh_all()
    while True:
        if session.poll_event('refresh'):
            idx = refresh_all()
        elif session.poll_event('automsg'):
            refresh_automsg(-1)
            echo(u'\a')  # bel
            refresh_prompt(prompt_msg)
        inp = getch(1)
        if inp in (u'g', u'G', term.KEY_EXIT, unichr(27), unichr(3),):
            # http://www.xfree86.org/4.5.0/ctlseqs.html
            # Restore xterm icon and window title from stack.
            echo(unichr(27) + u'[23;0t')
            echo(goodbye_msg)
            getch(1.5)
            disconnect('logoff.')
        elif inp in (u'n', u'N', term.KEY_DOWN, term.KEY_NPAGE,):
            idx = refresh_automsg(idx + 1)
            refresh_prompt(prompt_msg)
        elif inp in (u'p', u'P', term.KEY_UP, term.KEY_PPAGE,):
            idx = refresh_automsg(idx - 1)
            refresh_prompt(prompt_msg)
        elif inp in (u's', u'S'):
            # new prompt: say something !
            refresh_prompt(prompt_say)
            msg = LineEditor(width=automsg_len).read()
            if msg is not None and msg.strip():
                echo(u''.join((u'\r\n\r\n', write_msg,)))
                autodb = DBProxy('automsg')
                autodb.acquire()
                idx = max([int(ixx) for ixx in autodb.keys()] or [-1]) + 1
                autodb[idx] = (time.time(), handle, msg.strip())
                autodb.release()
                session.send_event('global', ('automsg', True,))
                refresh_automsg(idx)
                echo(u''.join((u'\r\n\r\n', commit_msg,)))
                getch(0.5)  # for effect, LoL
            # display prompt
            refresh_prompt(prompt_msg)
