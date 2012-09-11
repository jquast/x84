"""
oneliners for X/84 BBS, uses http://bbs-scene.org API. http://1984.ws
"""

import time
import threading
import Queue
from xml.etree.ElementTree import XML
import requests

def main ():
  session = getsession()
  term = session.terminal
  user = session.user
  MAX_INPUT = 80 # character limit for input
  HISTORY = 50   # limit history in buffer window
  SNUFF_TIME = 1*60*60*24   # one message per 24 hours, 0 to disable
  snuff_msg = 'YOU\'VE AlREADY SAiD ENUff!\a'
  say_msg = 'SAY WhAT? CTRl-X TO CANCEl'
  save_msg = 'BURNiNG TO rOM, PlEASE WAiT!'
  erase_msg = 'ERaSE HiSTORY ?!'
  erased_msg = 'ThE MiNiSTRY Of TRUTh hONORS YOU'
  udb = DBProxy('oneliner')
  chk_yesno = (term.KEY_ENTER, term.KEY_LEFT, term.KEY_RIGHT,
      'y', 'n', 'Y', 'N', 'h', 'l', 'H', 'L',)
  window, comment = None, None

  def redraw ():
    output = ''
    for n, ol in sorted(udb.items())[-HISTORY:]:
      n = int(n)
      if n%3 == 0: c = term.bold_white
      elif n%3 == 1: c = term.bold_green
      else: c = term.bold_blue
      l = '%s(%s' % (term.bold_white, c)
      m = '%s/%s' % (term.white + term.reverse, term.normal)
      r = '%s)%s' % (term.bold_white, term.normal)
      output += (l + ol['alias'] + m + ol['bbsname'] + r +': ') .rjust (20)
      output += str(ol['oneliner']) + '\n'
    output = output.rstrip()
    window.update (output, refresh=True, scrollToBottom=True)


  def statusline (text='SAY SUMthiNG?', c=''):
    " display text in status line "
    w = 33
    echo (term.move(term.height-3, (term.width/2)-(w/2)))
    echo (''.join((term.normal, c, text.center(w)),))

  def saysomething():
    comment.lowlight ()
    statusline (say_msg, term.cyan_inverse)
    comment.update ('')
    echo (term.normal)
    comment.fixate ()
    while True:
      session.activity = 'Blabbering'
      event, data = readevent(['input', 'oneliner_update'])
      if event == 'input':
        comment.run (key=data)
        if comment.enter:
          statusline (save_msg, term.bright_green)
          addline (comment.data().strip())
          session.user.set ('lastliner', time.time())
          redraw ()
          break
        elif comment.exit:
          break
      elif event == 'oneliner_update':
        redraw ()
    echo (term.normal)
    comment.noborder ()
    comment.update ()
    statusline ()
    user.set ('lastliner', time.time())

  def addline(msg):
    udb[max([int(k) for k in udb.keys()] or [0])+1] = {
        'oneliner': msg,
        'alias': session.handle,
        'bbsname': ini.cfg.get('system', 'bbsname'),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%s'),
    }

  class FetchUpdates(threading.Thread):
    def __init__(self, queue, lock):
      self.queue = queue
      self.lock = lock
      threading.Thread.__init__ (self)
    def run(self):
      r = requests.get \
          ('http://bbs-scene.org/api/onelinerz?limit=%d' % (HISTORY,),
            auth=(ini.cfg.get('bbs-scene','user'),
                  ini.cfg.get('bbs-scene','pass')))
      if 200 != r.status_code:
        echo (term.move (0,0) + term.clear + term.normal)
        echo ('%sonelinerz offline (status_code=%d): \r\n\r\n' \
            '%s%s%s\r\n\r\npress any key...' % (term.bold_red, r.status_code,
              term.normal, r.content, term.bold_red))
        getch ()
        return
      self.lock.acquire ()
      for node in XML(r.content).findall('node'):
        key = node.find('id').text
        self.queue.put ((key, dict([ (k, node.find(k).text) \
              for k in ('oneliner','alias','bbsname','timestamp',) ])))
      self.lock.release ()

  flushevent ('oneliner_update')
  forceRefresh = True
  q = Queue.Queue()
  if ini.cfg.has_section('bbs-scene'):
    l = threading.Lock()
    t = FetchUpdates(q, l)
    t.start ()
    session.activity = 'Reading bbs-scene 1liners'
  else:
    session.activity = 'Reading one-liners'

  while True:
    if not q.empty():
      matches = 0
      l.acquire ()
      while True:
        try:
          key, value = q.get(block=False)
        except Queue.Empty:
          break
        if not udb.has_key(key):
          udb[key] = value
          matches += 1
      l.release ()
      if matches > 0:
        print 'ol:', matches, 'new updates'
        redraw ()
      else:
        print 'ol: no new bbs-scene.org'

    if forceRefresh:
      echo (term.move (0,0) + term.clear + term.normal)
      if term.width < 78 or term.height < 20:
        echo (term.bold_red + 'Screen size too small to display oneliners' \
              + term.normal + '\r\n\r\npress any key...')
        getch ()
        return False
      art = fopen('art/wall.ans').readlines()
      mw = min(maxanswidth(art), term.width -6)
      x = max(3, (term.width/2) - (maxanswidth(art)/2) -2)

      yn = YesNoClass([x+mw-17, term.height-4])
      yn.interactive = True
      yn.highlight = term.green_reverse

      window= ParaClass(term.height-12, term.width-20,
          y=8, x=10, xpad=0, ypad=1)
      window.interactive = True
      comment = HorizEditor(w=mw, y=term.height-3,
          x=x, xpad=1, max=MAX_INPUT)
      comment.partial = True
      comment.interactive = True
      echo (''.join([term.move(y+1, x) + line.decode('iso8859-1') for y, line in enumerate(art)]))

      statusline ()
      redraw ()
      yn.refresh ()
      forceRefresh=False

    event, data = readevent (['input', 'oneliner_update', 'refresh'], timeout=1)

    if event == 'refresh':
      forceRefresh=True
      continue

    elif event == 'input':
      if data in ['\030','q']:
        break
      if data in chk_yesno:
        choice = yn.run (key=data)
        if choice == yn.NO:
          # exit
          break
        elif choice == yn.YES:
          lastliner = user.get('lastliner', time.time() -SNUFF_TIME)
          if time.time() -lastliner < SNUFF_TIME:
            statusline (snuff_msg, term.red_reverse)
            getch (1.5)
            yn.right ()
            continue
          # write something
          saysomething ()
      elif str(data).lower() == '\003':
        # sysop can clear history
        if not 'sysop' in session.user.groups:
          continue
        yn.right ()
        statusline (erase_msg, term.red_reverse)
        yn.interactive = False
        choice = yn.run (key=data)
        if choice == term.KEY_LEFT:
          statusline (erased_msg, term.bright_white)
          getch (1.6)
          udb.clear ()
          redraw ()
        statusline ()
        yn.interactive = True
      elif data == 'q':
        break
      else:
        # send as movement key to pager window
        print data
        window.run (key=data, timeout=None)
  echo (term.normal)
  return
