"""
 News reader module for X/84, http://1984.ws
 This script demonstrates use of a pager window.
"""

def main():
  try:
    news_content = fileutils.fopen(NEWS_PATH).read()
  except IOError:
    news_content = '%s not found -- no news :)\n' % (NEWS_PATH,)

  session = getsession()
  terminal = getsession().getterminal()

  def refresh(pager, lastupdate):
    getsession().activity = 'Reading News'
    y=7
    w=80
    x=1
    h=terminal.rows-y
    echo (terminal.move (0,0) + terminal.clear)
    if h < 5:
      echo (terminal.bold_red + 'screen height must be at least %i, ' \
            'but is %i.' % (y+5, terminal.rows))
      echo (terminal.normal + '\r\n\r\nPress any key...')
      getch(); return False
    if w < 80:
      echo (terminal.bold_red + 'screen width must be at least %i, ' \
            'but is %i.' % (80, terminal.columns))
      echo (terminal.normal + '\r\n\r\nPress any key...')
      getch(); return False

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

