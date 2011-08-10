"""
 Oneliners module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: ol.py,v 1.6 2008/05/27 11:37:02 dingo Exp $

 This modulde demonstrates database storage and state broadcasting

 In the main loop, we wait for keyboard event or oneliner_update
 event broadcasted by other users. If keyboard event, process through
 the leftrightbar class instance, and if a left or right key is not pressed,
 process as movement key to the pager window.

 If yes(left) is selected, start an inner loop, also waiting for keyboard
 event or oneliner_update event. Keyboard events are processed through
 the comment pager window in edit mode, where a liner is written. When
 enter is pressed, send comment data to buffer.update() and jump-to bottom

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast',
                 'Copyright (c) 2006 Johannes Lundberg']
__license__ = 'ISC'

deps = ['bbs']

history = 100
lrpos   = [62, 21]
# limit onliners to no more than 1 per 24 hours
once_per = 24

def init ():
  # open oneliners database
  global udb
  udb = openudb ('oneliner')
  if not udb.has_key('lines'):
    rebuild_db()
    olupdate ()

def olupdate ():
  """ recalculate raw oneliners database,
      re-create printable database (windata_ol)
      and return this printable list for use with pager"""
  global udb
  n, data = 0, []
  for n, rec in enumerate(udb['lines'][-history:]):
    name, text = rec[0], rec[1]
    data.append ('<' + name + '> ' + text)
  lock ()
  udb['windata_ol'] = data
  commit ()
  unlock ()
  broadcastevent ('oneliner_update', True)
  return data

def rebuild_db():
  " re-create raw oneliners database "
  global udb
  lock ()
  udb['lines'] = PersistentList ()
  udb['lines'].insert(0, ('biG BROthER', 'bEhAVE YOURSElVES'))
  commit ()
  unlock ()

def statusline (text='SAY SUMeTHiNG?', c=''):
  " display text in status line "
  echo (pos(25, lrpos[1]) + color() + c + strpadd(text, 33, align='center', ch=' ') + color())

def main ():

  def redraw ():
    buffer.update (udb['windata_ol'], align='bottom')

  def addline(line):
    if not line: return
    lock ()
    udb['lines'].append ([handle(), line])
    commit ()
    unlock ()
    buffer.update (olupdate(), align='bottom')

  def saysomething():
    statusline ('SAY WhAT? CTRl-X TO CANCEl')
    comment.update ()
    comment.ans.lowlight (partial=True)
    echo (color())
    echo (cursor_show())
    while True:
      session.activity = 'Blabbering'
      event, data = readevent(['input', 'oneliner_update'])
      if event == 'input':
        if data == KEY.ENTER:
          statusline ('BURNiNG TO rOM, PlEASE WAiT!')
          oflush ()
          addline (trim(comment.data()))
          user.set ('lastliner', timenow())
          redraw ()
          break
        if data == '\030':
          redraw ()
          break
        else:
          comment.run (key=data)
      elif event == 'oneliner_update':
        redraw ()

  if once_per:
    # test for existance of .lastliner
    if not user.has_key('lastliner'):
      user.set ('lastliner', 1.0)

  lr = leftrightclass([62, 21])
  lr.interactive = True

  buffer = paraclass(ansiwin(14,72,7,4), xpad=2)
  buffer.interactive = True

  comment = paraclass(ansiwin(3, 60, 22, 10), ypad=1, xpad=1)
  comment.edit, comment.interactive = True, True

  echo (cls() + color())
  showfile ('ans/ol.ans')
  buffer.ans.title ('up/down: history', align='top')

  statusline ()
  redraw ()
  lr.refresh ()

  flushevent ('oneliner_update')

  while 1:
    session.activity = 'Reading 1liners'
    event, data = readevent (['input', 'oneliner_update'])
    if event == 'input':
      choice = lr.run (key=data)
      if choice == RIGHT:
        # exit
        break
      elif choice == LEFT:
        # write something
        if once_per and timenow() - user.lastliner < (60*60*once_per):
          statusline (bel + 'YOU\'VE AlREADY SAiD ENUff!')
          inkey (1.5)
          statusline ()
          lr.right ()
          continue
        # write something
        saysomething ()
        comment.ans.noborder ()
        comment.update ()
        statusline ()
      elif str(data).lower() == '\003':
        # sysop can clear history
        u = getuser(handle())
        if not 'sysop' in u.groups: break
        lr.right ()
        statusline (color(BLACK) + 'ERaSE HiSTORY ?!', color(RED) + color(INVERSE))
        lr.interactive = False
        choice = lr.run (key=data)
        if choice == LEFT:
          statusline ('ThE MiNiSTRY Of TRUTh hONORS YOU')
          inkey (1.6)
          rebuild_db ()
          olupdate ()
          redraw ()
        statusline ()
        lr.interactive = True
      elif data != None and not lr.moved:
        # send as movement key to pager window
        buffer.run (key=data, timeout=None)
      elif data == 'q':
        break
    elif event == 'oneliner_update':
      redraw ()
  echo (cursor_show() + color())
  return


