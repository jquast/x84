"""
 Who's online module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: wo.py,v 1.6 2008/07/11 02:55:21 dingo Exp $
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

deps = ['bbs','ui.ansiwin','ui.pager','ui.lightwin']

def describe(s):
  groups = ''
  u = getuser(s.handle)
  if u:
    userdata = 'Location: %s, Call #%i' % (u.location, u.calls)
    if 'sysop' in u.groups:
      userdata += '\nemail: %s, password: %s' % (u.hint, u.password)
    groups = 'Groups: %s' % implode(u.groups)
  else:
    userdata = '[ Not yet authenticated ]'
    groups = ''
  if not s.terminals:
    idle = ' (detached)'
    termdata = 'no terminals attached'
  else:
    idle = ' (%s idle)' % asctime(s.idle())
    termdata = 'terminals: %i' % len(s.terminals)
    for n, t in enumerate(s.terminals):
      termdata += '\n  %i:' % n
      if t.attachtime:
        termdata += ' attached %s ago' % asctime(timenow()- t.attachtime)
      if t.spy:
        termdata += ' (%s spying)' % t.spy
      if 'sysop' in getuser(handle()).groups and hasattr(t, 'char'):
        termdata += '\n     last keypress: %s' % repr(t.char)
  return \
      'Activity: %s %s\n' % (s.activity, idle) \
    + 'Logged in %s ago\n' % (asctime(timenow() - s.logintime),) \
    + '%s\n' % userdata \
    + '%s\n' % groups \
    + termdata

def main():

  if getuser(handle()).has_key('screen delay'):
    delay = user['screen delay']
  else:
    delay = 0

  lastfresh = timenow()

  # online users
  ulist = LightClass (h=5, w=6, y=14, x=12, xpad=0, ypad=0)

  ulist.alignment = 'center'
  ulist.interactive = True
  ulist.byindex = True
  ulist.bcolor = color(BLUE) + color(INVERSE)

  # user info
  uinfo = ParaClass(h=15, w=53, y=4, x=20, ypad=1, xpad=2)

  # key help window
  keys = ParaClass(h=7, w=33, y=18, x=25, xpad=1)

  handles, sessions, refresh = [], [], True
  while not ulist.exit:
    ohandles, osessions = handles, sessions
    handles, sessions = [], []
    for s in sessionlist():
      if s.handle:
        handles.append (s.handle)
      else:
        handles.append ('[unknown]')
      sessions.append (s)

    if handles != ohandles and not refresh:
      if len(handles) != len(ohandles):
        echo (bel)
      ulist.update (handles)

    elif refresh or ulist.lastkey == '\014':
      echo (cls() + cursor_show())
      session.activity = 'Checking Who\'s online'
      keys.update \
        ( 'K:ill     D:isconnect\n\n' \
          'H:ijack   E:dit user\n\n' \
          'S:et refresh delay\n\n' \
          'spacebar: force refres')
      refresh = False
      ulist.moved = True
      uinfo.lowlight (partial=False)
      ulist.lowlight (partial=True)
      ulist.update (handles)
    if ulist.moved or ulist.lastkey == ' ' \
    or (delay and timenow() -lastfresh > delay):
      uinfo.update (describe(sessions[ulist.selection]))
      lastfresh = timenow()

    ulist.run (timeout=.5)

    remote = sessions[ulist.selection]

    if remote and ulist.lastkey == 'H':
      if not 'sysop' in getuser(handle()).groups \
      and remote.handle != getuser(handle()).handle:
        uinfo.update ('You must be in sysop group to hijack sessions of other users!')
      elif remote.sid == session.sid:
        uinfo.update ('Thats really sick, you know that?')
      else:
        attachsession (remote.sid, handle())

    elif remote and ulist.lastkey == 'D':
      if not 'sysop' in getuser(handle()).groups \
      and remote.handle != handle():
        uinfo.update ('Must be in sysop group to force disconnect other users!')
      elif not remote.terminals:
        uinfo.update ('No terminals connected to session')
      else:
        uinfo.update ('')
        for n, t in enumerate(remote.terminals):
          uinfo.add ('Removing terminal: ' + str(n) + '...')
          t.destroy ()
          uinfo.ins_ch (' ok.')

    elif remote and ulist.lastkey == 'K':
      if not 'sysop' in getuser(handle()).groups \
      and remote.handle != handle():
        uinfo.update ('Must be in sysop group to force disconnect other users!')
      else:
        uinfo.update ('')
        uinfo.add ('Closing session: ' + str(remote.sid) + '...')
        remote.putevent ('connectionclosed', 'killed by ' + handle())
        uinfo.ins_ch (' ok.')

    elif remote and ulist.lastkey == 'E':
      gosub ('ue', remote.handle)
      refresh = True

    elif ulist.lastkey == 's':
      echo (pos(10,23) + 'Set refresh delay in seconds or 0 to disable (float): ')
      ndelay = readline (max=4, value=str(delay))
      try: delay = float(ndelay)
      except: pass
      echo (pos(20,24) + cl())
      refresh = True
