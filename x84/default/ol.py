""" oneliners for x/84, http://github.com/jquast/x84

  To use the (optional) http://bbs-scene.org API,
  configure a section in your .ini file:

    [bbs-scene]
    user = my@email-addr.ess
    pass = my-plaintext-password
"""
import xml.etree.ElementTree
import threading
import requests
import logging
import time
import os

#pylint: disable=W0614
#        Unused import from wildcard import
from x84.bbs import *

# bbs-scene.org API is 50-character limit max
MAX_INPUT = 50
# scrollback / database limit
BUF_HISTORY = 500
# XML/API requests limit
XML_HISTORY = 84
# in dumb terminal mode or expert mode, wait up to
# this long for bbs-scene.org updates ('x' cancels)
WAIT_FETCH = 3

class FetchUpdates(threading.Thread):
    url = 'http://bbs-scene.org/api/onelinerz?limit=%d' % (XML_HISTORY,)
    content = list ()

    def run(self):
        logger = logging.getLogger()
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        logger.info ('fetching %r ..', self.url)
        stime = time.time()
        req = requests.get (self.url, auth=(usernm, passwd))
        if 200 != req.status_code:
            logger.error (req.content)
            logger.error ('bbs-scene.org returned %s', req.status_code)
            return
        else:
            logger.info ('bbs-scene.org returned %d in %2.2fs',
                    req.status_code, time.time() - stime)

        # can throw exceptions when xml is invalid, as a thread, nobody needs
        # to catch it. theres some things that should be CDATA wrapped ..
        xml_nodes = xml.etree.ElementTree.XML(req.content).findall('node')
        for node in xml_nodes:
            self.content.append ((node.find('id').text, dict(
                ((key, node.find(key).text.strip()) for key in (
                'oneliner', 'alias', 'bbsname', 'timestamp',))),))

def wait_for(thread):
    # for dummy or small terminals, wait until a request
    # thread has gotten content before continuing, *up to t WAIT_FETCH seconds
    if thread.is_alive():
        echo ("\r\n\r\nfetching bbs-scene.org oneliners .. "
                "(%s)s\b\b%s" % (' ' * 2, '\b' * 2,))
        for num in range(WAIT_FETCH):
            echo ('%2d%s' % (WAIT_FETCH - num - 1, '\b' * 2,))
            if not thread.is_alive():
                return
            thread.join (1)
            if getch(0) == u'q':
                return

def chk_thread(thread):
    # check if bbs-scene.org thread finished, if so, farm
    # its data and send updates if there is one,
    logger = logging.getLogger()
    session = getsession()
    if thread is not None and not thread.is_alive():
        udb = DBProxy('oneliner')
        udbkeys = udb.keys()
        nlc = 0
        for key, value in thread.content:
            if key not in udbkeys:
                udb[key] = value
                nlc += 1
        if nlc:
            logger.info ('%d new entries', nlc)
            session.buffer_event ('oneliner_update', True)
        else:
            logger.info ('no new bbs-scene.org entries')
        return True

def add_oneline (msg):
    import time
    session = getsession()
    udb = DBProxy('oneliner')
    udb.acquire ()
    udb[max([int(key) for key in udb.keys()] or [0]) + 1] = {
        'oneliner': msg,
        'alias': getsession().handle,
        'bbsname': ini.CFG.get('system', 'bbsname'),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    udb.release ()
    session.buffer_event ('oneliner_update', True)
    session.send_event ('global', ('oneliner_update', True))

def get_oltxt():
    term = getterminal()
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    hist= [(int(k), v) for (k, v) in DBProxy('oneliner').iteritems()]
    hist.sort ()
    output = list()
    for idx, onel in hist[BUF_HISTORY * -1:]:
        color = colors[int(idx) % len(colors)]
        atime = timeago(time.time() - time.mktime (
            time.strptime(onel['timestamp'], '%Y-%m-%d %H:%M:%S'))).strip()
        output.append (u''.join((
            term.bold_white('('), color(onel['alias']),
            term.bold_black(u'/'), onel['bbsname'],
            term.bold_white(u')'), color(u': '),
            Ansi(onel['oneliner']).decode_pipe(),
            term.bold_black(u'  /'), color(atime),
            term.bold_black(u' ago'),)))
    return output[(BUF_HISTORY * -1):]

def get_selector(selection=u'No'):
    term = getterminal ()
    selector = Selector(yloc=term.height - 1,
            xloc=(term.width / 2) - 25,
            width=50, left=u'Yes', right=u'No')
    selector.keyset['left'].extend((u'y', u'Y'))
    selector.keyset['right'].extend((u'y', u'Y'))
    selector.selection = selection
    selector.colors['selected'] = term.green_reverse
    return selector

def get_pager():
    term = getterminal ()
    xloc = max(3, (term.width / 2) - 50)
    width = min(term.width - 6, 100)
    pager = Pager(yloc=9, xloc=xloc, height=term.height - 12, width=width)
    pager.colors['border'] = term.blue
    return pager

def banner():
    term = getterminal()
    output = u''
    output += u'\r\n\r\n'
    if term.width >= 78:
        output += term.home + term.normal + term.clear
        # xzip's ansi is line-clean, center-align with terminal width,
        art = open(os.path.join(
            os.path.dirname(__file__), 'art', 'ol.ans')).readlines()
        max_ans = max([len(Ansi(from_cp437(line))) for line in art])
        for line in art:
            padded = Ansi(from_cp437(line)).center(max_ans)
            output += term.normal + term.blue # minor fix for this art ;/
            output += Ansi(padded).center(term.width).rstrip() + '\r\n'
    return output + term.normal

def redraw(pager, selector):
    session, term = getsession(), getterminal()
    session.flush_event ('oneliner_update')
    pager.update(u'\n'.join(get_oltxt()))
    pager.move_end ()
    pager.colors['border'] = term.white
    pager.glyphs['left-vert'] = u' '
    pager.glyphs['right-vert'] = u' '
    prompt_ole = u'SAY somethiNG ?!'
    output = u''
    output += pager.refresh() + pager.border()
    output += term.move(selector.yloc - 2, selector.xloc)
    output += term.bold_green (prompt_ole.center(selector.width).rstrip())
    output += term.clear_eol + selector.refresh()
    return output

def dummy_pager():
    term = getterminal()
    tail = 10
    indent = 4
    prompt_ole = u'SAY somethiNG ?!'
    echo (u'\r\n\r\n')
    for record in get_oltxt()[(tail * -1):]:
        # convert from record to a width-wrapped, indented
        # text-wrapped record, for real small terminals ^_*
        wrapped = Ansi(record.rstrip()).wrap(term.width - indent)
        echo ((u'\r\n' + u' ' * indent).join(wrapped.split(u'\r\n')) + u'\r\n')
    echo (term.normal + u'\r\n\r\n')
    echo (prompt_ole + u' [yn]')
    while True:
        ch = getch()
        if ch in (u'n', u'N', u'q', term.KEY_EXIT):
            break
        if ch in (u'y', u'Y'):
            return saysomething (dumb=True)
    return

def saysomething (dumb=True):
    session, term = getsession(), getterminal()
    prompt_api = u'MAkE AN ASS Of YOURSElf ON bbS-SCENE.ORG?!'
    prompt_say = u'SAY WhAt ?! '
    #heard_msg = u'YOUR MESSAGE hAS bEEN VOiCEd.'
    heard_api = u'YOUR MESSAGE hAS bEEN brOAdCAStEd.'
    logger = logging.getLogger()

    yloc = term.height - 3
    xloc = max(0, ((term.width / 2) - (MAX_INPUT / 2)))
    if dumb:
        echo (u'\r\n\r\n' + term.bold_blue(prompt_say))
    else:
        echo (term.move(yloc, xloc) or u'\r\n\r\n')
        echo (term.bold_blue(prompt_say))
    ole = LineEditor(MAX_INPUT)
    ole.highlight = term.green_reverse
    oneliner = ole.read ()
    if oneliner is None or 0 == len(oneliner.strip()):
        if not dumb:
            # clear input line,
            echo (term.normal + term.move(yloc, 0) + term.clear_eol)
        return None

    session.user['lastliner'] = time.time()
    # post local-onlyw hen bbs-scene.org is not configured
    if not ini.CFG.has_section('bbs-scene'):
        add_oneline (oneliner.strip())
        return None
    if dumb:
        # post to bbs-scene.org ?
        echo ('\r\n\r\n' + bold_blue(prompt_api) + u' [yn]')
        ch = getch(1)
        while ch not in (u'y', u'Y', u'n', u'N'):
            ch = getch()
        if ch in (u'n', u'N'):
            #  no? then just post locally
            add_oneline (oneliner.strip())
            return
    else:
        # fancy prompt, 'post to bbs-scene.org?'
        sel = get_selector()
        sel.colors['selected'] = term.red_reverse
        echo (term.move(sel.yloc-1, sel.xloc) or ('\r\n\r\n'))
        echo (term.blue_reverse(prompt_api.center(sel.width)))
        echo (sel.refresh())
        while not sel.selected and not sel.quit:
            echo (sel.process_keystroke(getch()))
        session.buffer_event('refresh', 'dirty')
        if sel.quit or sel.selection == sel.right:
            echo (term.normal + term.move(yloc, 0) + term.clear_eol)
            echo (term.move (sel.yloc, 0) + term.clear_eol)
            return None

    # This is an AJAX effect.
    # Dispatch a thread to fetch updates, whose callback
    # will cause the database and pager to update.
    url = 'http://bbs-scene.org/api/onelinerz.xml'
    usernm = ini.CFG.get('bbs-scene', 'user')
    passwd = ini.CFG.get('bbs-scene', 'pass')
    data = {u'oneliner': oneliner.strip(),
            u'alias': session.user.handle,
            u'bbsname': ini.CFG.get('system', 'bbsname')}
    # post to bbs-scene.rog
    req = requests.post (url, auth=(usernm, passwd), data=data)
    if (req.status_code != 200 or
            (xml.etree.ElementTree.XML (req.content)
                .find('success').text != 'true')):
        echo (u'\r\n\r\n%srequest failed,\r\n', term.clear_eol)
        echo (u'%r' % (req.content,))
        echo (u'\r\n\r\n%s(code : %s).\r\n', term.clear_eol, req.status_code)
        echo (u'\r\n%sPress any key ..', term.clear_eol)
        logger.warn ('bbs-scene.org api request failed')
        getch ()
        return
    logger.info ('bbs-scene.org api (%d): %r/%r', req.status_code,
            session.user.handle, oneliner.strip())
    thread = FetchUpdates()
    thread.start ()
    if not dumb:
        # clear line w/input bar,
        echo (term.normal + term.move(yloc, 0) + term.clear_eol)
        # clear line w/selector
        echo (term.move (sel.yloc, 0) + term.clear_eol)
    else:
        echo ('\r\n\r\n' + heard_api)
        getch (2)
    return thread

def main ():
    session, term = getsession(), getterminal()
    pager, selector = get_pager(), get_selector()

    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates()
        thread.start ()
        session.activity = u'one-liners [bbs-scene.org]'
    else:
        session.activity = u'one-liners'

    # flag a pager update,
    dirty = True
    # force screen clear on first loop,
    session.buffer_event ('refresh', ('init',))
    while True:
        # 1. calculate and redraw screen,
        # or enter dumb pager mode (no scrolling)
        if session.poll_event('refresh'):
            pager, selector = get_pager(), get_selector(selector.selection)
            echo (banner())
            dirty = True
        if chk_thread (thread):
            thread = None
        if session.poll_event('oneliner_update'):
            #echo (banner())
            dirty = True
        if dirty and (session.env.get('TERM') != 'unknown' and
                not session.user.get('expert', False)
                and term.width >= 78 and term.height >= 20):
            # smart terminal
            echo (redraw(pager, selector))
            dirty = False
        elif dirty:
            # dumb terminal
            if thread is not None:
                wait_for (thread)
            if chk_thread (thread):
                thread = None
            echo (u'\r\n\r\n')
            return dummy_pager()

        # 2. detect and process keyboard input,
        inp = getch (1)
        if inp is not None:
            # input is multiplexed to both interfaces
            echo (pager.process_keystroke (inp))
            echo (selector.process_keystroke (inp))

            # selected 'yes' & return, 'say something'
            if (selector.selected and selector.selection == selector.left):
                # re-assign thread so that it is checked for updates
                thread = saysomething (dumb=False)
                # undo 'selected' state of yes/no bar,
                selector.selected = False

            # quit 'q', or selected 'no' & return
            elif (selector.selected and selector.selection == selector.right
                    or pager.quit):
                return
