""" Who's online script for x/84. """
import time
POLL_KEY = 0.25  # blocking ;; how often to poll keyboard
POLL_INF = 2.00  # seconds elapsed until re-ask clients for more details
POLL_AYT = 4.00  # seconds elapsed until global 'are you there?' is checked,
POLL_OUT = 0.50  # seconds elapsed before screen updates


def request_info(sid):
    """ Send info-req event to target session id ``sid``. """
    from x84.bbs import getsession
    session = getsession()
    session.send_event('route', (sid, 'info-req', session.sid,))


def banner():
    """ Returns string suitable for displaying banner """
    from x84.bbs import getterminal, showart
    import os
    term = getterminal()
    banner = '\r\n'
    for line in showart(
            os.path.join(os.path.dirname(__file__), 'art', 'online.ans'), 'cp437'):
        banner = banner + term.move_x(max(0, (term.width / 2) - 40)) + line
    return (banner)


def describe(sessions):
    """
    Returns unicode string suitable for describing the activity of
    session id's of array ``sessions``.
    """
    from x84.bbs import getsession, getterminal, ini
    slen = lambda sessions: len(u'%d' % (len(sessions),))
    session, term = getsession(), getterminal()
    max_user = ini.CFG.getint('nua', 'max_user')

    text = u'\r\n'.join(([u''.join((
        term.move_x(max(0, (term.width / 2) - 40)), term.green,
        u'%*d' % (5 + slen(sessions), node), u' ' * 7, term.normal,
        u'%4is' % (attrs.get('idle', 0),), u' ', u' ' * 8,
        (term.bold_red(u'%-*s' % (max_user, (
            u'** diSCONNECtEd' if 'delete' in attrs
            else attrs.get('handle', u'** CONNECtiNG')),)
        ) if attrs.get('handle', u'') != session.user.handle
            else term.red(u'%-*s' % (max_user, session.user.handle))),
        term.green(u'       '),
        term.yellow((attrs.get('activity', u''))
                    if attrs.get('sid') != session.sid else
                    term.yellow(session.activity)),
    )) for node, (_, attrs) in get_nodes(sessions)]))

    return text + '\r\n'


def get_nodes(sessions):
    """ Given an array of sessions, assign an arbitrary 'node' number """
    return enumerate(sorted(sessions.items()))


def heading():
    """ Return string suitable for display heading. """
    from x84.bbs import getterminal, showart
    import os
    term = getterminal()
    bar = ''
    for line in showart(
            os.path.join(os.path.dirname(__file__), 'art', 'onlinebar.ans'), 'topaz'):
        bar = bar + term.move_x(max(0, (term.width / 2) - 40)) + line
    return u'\r\n'.join((
        u'\r\n'.join([term.center(pline, (term.width))
                      for pline in prompt()]),
        u'\r\n', bar))


def prompt():
    """
    Return string suitable for displaying prompt and available commands.
    """
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    decorate = lambda key, desc: u''.join((
        u'(', term.magenta_underline(key,),
        u')', term.cyan(desc.split()[0]), u' ',
        u' '.join(desc.split()[1:]), u' ',))
    return term.wrap(u''.join((
        u' ' * 2,
        term.green_reverse(':keys'), u' ',
        decorate('c', 'hAt USR'),
        decorate('s', 'ENd MSG'),
        (u''.join((
            decorate('d', 'iSCONNECt SiD'),
            decorate('e', 'diT USR'),
            decorate('v', 'iEW SiD AttRS'),
            u' ',)) if 'sysop' in session.user.groups else u''),
        decorate('Escape/q', 'Uit'),
        decorate('Spacebar', 'REfRESh'),
    )), int(term.width * .8), subsequent_indent=u' ' * 8)


def get_node(sessions):
    """ Prompt user for session node, Returns node & session attributes. """
    from x84.bbs import ini, LineEditor, echo
    max_user = ini.CFG.getint('nua', 'max_user')
    invalid = u'\r\ninvalid.'
    echo(u'\r\n\r\nNOdE: ')
    node = LineEditor(max_user).read()

    if node is None or 0 == len(node):
        # cancel
        return (None, None)

    try:
        node = int(node)
    except ValueError:
        # not an int
        echo(invalid)
        return (None, None)

    for tgt_node, (_, attrs) in get_nodes(sessions):
        if tgt_node == node:
            return (tgt_node, attrs)

    # not found
    echo(invalid)
    return (None, None)


def edit(sessions):
    """ Prompt for node and gosub profile.py script for user of target session.
    """
    from x84.bbs import gosub
    (node, tgt_session) = get_node(sessions)
    if node is not None:
        gosub('profile', handle=tgt_session['handle'])
        return True


def chat(sessions):
    """
    Prompt for node and page target session for chat.
    Sysop will send session id of -1, indicating the chat is forced.
    """
    from x84.bbs import gosub, getsession
    (_, tgt_session) = get_node(sessions)
    if tgt_session and tgt_session['sid'] != getsession().sid:
        gosub('chat', dial=tgt_session['handle'],
              other_sid=tgt_session['sid'])


def view(sessions):
    """
    Prompt for node and view session details of target session.
    """
    from x84.bbs import echo, getterminal
    term = getterminal()
    (node, tgt_session) = get_node(sessions)
    if node is not None:
        maxlen = max([len(key) for key in tgt_session.keys()])
        echo(u''.join((
            u'\r\n\r\n',
            u'\r\n'.join(['%s%s %s' % (
                term.bold('%*s' % (maxlen, key)),
                term.bold_green(':'),
                term.green(str(value)),)
                for key, value in sorted(tgt_session.items())]),
        )))
        return True


def disconnect(sessions):
    """
    Prompt for node and disconnect target session.
    """
    from x84.bbs import getsession
    session = getsession()
    (node, tgt_session) = get_node(sessions)
    if node is not None:
        session.send_event('remote-disconnect', tgt_session['sid'])
        return True


def sendmsg(sessions):
    """
    Prompt for node and gosub 'writemsg' with recipient set to target user.
    """
    from x84.bbs import gosub, Msg
    (node, tgt_session) = get_node(sessions)
    if node is not None:
        msg = Msg()
        msg.recipient = tgt_session['handle']
        msg.tags.add('private')
        gosub('writemsg', msg)
        return True


def main():
    """ Main procedure. """
    # pylint: disable=R0912,R0914,R0915
    #         Too many branches
    #         Too many local variables
    #         Too many statements
    from x84.bbs import getsession, getterminal, getch, echo
    session, term = getsession(), getterminal()
    SELF_ID = session.sid
    ayt_lastfresh = 0

    def broadcast_ayt(last_update):
        """ Globally boradcast 'are-you-there' request. """
        if time.time() - last_update > POLL_AYT:
            session.send_event('global', ('AYT', session.sid,))
            last_update = time.time()
        return last_update

    sessions = dict()
    dirty = time.time()
    cur_row = 0

    while True:
        ayt_lastfresh = broadcast_ayt(ayt_lastfresh)
        inp = getch(POLL_KEY)
        if session.poll_event('refresh') or (
                inp in (u' ', term.KEY_REFRESH, unichr(12))):
            dirty = time.time()
            cur_row = 0
        elif inp in (u'q', 'Q', term.KEY_EXIT, unichr(27)):
            echo(u'\r\n\r\n')
            return
        elif inp in (u'c', 'C'):
            cur_row = 0 if chat(sessions) else cur_row
            dirty = time.time()
        elif inp in (u's', 'S'):
            cur_row = 0 if sendmsg(sessions) else cur_row
            dirty = time.time()
        elif inp is not None and 'sysop' in session.user.groups:
            if inp in (u'e', u'E'):
                cur_row = 0 if edit(sessions) else cur_row
                dirty = time.time()
            elif inp in (u'v', u'V'):
                cur_row = 0 if view(sessions) else cur_row + 3
                dirty = time.time()
            elif inp in (u'd', u'D'):
                disconnect(sessions)
                dirty = time.time()

        # add sessions that respond to AYT
        data = session.poll_event('ACK')
        if data is not None:
            sid, handle = data
            if sid in sessions:
                sessions[sid]['handle'] = handle
            else:
                sessions[sid] = dict((
                    ('handle', handle),
                    ('lastfresh', time.time()),
                    ('lastasked', time.time()),))
                dirty = time.time()
                echo(u'\a')

        # update sessions that respond to info-req
        data = session.poll_event('info-ack')
        if data is not None:
            sid, attrs = data
            if sessions.get(sid, dict()).get('activity') != attrs['activity']:
                # and refresh screen if activity changes
                dirty = time.time()
            sessions[sid] = attrs
            sessions[sid]['lastfresh'] = time.time()

        # update our own session
        sessions[SELF_ID] = session.to_dict()
        sessions[SELF_ID]['lastfresh'] = time.time()

        # request that all sessions update if more stale than POLL_INF,
        # or is missing session info (only AYT replied so far!),
        # or has been displayed as 'Disconnected' (marked for deletion)
        for sid, attrs in sessions.items():
            if sid == SELF_ID:
                continue
            if attrs.get('idle', -1) == -1 or (
                    time.time() - attrs.get('lastfresh', 0) > POLL_INF
                    and time.time() - attrs.get('lastasked', 0) > POLL_INF):
                request_info(sid)
                attrs['lastasked'] = time.time()

        # prune users who haven't responded to AYT
        for sid, attrs in sessions.items():
            if time.time() - attrs['lastfresh'] > (POLL_AYT * 2):
                sessions[sid]['delete'] = 1
                dirty = time.time()

        if dirty is not None and time.time() - dirty > POLL_OUT:
            session.activity = u"Who's Online"
            otxt = describe(sessions)
            olen = len(otxt.splitlines())
            if 0 == cur_row or (cur_row + olen) >= term.height:
                otxt_b = banner()
                otxt_h = heading()
                cur_row = len(otxt_b.splitlines()) + len(otxt_h.splitlines())
                echo(u''.join((otxt_b, '\r\n', otxt_h, u'\r\n', otxt)))
            else:
                echo(u''.join((
                    u'\r\n',
                    '-'.center(term.width).rstrip(),
                    u'\r\n')))
                echo(otxt)
            cur_row += olen
            dirty = None

        # delete disconnected sessions
        for sid, attrs in sessions.items()[:]:
            if attrs.get('delete', 0) == 1:
                del sessions[sid]
