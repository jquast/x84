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
PROMPT_POS =(15,13)

def init():
  udb = db.openudb('automsg')
  if not len(udb.keys()):
    print 'a'
    lock()
    udb[1]=('B. b.','bEhAVE YOURSElVES')
    commit()
    unlock()
    print 'b'

def main():
  getsession().activity = 'Logging Off!'
  dirty=True
  while True:
    if dirty:
      echo (cls())
      # display random ansi
      try:
        showfile ('ans/goodbye.ans')
      except IOError:
        echo ('click...\r\n')
      echo (ansi.pos(*AUTOMSG_POS) + cl() + color() + 'RX')
      nick, msg = db.openudb('automsg').values()[-1]
      echo ('\b \b\b \b')
      echo ('%s%*s says: %s%s%s' % (
        color(*WHITE), int(db.cfg.get('nua','max_user'))+1, nick,
        color(*DARKGREY), msg, color()))
      echo (ansi.pos(AUTOMSG_POS[0], AUTOMSG_POS[1]+2) + ansi.cursor_show())
      echo ('s:AY SOMEthiNg; g:Et thE fUCk Off !\b')

    k = getch()
    if k in 'gG':
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
      getch (2)
      echo ('CLICK!')
      disconnect ()
      break
    if k in 'sS':
      echo (ansi.pos(*AUTOMSG_POS) + cl() + color())
      echo ('%10s%s: ' % ('say', color(*WHITE),))
      echo (ansi.pos(AUTOMSG_POS[0]+10+2, AUTOMSG_POS[1]))
      echo (color(BLUE) + color(INVERSE) + ' '*AUTOMSG_LENGTH)
      echo (ansi.pos(AUTOMSG_POS[0]+10+2, AUTOMSG_POS[1]))
      nmsg = readline(AUTOMSG_LENGTH)
      if nmsg.strip():
        udb = db.openudb('automsg')
        idx = udb.keys()[-1]+1
        lock()
        udb[idx] = (handle() if handle() else 'anonymous', nmsg)
        commit()
        unlock()
      dirty=True
