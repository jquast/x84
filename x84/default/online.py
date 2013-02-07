""" Who's online script for X/84, https://github.com/jquast/x84 """

# TODO: like 'iostat', only show prompt & headings once per screenful,
# and of course, bake in various functionality like disconnect, chat

import time
SELF_ID = -1


def request_info(session_ids):
    # send individual info-req messages
    from x84.bbs import getsession
    session = getsession()
    for sid in session_ids:
        session.send_event('route', (sid, 'info-req', session.sid,))


def main(login_handle=None):
    from x84.bbs import getsession, getterminal, getch, echo
    session, term = getsession(), getterminal()
    session.activity = u"Who's Online"
    poll_ayt = 5
    fresh = 10
    ayt_lastfresh = time.time()
    def broadcast_AYT(last_update):
        # broadcast are-you-there
        if time.time() - last_update > poll_ayt:
            session.send_event('global', 'AYT')
            last_update = time.time()
        return last_update

    echo(u'\r\n\r\n')
    echo(u''.center((term.width / 2) - 3))
    echo(term.underline('...'))
    echo(term.bold_green(" whO'S ONliNE"))
    echo(u'\r\n\r\n')

    sessions = dict()
    dirty = True
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
                print 'ACK dupe'
                sessions[sid]['handle'] = handle
            else:
                print 'NEW user'
                sessions[sid] = dict((
                    ('handle', handle),
                    ('lastfresh', time.time()),))
                dirty = True

        # update sessions that respond to info-req
        data = session.poll_event('info-ack')
        if data is not None:
            print 'got info', data
            sid, attrs = data
            if sessions.get(sid, dict()).get('activity') != attrs['activity']:
                print 'new activity'
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
            if time.time() - attrs['lastfresh'] > fresh:
                print 'delete', time.time() - attr['lastfresh'], fresh
                del sessions[sid]
                dirty = True

        if dirty:
            refresh(sessions)
            dirty = False

def refresh(sessions):
    from x84.bbs import getsession, getterminal, ini, echo, Ansi
    session, term = getsession(), getterminal()
    decorate = lambda key, desc: u''.join((
        term.green(u'('), term.green_underline(key,),
        term.green(u')'), term.bold(desc.split()[0]),
        u' '.join(desc.split()[1:]),
        u' ',))
    echo(u'\r\n\r\n')
    for idx, (sid, attrs) in enumerate(sorted(sessions.items())):
        echo(u''.join((
            term.green(u'[ '),
            term.bold_green('%*d' % (len(u'%d' % (len(sessions),)), idx,)),
            term.green(u' ]'),
            '%4is idle' % attrs.get('idle', 0),
            term.bold_green(': '),
            term.bold('%-*s' % (
                ini.CFG.getint('nua', 'max_user'),
                attrs.get('handle', u''))),
            term.green(u' - '),
            attrs.get('activity', u''),
            u'\r\n',
            )))
    echo(u'\r\n')
    if 'sysop' in session.user.groups:
        echo(Ansi(u''.join(((u' '),
            decorate('c', 'hAt'),
            decorate('p', 'lAYbACk'),
            decorate('w', 'AtCh'),
            decorate('d', 'iSCONNECt'),
            decorate('s', 'ENd MSG'),
            decorate('e', 'diT USR'),
            decorate('Escape/q', 'Uit'),
            decorate('Spacebar', 'REfRESh'),
            term.green_reverse(':'),
            u' ',
            ))).wrap(term.width))
    else:
        echo(Ansi(u''.join(((u' '),
            decorate('c', 'hAt'),
            decorate('s', 'ENd MSG'),
            decorate('Escape/q', 'Uit'),
            decorate('Spacebar', 'REfRESh'),
            term.green_reverse(':'),
            u' ',
            ))).wrap(term.width))
