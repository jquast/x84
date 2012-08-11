"""
 News reader module for X/84, http://1984.ws
 $Id: viewlog.py,v 1.1 2010/01/01 09:26:35 dingo Exp $

 This modulde demonstrates use of a pager window.

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

import datetime

deps = ['bbs']

def update():
  global lastupdate
  lastupdate = datetime.datetime.now()
  l=[]
  last_d=last_h=last_c=None
  records = sorted(openudb('eventlog').items ()) # so wrong.
  for t, msg in records:
    d=t.strftime('%b %d')
    h=t.strftime('%H:%M:%S')
    s=color(*LIGHTBLUE)
    if d != last_d:
      s+= '%s%s ' % (d, color(*DARKGREY),)
      last_h=last_c=None
    if not last_h or ':'.join(h.split(':')[:2]) != ':'.join(last_h.split(':')[:2]):
      s+= '%s%s%s\n' % (h, color(*DARKGREY), color(*LIGHTBLUE),)
    l.append ('%s\n' % (msg,))
    last_d,last_h=d,h
  return l

def init():
  global printbuf
  printbuf = update()

def main():
  global printbuf, lastupdate
  eventlog = openudb('eventlog')

  def refresh(pager=None, pb=None):
    # transform the log buffer into a printable form
    getsession().activity = 'Viewing system log'
    x,y,w,h = 1, 1, getsession().width, getsession().height
    echo (color() + cls() + pos())
    if h < 20:
      echo (color(*LIGHTRED) + 'screen height must be at least %i, ' \
            'but is %i.' % (20, getsession().height))
      echo (color() + '\r\n\r\nPress any key...')
      readkey(); return False
    if w < 40:
      echo (color(*LIGHTRED) + 'screen width must be at least %i, ' \
            'but is %i.' % (40, getsession().width))
      echo (color() + '\r\n\r\nPress any key...')
      readkey(); return False
    if not pb or lastupdate < sorted(eventlog.keys())[-1]:
      # refresh the buffer content
      pb= update()

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
    if lastupdate < sorted(eventlog.keys())[-1] if len(eventlog) else 0 \
    or event == 'refresh':
      pager, printbuf = refresh(pager)
      flushevents (['refresh','input'])
    if event == 'input':
      pager.run (data)
