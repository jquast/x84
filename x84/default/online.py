""" Who's online script for X/84, https://github.com/jquast/x84 """
import time
SELF_ID = -1
# slen: returns terminal width of ascii representation of #sessions
slen = lambda sessions: len(u'%d' % (len(sessions),))

def request_info(session_ids):
    # send individual info-req messages
    from x84.bbs import getsession
    session = getsession()
    for sid in session_ids:
        session.send_event('route', (sid, 'info-req', session.sid,))


def banner():
    from x84.bbs import getterminal
    term = getterminal()
    return u''.join((
        u''.center((term.width / 2) - 3),
        term.green_underline('.'),
        term.green_bold_underline('.'),
        term.underline('.'),
        term.bold_green(" whO'S ONliNE"),))


def main(login_handle=None):
    from x84.bbs import getsession, getterminal, getch, echo
    session, term = getsession(), getterminal()
    session.activity = u"Who's Online"
    poll_ayt = 5
    fresh = 1
    ayt_lastfresh = 0
    def broadcast_AYT(last_update):
        # broadcast are-you-there
        if time.time() - last_update > poll_ayt:
            session.send_event('global', 'AYT')
            last_update = time.time()
        return last_update

    sessions = dict()
    dirty = True
    cur_row = 0
    while True:
        ayt_lastfresh = broadcast_AYT(ayt_lastfresh)
        inp = getch(0.5)
        if session.poll_event('refresh') or (
                inp in (u' ', term.KEY_REFRESH, unichr(12))):
            dirty = True
        if inp in (u'q', 'Q', term.KEY_EXIT, unichr(27)):
            return

        # add sessions that respond to AYT
        data = session.poll_event('ACK')
        if data is not None:
            sid, handle = data
            if sid in sessions:
                sessions[sid]['handle'] = handle
            else:
                sessions[sid] = dict((
                    ('handle', handle),
                    ('lastfresh', time.time()),))
                dirty = True

        # update sessions that respond to info-req
        data = session.poll_event('info-ack')
        if data is not None:
            sid, attrs = data
            if sessions.get(sid, dict()).get('activity') != attrs['activity']:
                # and refresh screen if activity changes
                dirty = True
            sessions[sid] = attrs
            sessions[sid]['lastfresh'] = time.time()

        # update our own session
        sessions[SELF_ID] = session.info()
        sessions[SELF_ID]['lastfresh'] = time.time()

        # request that all sessions update if more stale than poll_ayt,
        # or is missing session info (only AYT replied so far!)
        request_info(set([key for key, attr in sessions.items()
            if time.time() - attr['lastfresh'] > poll_ayt
            or attr.get('idle', -1) == -1]) ^ set([-1]))

        # prune users who haven't responded to AYT
        for sid, attrs in sessions.items()[:]:
            if time.time() - attrs['lastfresh'] > (poll_ayt * 2):
                del sessions[sid]
                dirty = True

        if dirty:
            otxt = update(sessions)
            olen = len(otxt.splitlines())
            if 0 == cur_row or (cur_row + olen) >= term.height:
                otxt_b = banner()
                otxt_h = heading(sessions)
                cur_row = len(otxt_b.splitlines()) + len(otxt_h.splitlines())
                echo(u'\r\n'.join((u'\r\n\r\n', otxt_b, otxt_h, otxt)))
            else:
                echo(u''.join((
                    u'\r\n',
                    '-'.center(term.width).rstrip(),
                    u'\r\n')))
                echo(otxt)
            cur_row += olen
            dirty = False

def update(sessions):
    from x84.bbs import getsession, getterminal, ini
    session, term = getsession(), getterminal()
    max_user = ini.CFG.getint('nua', 'max_user')
    return u'\r\n'.join(([u''.join((
            u'%*d' % (4 + slen(sessions), node),
            u'%4is' % (attrs.get('idle', 0),), u' ',
            u'%-*s' % (max_user, (
                attrs.get('handle', u'** Connecting')
                if attrs.get('handle') != session.user.handle
                else session.user.handle),),
            term.green(u' - '),
            term.bold_green((attrs.get('activity', u''))
                if attrs.get('handle') != session.user.handle else
                session.activity),
            )) for node, (sid, attrs) in get_nodes(sessions)]))


def get_nodes(sessions):
    return enumerate(sorted(sessions.items()))


def heading(sessions):
    from x84.bbs import getsession, getterminal, ini
    session, term = getsession(), getterminal()
    max_user = ini.CFG.getint('nua', 'max_user')
    return u'\r\n'.join((
        u'\r\n'.join([pline.center(term.width)
            for pline in prompt().splitlines()]),
        u'\r\n',
        term.green_underline(u''.join((
            'node'.rjust(4 + slen(sessions)),
            'idle'.rjust(5),
            ' handle'.ljust(max_user + 3),
            'activity',))),))

def prompt():
    from x84.bbs import getsession, getterminal, Ansi
    session, term = getsession(), getterminal()
    decorate = lambda key, desc: u''.join((
        u'(', term.green_underline(key,),
        u')', term.reverse_green(desc.split()[0]), u' ',
        u' '.join(desc.split()[1:]), u' ',))
    return Ansi(u''.join((
        term.green_reverse(':keys'), u' ',
        decorate('c', 'hAt USR'),
        decorate('s', 'ENd MSG'),
        (u''.join((
        decorate('p', 'lAYbACk REC'),
        decorate('w', 'AtCh liVE'),
        decorate('d', 'iSCONNECt SiD'),
        decorate('e', 'diT USR'),
        decorate('v', 'iEW SiD AttRS'),
        u' ',)) if 'sysop' in session.user.groups else u''),
        decorate('Escape/q', 'Uit'),
        decorate('Spacebar', 'REfRESh'),
        ))).wrap(int(term.width * .7))
