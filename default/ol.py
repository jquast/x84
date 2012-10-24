"""
oneliners for x/84, http://github.com/jquast/x84

  To use the (optional) http://bbs-scene.org API,
  configure a section in your .ini file:

    [bbs-scene]
    user = my@email-addr.ess
    pass = my-plaintext-password
"""
import xml.etree.ElementTree
import threading
import Queue
import time

import requests

# bbs-scene.org API is 50-character limit max
MAX_INPUT = 50
# one message per 24 hours, 0 to disable
SNUFF_TIME = 1*60*60*24
# limit history in buffer window
BUF_HISTORY = 100
# limit XML/API requests limit
XML_HISTORY = 84
# in dumb terminal mode or expert mode, wait up to
# this long for bbs-scene.org updates ('x' cancels)
WAIT_FETCH = 15

class FetchUpdates(threading.Thread):
    """
    Dispatch request to find updates to bbs-scene.org's oneliner's
    """
    url = 'http://bbs-scene.org/api/onelinerz?limit=%d' % (BUF_HISTORY,)
    def __init__(self, queue, lock):
        self.queue = queue
        self.lock = lock
        threading.Thread.__init__ (self)

    def run(self):
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        logger.info ('fetching %r ..', self.url)
        req = requests.get (self.url, auth=(usernm, passwd))
        if 200 != req.status_code:
            logger.error (req.content)
            logger.error ('bbs-scene.org returned %s', req.status_code)
            return
        else:
            logger.info ('bbs-scene.org returned %s', req.status_code)

        # can throw exceptions when xml is invalid
        xml_nodes = xml.etree.ElementTree.XML(req.content).findall('node')
        udb = DBProxy('oneliner')
        udb.acquire (timeout=float('inf'), stale=30)
        updates = 0
        for node in xml_nodes:
            udb[node.find('id').text] = dict([(key, node.find(key).text)
                for key in ('oneliner', 'alias', 'bbsname', 'timestamp',)])
            updates += 1
        udb.release ()
        logger.info ('stored %d updates from bbs-scene.org', updates)

def wait_for(thread):
    if thread.is_alive():
        echo ("\r\n\r\nOneliners -- fetching bbs-scene.org, 'x' to cancel .. "
                "(%s)s\b\b%s" % (' ' * wflen, '\b' * wflen,))
        for n in range(WAIT_FETCH):
            echo ('%d%s' % (WAIT_FETCH - num - 1,), '\b' * wflen,)
            if not thread.is_alive():
                return
            thread.join (1)
            if getch(-1) == 'x':
                return

def addline(msg):
    udb = DBProxy('oneliner')
    udb.acquire (timeout=float('inf'), stale=5)
    udb[max([int(key) for key in udb.iterkeys()] or [0]) + 1] = {
        'oneliner': msg,
        'alias': session.handle,
        'bbsname': ini.CFG.get('system', 'bbsname'),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    udb.release ()

def get_oltxt():
    term = getterminal()
    output = u''
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    print repr('fetch udb ol..')
    for idx, onel in sorted(DBProxy('oneliner').items())[BUF_HISTORY * -1:]:
        print repr(idx), repr(onel)
        color = colors[int(idx) % len(colors)]
        atime = timeago(time.time() - time.mktime (
            time.strptime(onel['timestamp'], '%Y-%m-%d %H:%M:%S'))).strip()
        output += u''.join((
            term.bold_white('('), color(onel['alias']),
            term.bold_black(u'/'), onel['bbsname'],
            term.bold_white(u')'), color(u': '),
            Ansi(onel['oneliner']).decode_pipe(),
            term.bold_black(u'  /'), color(atime),
            term.bold_black(u' ago\n'),))
    print 'output', repr(output)
    return output

def get_selector(selection=u'No'):
    term = getterminal ()
    selector = Selector(yloc=term.height-1, xloc=(term.width / 2) - 25,
            width=50, left=u'Yes', right=u'No')
    selector.keyset['left'].extend((u'y', u'Y'))
    selector.keyset['right'].extend((u'y', u'Y'))
    selector.selection = selection
    selector.colors['selected'] = term.green_reverse
    return selector

def get_pager():
    term = getterminal ()
    pager = Pager(yloc=12, xloc=3,
            height=term.height - 15, width=term.width - 6)
    pager.colors['border'] = term.blue
    return pager

def redraw(pager, selector):
    term = getterminal()
    output = term.home + term.normal + term.clear
    flushevent ('oneliner_update')

    # xzip's ansi is line-clean, center-align with terminal width,
    art = fopen('default/art/ol.ans').readlines()
    max_ans = max([len(Ansi(from_cp437(line))) for line in art])
    for line in art:
        padded = Ansi(from_cp437(line)).center(max_ans)
        output += Ansi(padded).center(term.width).rstrip()
        output += term.normal + '\r\n'

    xloc = (term.width / 2) - (max_ans / 2)
    selector.yloc = term.height - 1
    selector.xloc = xloc
    selector.width = max_ans
    pager.yloc = 1 + len(art)
    pager.xloc = xloc
    pager.height = term.height - pager.yloc - 4
    pager.width = max_ans
    pager.update(get_oltxt())
    output += pager.refresh() + pager.border() + selector.refresh()
    return output

def dummy_pager():
    term = getterminal()
    echo (term.normal + '\r\n\r\n')
    if term.width >= 79:
        echo ('\r\n'.join((Art(line.rstrip()).center(term.width).rstrip()
            for line in fopen('default/art/ol.ans'))))
    echo (term.normal + '\r\n\r\n')
    for row in get_oltxt().split('\n')[:(term.height - 2) * -1]:
        echo (Ansi(row.rstrip()).center((term.width)).rstrip() + '\r\n')
    echo (term.normal + '\r\npress any key .. ')
    getch ()
    return

def saysomething():
    #broadcastevent ('oneliner_update', self.handle, )
    pass
    #snuff_msg = u'YOU\'VE AlREADY SAiD ENUff!\a'
    #flushevent ('oneliner_update')
    #say_msg = u'SAY WhAT? CTRl-X TO CANCEl'
    #save_msg = u'BURNiNG TO rOM, PlEASE WAiT!'
    #if SNUFF_TIME != 0:
    #    lastliner = session.user.get('lastliner',
    #            time.time() - SNUFF_TIME)
    #    if time.time() - lastliner < SNUFF_TIME:
    #        #statusline (snuff_msg, term.red_reverse)
    #        getch (1.5)
    #        echo (yn.move_right ())
    #        continue


#    comment = LineEditor(MAX_INPUT).read ()
#    if comment is not None and 0 != len(comment):
#        statusline (save_msg, term.bright_green)
#        session.user['lastliner'] = time.time()
#        if not ini.CFG.has_section('bbs-scene'):
#            addline (msg)
#            redraw_msgs ()
#            return
#        url = 'http://bbs-scene.org/api/onelinerz.xml'
#        usernm = ini.CFG.get('bbs-scene', 'user')
#        passwd = ini.CFG.get('bbs-scene', 'pass')
#        bbsname = ini.CFG.get('system', 'bbsname')
#        # post to bbs-scene.rog
#        req = requests.post (url, auth=(usernm, passwd), data={
#            'oneliner': msg, 'alias': session.handle, 'bbsname': bbsname,})
#        if (req.status_code == 200 and
#                xml.etree.ElementTree.XML(req.content).find('success').text == 'true'):
#            # spawn request threads for updates and bark-back our own line
#            thread = FetchUpdates(queue, lock, history=3)
#            thread.start ()
#            return
#    echo (comment.clear())
#    return
##            comment = HorizEditor(width=mw, yloc=term.height-3,
#                xloc=x, xpad=1, maxlen=MAX_INPUT)
#            comment.partial = True
#            comment.interactive = True
#            echo (''.join([term.move(y+1, x) + from_cp437(line) \
#                for y, line in enumerate(art)]))
#            statusline ()
#            redraw_msgs ()
#            yn.refresh ()
#

#    dirty = True


def main ():
    session, term = getsession(), getterminal()
    session.activity = 'one-liners'

    queue = Queue.Queue()
    lock = threading.Lock()
    # spawn background thread to get new oneliners, and provide us the results
    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates(queue, lock)
        thread.start ()
        session.activity = 'one-liners [bbs-scene.org]'

    pager, selector = get_pager(), get_selector()
    dirty = True
    while True:
        # bbs-scene.org updates setn queued by thread
        if thread is not None and not thread.is_alive():
            logger.debug ('bbs-scene.org thread end, will-redraw')
            thread = None
            dirty = True

        # screen resize
        if pollevent('refresh'):
            logger.debug ('bbs-scene.org updates will-redraw')
            pager, selector = get_pager(), get_selector(selector.selection)
            dirty = True

        if pollevent('oneliner_update'):
            logger.debug ('bbs-scene.org oneliner_update event')
            dirty = True

        if dirty:
            # re-draw a smart terminal
            if (session.env.get('TERM') != 'unknown' and not
                    session.user.get('expert', False) and term.width >= 79):
                echo (term.home + term.clear)
                echo (redraw(pager, selector))
                dirty = False
            else:
                # enter dumb terminal mode
                if thread is not None:
                    wait_for (thread)
                return dummy_pager()

        # block 1s for keyboard.
        inp = getch (1)
        if inp is not None:
            # input is multiplexed to both interfaces
            echo (pager.process_keystroke (inp))
            echo (selector.process_keystroke (inp))

            # quit 'q', or selected 'no' & return
            if (selector.selected and selector.selection == selector.right
                    or pager.quit):
                return

            # selected 'yes' & return, 'say something'
            if (selector.selected and selector.selection == selector.left):
                saysomething ()
                dirty = True
