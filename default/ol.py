"""
oneliners for X/84 BBS, uses http://bbs-scene.org API. http://1984.ws
"""

import time
import threading
import Queue
from xml.etree.ElementTree import XML
import requests

MAX_INPUT = 50          # bbs-scene.org API is 50-character limit max
SNUFF_TIME = 1*60*60*24 # one message per 24 hours, 0 to disable
BUF_HISTORY = 1984      # limit history in buffer window and XML/API requests

class FetchUpdates(threading.Thread):
    """
    Dispatch request for updates to bbs-scene.org's oneliner's, ensuring the
    interface isn't locked up if the API is slow or offline, using an
    asynchronous callback mechanism.
    """
    url = 'http://bbs-scene.org/api/onelinerz?limit=%d'
    def __init__(self, queue, lock, num):
        self.queue = queue
        self.lock = lock
        self.num = num
        threading.Thread.__init__ (self)

    def run(self):
        term = getterminal ()
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        r = requests.get (self.url % (self.num,), auth=(usernm, passwd))
        if 200 != r.status_code:
            logger.error (r.content)
            logger.error ('bbs-scene.org returned %s', r.status_code)
            return
        self.lock.acquire ()
        for node in XML(r.content).findall('node'):
            key = node.find('id').text
            self.queue.put ((key, dict([(k, node.find(k).text) for k in
                ('oneliner', 'alias', 'bbsname', 'timestamp',)])))
        self.lock.release ()

def saysomething():
    comment = LineEditor(MAX_INPUT).read ()
    if comment is not None and 0 != len(comment):
        statusline (save_msg, term.bright_green)
        session.user['lastliner'] = time.time()
        if not ini.CFG.has_section('bbs-scene'):
            addline (msg)
            redraw_msgs ()
            return
        url = 'http://bbs-scene.org/api/onelinerz.xml'
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        bbsname = ini.CFG.get('system', 'bbsname')
        # post to bbs-scene.rog
        req = requests.post (url, auth=(usernm, passwd), data={
            'oneliner': msg, 'alias': session.handle, 'bbsname': bbsname,})
        if (req.status_code == 200 and
                XML(req.content).find('success').text == 'true'):
            # spawn request threads for updates and bark-back our own line
            thread = FetchUpdates(queue, lock, history=3)
            thread.start ()
            return
    echo (comment.clear())
    return


def redraw(pager):
    term = getterminal()
    udb = DBProxy('oneliner')
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    output = u''
    for idx, onel in sorted(udb.items())[-BUF_HISTORY:]:
        color = colors[idx % len(colors)]
        atime = timeago(time.time() - time.mktime (
            time.strptime(onel['timestamp'], '%Y-%m-%d %H:%M:%S'))).strip()
        output += u''.join(term.bold_white('('), color(onel['alias']),
                term.bold_black(u'/'), onel['bbsname'], term.bold_white(u')'),
                color(u': '), Ansi(onel['oneliner']).decode_pipe(),
                term.bold_black(u'  /'), color(atime),
                term.bold_black(u' ago\n'))
    return pager.update(output)

def main ():
    session, term = getsession(), getterminal()
    session.activity = 'Reading one-liners'

    snuff_msg = u'YOU\'VE AlREADY SAiD ENUff!\a'
    say_msg = u'SAY WhAT? CTRl-X TO CANCEl'
    save_msg = u'BURNiNG TO rOM, PlEASE WAiT!'
    erase_msg = u'ERaSE HiSTORY ?!'
    erased_msg = u'ThE MiNiSTRY Of TRUTh hONORS YOU'
    dirty = True
    queue = Queue.Queue()
    lock = threading.Lock()
    # spawn background thread to get new oneliners, and provide us the results
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates(queue, lock, BUF_HISTORY)
        thread.start ()
        session.activity = 'Reading bbs-scene 1liners'

    flushevent ('oneliner_update')

#    def addline(msg):
#        udb[max([int(k) for k in udb.keys()] or [0])+1] = {
#            'oneliner': msg,
#            'alias': session.handle,
#            'bbsname': ini.CFG.get('system', 'bbsname'),
#            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
#        }
#

#    while True:
#        # a bbs-scene.org update occured from our spawned thread, and has items
#        # in the queue to be read. matches increments for new records, and if any
#        # are found, the screen is refreshed.
#        if not queue.empty():
#            lock.acquire ()
#            matches = 0
#            while True:
#                try:
#                    key, value = queue.get(block=False)
#                except Queue.Empty: # queue exausted
#                    break
#                if not udb.has_key(key):
#                    udb[key] = value
#                    matches += 1
#            lock.release ()
#            if matches > 0:
#                echo ('\a')
#                redraw_msgs ()
#            logger.debug ('bbs-scene.org ol-api: %d updates', matches)
#
#        if forceRefresh:
#            forceRefresh=False
#            echo (term.move (0,0) + term.clear + term.normal)
#            if term.width < 78 or term.height < 20:
#                echo (term.bold_red + 'Screen size too small to display oneliners' \
#                      + term.normal + '\r\n\r\npress any key...')
#                getch ()
#            art = fopen('default/art/ol.ans').readlines()
#            mw = min(max([len(Ansi(line)) for line in art]), term.width - 6)
#            x = max(3, (term.width / 2) - (max([len(Ansi(line)) for line in
#                art]) / 2) - 2)
#
#            yn = YesNoClass([x+mw-17, term.height-4])
#            yn.interactive = True
#            yn.highlight = term.green_reverse
#            window = ParaClass(term.height-12, term.width-20,
#                y=8, x=10, xpad=0, ypad=1)
#            window.interactive = True
#            comment = HorizEditor(width=mw, yloc=term.height-3,
#                xloc=x, xpad=1, maxlen=MAX_INPUT)
#            comment.partial = True
#            comment.interactive = True
#            echo (''.join([term.move(y+1, x) + from_cp437(line) \
#                for y, line in enumerate(art)]))
#            statusline ()
#            redraw_msgs ()
#            yn.refresh ()
#
#        event, data = readevent (['input', 'oneliner_update', 'refresh'],
#            timeout=int(ini.CFG.get('session', 'timeout')))
#
#        if (None, None) == (event, data):
#            return # timeout
#        if event == 'refresh':
#            forceRefresh=True
#            continue
#
#        elif event == 'input':
#            if data in ['\030','q']:
#                break
#            if data in chk_yesno:
#                choice = yn.run (key=data)
#                if choice == yn.NO:
#                    # exit
#                    break
#                elif choice == yn.YES:
#                    if SNUFF_TIME != 0:
#                        lastliner = session.user.get('lastliner',
#                                time.time() -SNUFF_TIME)
#                        if time.time() -lastliner < SNUFF_TIME:
#                            statusline (snuff_msg, term.red_reverse)
#                            getch (1.5)
#                            yn.right ()
#                            continue
#                    # write something
#                    saysomething ()
#            elif str(data).lower() == '\003' and session.user.is_sysop:
#                # sysop can clear history with ctrl+c
#                yn.right ()
#                statusline (erase_msg, term.red_reverse)
#                yn.interactive = False
#                choice = yn.run (key=data)
#                if choice == term.KEY_LEFT:
#                    # yes, delete all the db ..
#                    statusline (erased_msg, term.bright_white)
#                    getch (1.6)
#                    udb.clear ()
#                    redraw_msgs ()
#                statusline ()
#                yn.interactive = True
#            elif data == 'q':
#                break
#            else:
#                # send as movement key to pager window
#                window.run (key=data, timeout=None)
#    echo (term.normal)


