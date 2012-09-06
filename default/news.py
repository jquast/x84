"""
 News reader module for X/84, http://1984.ws
 $Id: news.py,v 1.6 2009/05/25 20:46:25 dingo Exp $

 This modulde demonstrates use of a pager window.

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast',
                 'Copyright (c) 2005 Johannes Lundberg']
__license__ = 'ISC'
__url__ = 'http://1984.ws'


__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'

import os

deps = ['bbs']

def init():
  NEWS_PATH='text/news.txt'
  global news_content, lastupdate
  try:
    news_content = fileutils.fopen(NEWS_PATH).read()
  except IOError:
    news_content = '%s not found -- no news :)\n' % (NEWS_PATH,)
  lastupdate = os.path.getmtime(fileutils.abspath('text/news.txt'))


def main():
  global news_content, lastupdate
  session = getsession()
  terminal = getsession().getterminal()

  def refresh(pager, lastupdate):
    getsession().activity = 'Reading News'
    y=7
    w=80
    x=1
    h=terminal.rows-y
    echo (color() + cls() + pos())
    if h < 5:
      echo (color(*LIGHTRED) + 'screen height must be at least %i, ' \
            'but is %i.' % (y+5, terminal.rows))
      echo (color() + '\r\n\r\nPress any key...')
      getch(); return False
    if w < 80:
      echo (color(*LIGHTRED) + 'screen width must be at least %i, ' \
            'but is %i.' % (80, terminal.columns))
      echo (color() + '\r\n\r\nPress any key...')
      getch(); return False

    if lastupdate < os.path.getmtime(fileutils.abspath('text/news.txt')):
      # refresh the news text file
      init ()
      if pager:
        pager.update (news_content, refresh=False)

    if not pager:
      pager = ParaClass(h, w, y, x, xpad=2, ypad=1)
      pager.update (news_content, refresh=False)
      pager.interactive = True
      pager.partial = True
    else:
      # just adjust the height
      pager.adjheight (h)

    pager.refresh ()
    pager.lowlight ()
    pager.title ('up/down/(q)uit', align='bottom')
    art = fileutils.fopen('art/news.asc').readlines()
    # overlay art above pager border
    for row, txt in enumerate(art):
      n = 0
      while txt.startswith('  '):
        txt= txt[1:]
        n+= 1
      echo (pos(1, row+1))
      if n: echo (ansi.right(n))
      echo (txt[:-1] + ' ')
    return pager

  forceRefresh, pager = False, refresh(None, lastupdate)
  while not pager.exit:
    event, data = readevent(['input','refresh'])
    if event in ['refresh']:
      pager = refresh(pager, lastupdate)
      if not pager:
        return
      flushevents (['refresh','input'])
    elif event == 'input':
      pager.run (data)

