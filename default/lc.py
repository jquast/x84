""" Last Callers script for X/84 BBS, http://1984.ws """
import time

def main(recordonly=False):
  db = DBSessionProxy('lastcallers')
  def build():
    " build and return last callers list for display "
    for u in listusers():
      db[u.handle] = u.lastcall

  if recordonly:
    return build ()

  padd_handle = 1+ int(ini.cfg.get('nua','max_user'))
  padd_origin = 1+ int(ini.cfg.get('nua','max_origin'))
  padd_timeago = 12
  padd_ncalls = 13
  def lc_retrieve():
    " retrieve window paint data, list of last callers "
    return '\n'.join((
      u.handle.ljust (padd_handle) \
          + u.location.ljust (padd_origin) \
          + ('%s ago' % (timeago,)).rjust (padd_timeago) \
          + ('   Calls: %s' % (u.calls,)).ljust (padd_ncalls) \
          for timeago, u in [(asctime(time.time() -lc), getuser(handle)) \
            for lc, handle in sorted([(v,k) \
              for (k,v) in db.items() \
                if finduser(k) is not None])]))

  session = getsession()
  session.activity = 'Viewing Last Callers'
  term = getsession().terminal
  def refresh_highdef():
    y=14
    h=term.height - (y+2)
    w=67
    x=(80-w)/2 # ansi is centered for 80-wide
    echo (term.clear + term.normal)
    if h < 5:
      echo (term.bold_green + 'Screen size too small to display last callers' \
            + term.normal + '\r\n\r\npress any key...')
      getch()
      return False
    p= ParaClass(h, w, y, (80-w)/2-2, xpad=2, ypad=1)
    p.colors['inactive'] = term.red
    p.partial = True
    p.lowlight ()
    echo (term.move(0,0))
    showfile ('art/lc.ans')
    data = lc_retrieve()
    if len(data) < h:
      footer='%s-%s (q)uit %s-%s' % (term.bold_white,
          term.normal, term.bold_white, term.normal)
    else:
      footer='%s-%s up%s/%sdown%s/%s(q)uit %s-%s' % (term.bold_white,
          term.normal, term.bold_red, term.normal,
          term.bold_red, term.normal, term.bold_white,
          term.normal)
    p.title (footer, 'bottom')
    p.update (data)
    p.interactive = True
    return p

  if not term.number_of_colors:
    # TODO: scrolling, polling for new logins while waiting for return key..
    echo (lc_retrieve)
    return

  pager = refresh_highdef()
  while pager.exit is False:
    event, data = readevent(['input', 'refresh', 'login'], timeout=None)
    if event in ['refresh', 'login']:
      # in the event of a window refresh (or screen resize),
      # or another user logging in, refresh the screen
      pager = refresh_highdef ()
      if pager is False:
        return # resized to window that is too small ..
      flushevents (['refresh', 'login', 'input'])
    elif event == 'input':
      # update display dataset and run
      pager.run (data)
