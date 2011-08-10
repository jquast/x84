"""
 Leave Comment to Sysop/goodbye screen hook for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: comment.py,v 1.5 2008/05/26 07:27:58 dingo Exp $
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = ['Tim Pender']
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

deps = ['bbs']

def addcomment(comment):
  if trim(comment) != '':
    lock()
    udb['lines'].append ((handle(), comment,))
    commit ()
    unlock ()

def comments():
  data = []
  for nick, words in udb['lines']:
    data.append (nick + ': ' + words)
  return data

def main ():
  echo (cls())
  showfile ('ans/comment.ans')
  session.activity = 'Feedback'
  pager = paraclass(ansiwin(h=10, w=60, y=14, x=10), ypad=1, xpad=1)
  pager.ans.title ('lEAVE fEEdbACk tO SYSOP?')
  lr = leftrightclass (xypos=[pager.ans.x + pager.ans.w-13, pager.ans.y])
  lr.interactive = True
  lr.refresh ()

  while True:
    session.activity = 'Sysop Feedback'
    lr.refresh ()
    key = inkey()
    choice = lr.run (key)
    echo (color())
    if choice == LEFT:
      session.activity = 'Leaving feedback'
      pager.ans.border (partial=True)
      pager.ans.title ('< SAY WhAt? CtRl-Y:SENd CtRl-X:CANCEl >', align='bottom')
      pager.update ('')
      pager.edit, pager.interactive = True, True
      pager.fixate ()
      while True:
        ch = inkey()
        if ch == '\031':
          # exit (Ctrl-Y)
          addcomment (pager.data())
          break
        elif ch == '\030':
          # exit (Ctrl-S)
          break
        else:
          ch = pager.run (key=ch)
      pager.ans.clear ()
      break
    elif choice == RIGHT:
      # quit
      break
    elif key == 'c' and 'sysop' in user.groups:
      # clean out comments database
      lock ()
      udb['lines'] = PersistentList()
      commit ()
      unlock ()
    elif key == 'v' and 'sysop' in user.groups:
      # view comments
      pager.ans.border (partial=True)
      pager.update (comments())
      pager.edit, pager.interactive = False, False
      pager.run ()
      pager.ans.noborder ()
      pager.ans.clear ()
      pager.ans.title ('lEAVE fEEdbACk tO SYSOP?')
  return

def init():
  global udb
  udb = openudb ('comments')
  if not udb.has_key('lines'):
    lock ()
    udb['lines'] = PersistentList()
    commit ()
    unlock ()

