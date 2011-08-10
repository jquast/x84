"""
 News reader module for X/84, http://1984.ws
 $Id: viewlog.py,v 1.1 2010/01/01 09:26:35 dingo Exp $

 This modulde demonstrates use of a pager window.

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

import os, time

deps = ['bbs']

def init():
  global printbuf
  printbuf = reload()

def reload():
  global lastupdate
  lastupdate = timenow()
  l=[]
  last_d=last_h=last_c=None
  for t, (c, msg) in db.logfile.items():
    d=time.strftime('%b %d', time.localtime(t))
    h=time.strftime('%H:%M:%S', time.localtime(t))
    s=color(*LIGHTBLUE)
    if d != last_d:
      s+= '%s%s ' % (d, color(*DARKGREY),)
      last_h=last_c=None
    if not last_h or ':'.join(h.split(':')[:2]) != ':'.join(last_h.split(':')[:2]):
      s+= '%s%s%s\n' % (h, color(*DARKGREY), color(*LIGHTBLUE),)
      last_c=None
    if c != last_c:
      s+= '%s[%s%s%s] ' % \
          (color(*WHITE), color(*DARKGREY), c, color(*WHITE))
    else:
      s+= ' '*(len(c)+3)
    l.append('%s%s%s\n' % (s, color(), msg))
    last_d,last_h,last_c=d,h,c
  return l

def main():
  global printbuf, lastupdate
  session = getsession()

  def refresh(pager=None, pb=None):
    # transform the log buffer into a printable form
    session.activity = 'Viewing system log'
    x,y,w,h = 1, 1, session.width, session.height
    echo (color() + cls() + pos())
    if h < 20:
      echo (color(*LIGHTRED) + 'screen height must be at least %i, ' \
            'but is %i.' % (20, session.height))
      echo (color() + '\r\n\r\nPress any key...')
      readkey(); return False
    if w < 40:
      echo (color(*LIGHTRED) + 'screen width must be at least %i, ' \
            'but is %i.' % (40, session.width))
      echo (color() + '\r\n\r\nPress any key...')
      readkey(); return False
    if lastupdate < sorted(db.logfile.keys())[-1] or not pb:
      # refresh the buffer content
      pb= reload ()

    if not pager:
      pager = ParaClass(h, w, y, x, xpad=0, ypad=1)
      pager.interactive = True
      pager.colors['inactive'] = color(BLUE)
      pager.partial = True
    pager.update (pb, scrollToBottom=True)
    pager.lowlight ()
    pager.title (color()+'- up/down/(q)uit/(f)ind -' \
      .replace('/','%s/%s'%(color(*DARKGREY),color())),
      align='bottom')
    return pager, pb

  pager, printbuf = refresh()
  while not pager.exit:
    event, data = readevent(['input','refresh'], timeout=1)
    # buffer is out of date, recalculate
    if lastupdate < sorted(db.logfile.keys())[-1] or event == 'refresh':
      pager, printbuf = refresh(pager)
      flushevents (['refresh','input'])
    if event == 'input':
      pager.run (data)
