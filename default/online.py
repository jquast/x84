"""
Whos online script for X/84, http://1984.ws
$Id: wfc.py,v 1.2 2010/01/01 09:26:35 dingo Exp $

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

import time
#deps = ['bbs']

def main(login_handle=None):
    session = getsession()
    session.activity = 'WFC screen'
    user = getuser(session.handle)

    # retrieve local user record (for WFC settings)
    if user.has_key('screen delay'):
        delay = user.get('screen delay')
    else: delay = 10
    if user.has_key('blank timeout'):
        blank = user.get('blank timeout')
    else: blank = 1800
    lastfresh = time.time()
    session = getsession()
    isSysop = 'sysop' in user.groups

    SYSTEM, SESSIONS = 1,2

    def refresh(clist=None, info=None, mode=SYSTEM):
        echo (color() + cls() + cursor_hide())
        showcp437 ('art/wfc.ans')
        session.activity = 'WFC screen'
        flushevent('refresh')

        info=None
        if mode == SESSIONS:
            titles =((60, 23, 'Session List'),
                     ( 4, 23, 'Session Details (+/- to scroll)'),
                     (30,  6, 'Session Commands'),)
            info = ParaClass (h=7, w=50, y=15, x=3, ypad=0, xpad=1)
        else:
            titles =((50, 23, 'Commands'),
                     ( 4, 23, 'System Activity'))
            info = ParaClass (h=5, w=50, y=17, x=3, ypad=0, xpad=1)

        echo (color(*WHITE))
        for x,y,txt in titles:
            echo (pos(x,y) + txt)

        info.byindex = True

        clist = LightClass (h=8, w=20, y=15, x=59, xpad=0,ypad=0)
        clist.colors['highlight'] = color(BLUE) + color(INVERSE)
        clist.colors['lowlight'] = color(*DARKGREY)
        clist.byindex = clist.interactive = True
        clist.moved = True # force update of user info

        keys = ParaClass (h=3, w=50, y=3, x=29, ypad=0, xpad=2)
        if mode == SESSIONS:
            keys.update (
              '%sH%sijack       %sK%sill          %sE%sdit\n' \
              '%sQ%suickview    %sD%sisconnect' \
              % (color(*WHITE), color(BLUE),
                 color(*WHITE), color(BLUE),
                 color(*WHITE), color(BLUE),
                 color(*WHITE), color(BLUE),
                 color(*WHITE), color(BLUE)))
            echo (pos(30,6)+color()+color(BLUE)+color(INVERSE)+'  SESSIONS  ')
            echo (color(*DARKGREY)         +'   SYSTEM   ')
        elif mode == SYSTEM:
            echo (pos(60,5)+color(*DARKGREY)         +'  SESSIONS  ')
            echo (color(BLUE)+color(INVERSE)+'   SYSTEM   ')
            keys.update ('Last call: X X ago\n')

        d= time.strftime('%D', localtime(time.time()))
        t= time.strftime('%r', localtime(time.time())).replace(' ','').replace('M','').lower()
        echo (color() + ansi.pos(13,4) + d \
                      + ansi.pos(13,5) + t)
        return clist, info

    def describe(s):
        " return text description of session "
        groups, u = '', getuser(s.handle)
        if u:
            userdata = 'Location: %s, Call #%i' % (u.location, u.calls)
            groups = 'Groups: %s' % implode(u.groups)
        else:
            userdata = '[ Not yet authenticated ]'
            groups = ''
        if not s.terminals:
            idle = ' (detached)'
            termdata = 'no terminals attached'
        else:
            idle = asctime(s.idle())
            termdata = 'terminals: %i' % len(s.terminals)
            for n, t in enumerate(s.terminals):
                termdata += '\n %i:' % n
                if t.attachtime:
                    termdata += ' attached %s ago' % asctime(time.time()- t.attachtime)
                if t.spy:
                    termdata += ' (%s spying)' % t.spy
                termdata += '\n'
                if hasattr(t, 'type'):
                    termdata += '    %s' % (t.type)
                if hasattr(t, 'info'):
                    termdata += ': %s ' % (t.info)
        return \
            'Activity: %s\n' % (s.activity,) \
          + 'Idle: %s, ' % (idle,) \
          + 'Logged in %s ago\n' % (asctime(time.time() - s.logintime),) \
          + '%s\n' % (userdata,) \
          + '%s\n' % (groups,) \
          + termdata

    mode=SESSIONS
    handles, sessions, dirty, clist, info = [], [], True, None, None
    while True:
        ohandles, osessions = handles, sessions
        handles, sessions = [], []

        sessions = sessionlist()
        handles = [s.handle and s.handle or '[ unauthenticated ]' for s in sessions]

        if dirty:
            if clist:
                i, s = clist.item, clist.shift
            else: i, s = 0, 0
            clist, info = refresh(clist, info, mode)
            clist.update (handles)
            clist.position(i, s)
            clist.refresh ()
            info.update (describe(sessions[clist.selection]))
            i=info.scrollIndicator()
            echo (color())
            echo (info.pos(info.visibleWidth-len(i),info.visibleHeight))
            echo (i)
            dirty = False

        elif handles != ohandles:
            if len(handles) != len(ohandles):
                echo (bel)
            clist.update (handles)

        event, data = readevent(['input','refresh'], timeout=.5)

        if event == 'refresh':
            dirty = True
            continue

        if event == 'input' and data:
            if data == KEY.LEFT and mode == SYSTEM:
                mode=SESSIONS
                dirty=True
                continue
            if data == ' ':
                info.update (describe(sessions[clist.selection]))
                lastfresh = time.time()
                continue

            remote = sessions[clist.selection]
            if remote and data == '-':
                info.up()
                continue
            if remote and data == '+':
                info.down()
                continue
            if remote and data == 'H':
                # hijack selected session
                if not isSysop and remote.handle != user.handle:
                    info.update ('You must be in sysop group to hijack sessions of other users!')
                elif remote.sid == session.sid:
                    info.update ('Thats really sick, you know that?')
                else:
                    attachsession (remote.sid, handle())
                continue

            elif remote and data == 'Q':
                # quick-view selected session
                if not isSysop and remote.handle != user.handle:
                    info.update ('You must be in sysop group to view screens of other users!')
                elif remote.sid == session.sid:
                    info.update ('Thats really sick, you know that?')
                else:
                    echo (color() + clear() + getsession(remote.sid).buffer['resume'].getvalue())
                    echo (color() + attr(SBLINK) + '\npress any key')
                    getch ()
                    dirty=True
                continue

            elif remote and data == 'D':
                if not isSysop and remote.handle != handle():
                    info.update ('Must be in sysop group to force disconnect other users!')
                elif not remote.terminals:
                    info.update ('No terminals connected to session')
                else:
                    info.update ('')
                    for n, t in enumerate(remote.terminals):
                        info.add ('Removing terminal: ' + str(n) + '...')
                        t.destroy ()
                continue

            elif remote and data == 'K':
                if not isSysop and remote.handle != handle():
                    info.update ('Must be in sysop group to kill other users!')
                else:
                    info.update ('')
                    info.add ('Closing session: ' + str(remote.sid) + '...')
                    remote.putevent ('ConnectionClosed', 'killed by ' + handle())
                continue

            elif remote and data == 'E':
                gosub ('ueditor', remote.handle)
                dirty = True
                continue

            elif remote and data == 'L' and isSysop:
                gosub (db.cfg.get('system', 'matrixscript'))
                dirty = True
                continue

            elif remote and data == '$':
                gosub ('viewlog')
                dirty = True
                continue

            elif data == 'O':
                info.clean()
                echo (color(*DARKGREY))
                echo (info.pos(1,2) + 'Set refresh delay in seconds')
                echo (info.pos(1,3) + 'or 0 to disable (%sfloat%s): %s' \
                  % (color(*LIGHTBLUE), color(*DARKGREY), color(*WHITE)))
                ndelay = readline (width =4, value=str(delay))
                try:
                    delay = float(ndelay)
                    user.set('screen delay', delay)
                except ValueError: pass
                echo (color(*DARKGREY))
                echo (info.pos(1,5) + 'Set screen blank timeout in seconds')
                echo (info.pos(1,6) + 'or 0 to disable (%sint%s): %s' \
                  % (color(*LIGHTBLUE), color(*DARKGREY), color(*WHITE)))
                nblank = readline (width =8, value=str(blank))
                try:
                    blank = int(nblank)
                    user.set('blank timeout', blank)
                except ValueError: pass
                dirty = True
                continue

            clist.run (data)

            if clist.exit:
                break

        if clist.moved or (delay and time.time() -lastfresh > delay):
            info.update (describe(sessions[clist.selection]))
            lastfresh = time.time()
            clist.moved = False
            continue
