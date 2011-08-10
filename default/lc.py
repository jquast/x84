"""
 Last Callers script for X/84 BBS, http://1984.ws
 $Id: lc.py,v 1.8 2009/05/31 16:12:29 dingo Exp $

 This script displays all users of the BBS, and the last time
 they have called in descending order. When True is passed as
 the first argument, only the call log is built.
"""

__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast',
                 'Copyright (c) 2005 Johannes Lundberg']
__license__ = 'ISC'
__url__ = 'http://1984.ws'


deps = ['bbs']

def init():
  global udb
  udb = openudb('lc') # open sorted call log

def lc_retrieve():
  " retrieve window paint data, list of last callers "
  return '\n'.join([
    strpadd(user.handle, cfg.max_user +1) + \
    strpadd(user.location, cfg.max_origin +1) + \
    strpadd(timeago + ' ago', 12, 'right') + \
    strpadd('  Calls: %s' % (user.calls), 13) \
      for timeago, user in \
        [(asctime(timenow() -lc), getuser(name)) \
         for lc, name in udb['callers'] if userexist(name)]])

def build():
  " build and return last callers list for display "
  global udb
  callers = [(user.lastcall, user.handle) for user in listusers()]
  callers.sort ()
  callers.reverse ()
  lock()
  udb['callers'] = callers
  commit()
  unlock()

def main(recordonly=False):
  if recordonly:
    return build ()

  session = getsession()
  def refresh():
    session.activity = 'Viewing Last Callers'
    y=14
    h=session.height -y+1
    w=67
    x=(80-w)/2 # ansi is centered for 80-wide
    echo (color() + cls())
    if h < 5:
      echo (color(*LIGHTRED) + 'Screen size too small to display last callers' \
            + color() + '\r\n\r\npress any key...')
      readkey()
      return False
    pager = ParaClass(h, w, y, (80-w)/2-2, xpad=2, ypad=1)
    pager.colors['inactive'] = color(RED)
    pager.partial = True
    pager.lowlight ()
    echo (pos())
    showfile ('art/lc.ans')
    data = lc_retrieve()
    if len(data) < h:
      footer='%s-%s (q)uit %s-%s'%(color(*DARKGREY),color(),color(*DARKGREY),color())
    else: footer='%s-%s up%s/%sdown%s/%s(q)uit %s-%s' % (color(*DARKGREY),color(),
      color(*LIGHTRED),color(),color(*LIGHTRED),color(),color(*DARKGREY),color())
    pager.title (footer, 'bottom')
    pager.update (data)
    pager.interactive = True
    return pager

  # refresh on first loop
  forceRefresh=True

  while True:
    if forceRefresh:
      pager = refresh()
      if not pager:
        return
      forceRefresh = False
      flushevents (['refresh','login','input'])

    event, data = readevent(['input', 'refresh', 'login'], timeout=None)

    if event in ['refresh', 'login']:
      # in the event of a window refresh (or screen resize),
      # or another user logging in, refresh the screen
      forceRefresh=True
      continue

    elif event == 'input':
      # update display dataset and run
      pager.run (data)

    if pager.exit:
      return # exit
