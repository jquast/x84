"""
Oneliners for X/84 BBS, http://1984.ws
$Id: ol.py,v 1.6 2009/06/01 14:03:32 dingo Exp $

This script demonstrates database storage and state broadcasting.

Features:
 - dynamic screen height resizing
 - scroll up/down through history
 - limit one message per 24 hours
 - new one-liners instantly display while viewing
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2008, 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs','ui/editor']

def init ():
  global MAX_INPUT, HISTORY, ONCE_PER, udb
  MAX_INPUT = 120 # character limit for input
  HISTORY = 200   # limit history in buffer
  ONCE_PER = 1   # one message per 24 hours, 0 to disable
  udb = openudb ('oneliner')
  if not udb.has_key('lines'):
    rebuild_db(udb)

def rebuild_db(udb):
  import persistent
  " re-create raw oneliners database "
  lock ()
  udb['lines'] = persistent.list.PersistentList ()
  commit ()
  unlock ()

def main ():
  session = getsession()
  buffer, comment = None, None

  def redraw ():
    txt = ''
    for n, (name, text) in enumerate(udb['lines'][-HISTORY:]):
      if n % 3 == 0: c = color(*WHITE)
      if n % 3 == 1: c = color(*LIGHTBLUE)
      if n % 3 == 2: c = color(*LIGHTGREEN)
      l = '%s(%s' % (color(*DARKGREY), c)
      r = '%s)%s' % (color(*DARKGREY), color())
      # rjust..
      txt += strpadd(l+name+r, int(cfg.get('nua','max_user'))+2) + text + '\n'
    if txt.endswith('\n'): txt = txt[:-1]
    buffer.update (txt, refresh=True)
    buffer.end (silent=True)

  def addline(line):
    if not line.strip():
      return
    lock ()
    udb['lines'].append ([handle(), line])
    commit ()
    unlock ()
    redraw ()

  def statusline (text='SAY SUMthiNG?', c=''):
    " display text in status line "
    w = 33
    echo (pos((session.width/2)-(w/2), session.height-3))
    echo ('%s%s%s' % (color(), c, strpadd(text, w, align='center', ch=' ')))

  def saysomething():
    statusline ('SAY WhAT? CTRl-X TO CANCEl', color(GREEN))
    comment.update ('')
    comment.highlight ()
    echo (color() + cursor_show())
    comment.fixate ()
    while True:
      session.activity = 'Blabbering'
      event, data = readevent(['input', 'oneliner_update'])
      if event == 'input':
        comment.run (key=data)
        if comment.enter:
          statusline ('BURNiNG TO rOM, PlEASE WAiT!', color(*LIGHTRED))
          oflush ()
          addline (comment.data().strip())
          getuser(handle()).set ('lastliner', timenow())
          redraw ()
          break
        elif comment.exit:
          break
      elif event == 'oneliner_update':
        redraw ()
    echo (color() + cursor_hide())
    comment.noborder ()
    comment.update ()
    statusline ()

  if ONCE_PER:
    # test for existance of .lastliner
    if not getuser(handle()).has_key('lastliner'):
      getuser(handle()).set ('lastliner', 1.0)

  flushevent ('oneliner_update')

  forceRefresh = True

  while True:
    getsession().activity = 'Reading 1liners'

    if forceRefresh:
      echo (cls() + color() + cursor_hide())
      if session.width < 78 or session.height < 20:
        echo (color(*LIGHTRED) + 'Screen size too small to display oneliners' \
              + color() + '\r\n\r\npress any key...')
        readkey()
        return False
      art = fopen('art/wall.ans').readlines()
      mw = maxanswidth(art)
      x = (getsession().width/2)- (mw/2)

      lr = YesNoClass([x+mw-17, session.height-3])
      lr.interactive = True
      lr.highlight = color(GREEN)+color(INVERSE)

      buffer = ParaClass(session.height-11, session.width-20, 8, 10, xpad=0, ypad=1)
      buffer.interactive = True
      comment = HorizEditor(w=mw, y=session.height-2, x=x, xpad=1, max=MAX_INPUT)
      comment.colors['active'] = color(BLUE)
      comment.partial = True
      comment.interactive = True
      echo (''.join([pos(x, y+1) + line for y, line in enumerate(art)]))

      statusline ()
      redraw ()
      lr.refresh ()
      forceRefresh=False

    event, data = readevent (['input', 'oneliner_update', 'refresh'])
    if event == 'refresh':
      forceRefresh=True
      continue
    elif event == 'input':
      if data in ['\030','q']:
        break
      if data in [KEY.ENTER,KEY.LEFT,KEY.RIGHT,'y','n','Y','N','h','l','H','L']:
        choice = lr.run (key=data)
        if choice == RIGHT:
          # exit
          break
        elif choice == LEFT:
          # write something
          if ONCE_PER and timenow() - getuser(handle()).lastliner < (60*60*ONCE_PER):
            statusline (bel + 'YOU\'VE AlREADY SAiD ENUff!', color(*LIGHTRED) + color(INVERSE))
            inkey (1.5)
            lr.right ()
            continue
          # write something
          saysomething ()
      elif str(data).lower() == '\003':
        # sysop can clear history
        u = getuser(handle())
        if not 'sysop' in u.groups:
          continue
        lr.right ()
        statusline (color(RED) + 'ERaSE HiSTORY ?!', color(RED) + color(INVERSE))
        lr.interactive = False
        choice = lr.run (key=data)
        if choice == LEFT:
          statusline ('ThE MiNiSTRY Of TRUTh hONORS YOU', color(*WHITE))
          inkey (1.6)
          rebuild_db (udb)
          redraw ()
        statusline ()
        lr.interactive = True
      elif data == 'q':
        break
      else:
        # send as movement key to pager window
        buffer.run (key=data, timeout=None)
    elif event == 'oneliner_update':
      redraw ()
  echo (cursor_show() + color())
  return
