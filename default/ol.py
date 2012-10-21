"""
oneliners for X/84 BBS, uses http://bbs-scene.org API. http://1984.ws
"""

import time
import threading
import Queue
from xml.etree.ElementTree import XML
import requests

def main ():
    session, term = getsession(), getterminal()
    user = session.user
    MAX_INPUT = 50  # character limit for input
    HISTORY   = 84  # limit history in buffer window
    SNUFF_TIME = 1*60*60*24 # one message per 24 hours, 0 to disable
    snuff_msg = 'YOU\'VE AlREADY SAiD ENUff!\a'
    say_msg = 'SAY WhAT? CTRl-X TO CANCEl'
    save_msg = 'BURNiNG TO rOM, PlEASE WAiT!'
    erase_msg = 'ERaSE HiSTORY ?!'
    erased_msg = 'ThE MiNiSTRY Of TRUTh hONORS YOU'
    color1 = term.bold_white
    color2 = term.bold_green
    color3 = term.bold_blue
    udb = DBProxy('oneliner')
    chk_yesno = (term.KEY_ENTER, term.KEY_LEFT, term.KEY_RIGHT,
        'y', 'n', 'Y', 'N', 'h', 'l', 'H', 'L',)
    window, comment = None, None

    def redraw_msgs ():
        output = ''
        for n, ol in sorted(udb.items())[-HISTORY:]:
            c = (color1, color2, color3)[int(n)%3]
            l = '%s(%s' % (term.bold_white, c)
            m = '%s/%s' % (c + term.reverse, term.normal)
            r = '%s)%s' % (term.bold_white, term.normal)
            a = timeago(time.time() -time.mktime \
                (time.strptime(ol['timestamp'], '%Y-%m-%d %H:%M:%S'))).strip()
            output += (l + ol['alias'] + m + ol['bbsname'] + r +': ') .rjust (20)
            output += seqp(ol['oneliner'])
            output += ' %s/%s%s%s ago%s\n' \
                % (term.bold_white, c, a, term.bold_black, term.normal)
        output = output.strip()
        window.update (output, refresh=True, scrollToBottom=True)

    def statusline (text='SAY SUMthiNG?', c=''):
        " display text in status line "
        w = 33
        echo (term.move(term.height-3, (term.width/2)-(w/2)))
        echo (''.join((term.normal, c, text.center(w), term.normal),))

    def saysomething():
        flushevent ('oneliner_update')
        comment.lowlight ()
        statusline (say_msg, term.cyan_inverse)
        comment.update ('')
        echo (term.normal)
        comment.fixate ()
        while True:
            session.activity = 'Blabbering'
            event, data = readevent(['input', 'oneliner_update'])
            if event == 'input':
                if data == '\030':
                    break # ^X (cancel)
                comment.run (key=data)
                if comment.enter:
                    msg = comment.data().strip()
                    if 0 == len(msg):
                        break
                    statusline (save_msg, term.bright_green)
                    session.user.set ('lastliner', time.time())
                    if not ini.cfg.has_section('bbs-scene'):
                        addline (msg)
                        redraw_msgs ()
                        break
                    # post to bbs-scene.rog
                    r = requests.post ('http://bbs-scene.org/api/onelinerz.xml',
                      auth=(ini.cfg.get('bbs-scene','user'),
                            ini.cfg.get('bbs-scene','pass')),
                      data={'oneliner': msg,
                            'alias': session.handle,
                            'bbsname': ini.cfg.get('system', 'bbsname'),})
                    if r.status_code == 200 and XML(r.content) \
                        .find('success').text == 'true':
                        # spawn thread to ensure our update got there ..
                        t = FetchUpdates(queue, lock, history=3)
                        t.start ()
                    break
                elif comment.exit:
                    break
            elif event == 'oneliner_update':
                redraw_msgs ()
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
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    class FetchUpdates(threading.Thread):
        def __init__(self, queue, lock, history):
            self.queue = queue
            self.lock = lock
            self.history = history
            threading.Thread.__init__ (self)

        def run(self):
            r = requests.get \
                ('http://bbs-scene.org/api/onelinerz?limit=%d' % (self.history,),
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
    queue = Queue.Queue()
    lock = threading.Lock()
    t = None
    session.activity = 'Reading one-liners'
    if ini.CFG.has_section('bbs-scene'):
        t = FetchUpdates(queue, lock, HISTORY)
        t.start ()
        session.activity = 'Reading bbs-scene 1liners'

    while True:
        # a bbs-scene.org update occured from our spawned thread, and has items
        # in the queue to be read. matches increments for new records, and if any
        # are found, the screen is refreshed.
        if not queue.empty():
            lock.acquire ()
            matches = 0
            while True:
                try:
                    key, value = queue.get(block=False)
                except Queue.Empty: # queue exausted
                    break
                if not udb.has_key(key):
                    udb[key] = value
                    matches += 1
            lock.release ()
            if matches > 0:
                echo ('\a')
                redraw_msgs ()
            logger.debug ('bbs-scene.org ol-api: %d updates', matches)

        if forceRefresh:
            forceRefresh=False
            echo (term.move (0,0) + term.clear + term.normal)
            if term.width < 78 or term.height < 20:
                echo (term.bold_red + 'Screen size too small to display oneliners' \
                      + term.normal + '\r\n\r\npress any key...')
                getch ()
            art = fopen('art/ol.ans').readlines()
            mw = min(max([len(Ansi(line)) for line in art]), term.width - 6)
            x = max(3, (term.width / 2) - (max([len(Ansi(line)) for line in
                art]) / 2) - 2)
            yn = YesNoClass([x+mw-17, term.height-4])
            yn.interactive = True
            yn.highlight = term.green_reverse
            window = ParaClass(term.height-12, term.width-20,
                y=8, x=10, xpad=0, ypad=1)
            window.interactive = True
            comment = HorizEditor(width=mw, yloc=term.height-3,
                xloc=x, xpad=1, maxlen=MAX_INPUT)
            comment.partial = True
            comment.interactive = True
            echo (''.join([term.move(y+1, x) + from_cp437(line) \
                for y, line in enumerate(art)]))
            statusline ()
            redraw_msgs ()
            yn.refresh ()

        event, data = readevent (['input', 'oneliner_update', 'refresh'],
            timeout=int(ini.cfg.get('session', 'timeout')))

        if (None, None) == (event, data):
            return # timeout
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
                    if SNUFF_TIME != 0:
                        lastliner = user.get('lastliner', time.time() -SNUFF_TIME)
                        if time.time() -lastliner < SNUFF_TIME:
                            statusline (snuff_msg, term.red_reverse)
                            getch (1.5)
                            yn.right ()
                            continue
                    # write something
                    saysomething ()
            elif str(data).lower() == '\003' and session.user.is_sysop:
                # sysop can clear history with ctrl+c
                yn.right ()
                statusline (erase_msg, term.red_reverse)
                yn.interactive = False
                choice = yn.run (key=data)
                if choice == term.KEY_LEFT:
                    # yes, delete all the db ..
                    statusline (erased_msg, term.bright_white)
                    getch (1.6)
                    udb.clear ()
                    redraw_msgs ()
                statusline ()
                yn.interactive = True
            elif data == 'q':
                break
            else:
                # send as movement key to pager window
                window.run (key=data, timeout=None)
    echo (term.normal)
