"""
  Logoff script for X/84, http://1984.ws
  $Id: logoff.py,v 1.3 2010/01/02 01:03:30 dingo Exp $

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']
AUTOMSG_LENGTH=40
AUTOMSG_POS=(15,11)

def init():
  udb = openudb('automsg')
  if not len(udb.keys()):
    lock()
    udb[1]=('B. b.','bEhABE YOURSElVES')
    commit()
    unlock()

def main():
  session.activity = 'Logging Off!'
  dirty=True
  while True:
    if dirty:
      echo (cls())
      # display random ansi
      try:
        showfile ('ans/goodbye.ans')
      except IOError:
        echo ('click...\r\n')
      echo (ansi.pos(*AUTOMSG_POS) + cl() + color())
      nick, msg = openudb('automsg').values()[-1]
      # XXX db.cfg.max_user
      echo ('%10s%s: %s%s' % (nick, color(*WHITE), color(*DARKGREY), msg))

    k = readkey()
    if k == 's':
      gosub('comment')
      dirty=True
    if k == 't':
      echo ( cls() + \
      'Try some of these other fine boards!\r\n\r\n' \
      '  htc.zapto.org              The Haunted Chapel\r\n' \
      '  +o MercyFul Fate           C++/BSD\r\n\r\n' \
        \
      '  ## offline ##              The Centre\r\n' \
      '  +o tombin                  perl/linux\r\n\r\n' \
        \
      '  bld.ph4.se                 Blood Island\r\n' \
      '  +o hellbeard               python/linux\r\n\r\n' \
        \
      '  ## offline ##              whereabouts unknown!\r\n' \
      '  +o sinister x              .net/win32\r\n\r\n'
        \
      '  graveyardbbs.kicks-ass.net The Graveyard\r\n' \
      '  +o The Reaper              renegade bbs\r\n\r\n' \
      )
      readkey (10)
      echo ('CLICK!')
      disconnect ()
      break
    if k == 'a':
      return # unless we were called with a 'goto'
    if k == 'c':
      echo (ansi.pos(*AUTOMSG_POS) + cl() + color())
      echo ('%10s%s: ' % ('say', color(*WHITE),))
      echo (ansi.pos(AUTOMSG_POS[0]+10+2, AUTOMSG_POS[1]))
      echo (color(BLUE) + color(INVERSE) + ' '*AUTOMSG_LENGTH)
      echo (ansi.pos(AUTOMSG_POS[0]+10+2, AUTOMSG_POS[1]))
      nmsg=readline(AUTOMSG_LENGTH)
      if nmsg.strip():
        udb = openudb('automsg')
        idx = udb.keys()[-1]+1
        lock()
        udb[idx] = (session.handle and session.handle or '?', nmsg,)
        commit()
        unlock()
      dirty=True
