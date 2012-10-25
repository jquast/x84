""" oneliners for x/84, http://github.com/jquast/x84

  To use the (optional) http://bbs-scene.org API,
  configure a section in your .ini file:

    [bbs-scene]
    user = my@email-addr.ess
    pass = my-plaintext-password
"""
import threading
import time
import requests
import xml.etree.ElementTree

#pylint: disable=W0614
#        Unused import from wildcard import
from bbs import *

# bbs-scene.org API is 50-character limit max
MAX_INPUT = 50
# one message per 24 hours, 0 to disable
BUF_HISTORY = 100
# limit XML/API requests limit
XML_HISTORY = 84
# in dumb terminal mode or expert mode, wait up to
# this long for bbs-scene.org updates ('x' cancels)
WAIT_FETCH = 10

class FetchUpdates(threading.Thread):
    """
    Dispatch request to find updates to bbs-scene.org's oneliner's
    """
    url = 'http://bbs-scene.org/api/onelinerz?limit=%d' % (XML_HISTORY,)
    content = list ()

    def run(self):
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
            logger.info ('bbs-scene.org returned %d records in %2.2fs',
                    req.status_code, time.time() - stime)

        # can throw exceptions when xml is invalid
        xml_nodes = xml.etree.ElementTree.XML(req.content).findall('node')
        for node in xml_nodes:
            self.content.append ((node.find('id').text, dict(
                ((key, node.find(key).text.strip()) for key in (
                'oneliner', 'alias', 'bbsname', 'timestamp',))),))
        logger.info ('stored %d updates from bbs-scene.org', len(self.content))

def wait_for(thread):
    if thread.is_alive():
        echo ("\r\n\r\nfetching bbs-scene.org oneliners .. "
                "(%s)s\b\b%s" % (' ' * 2, '\b' * 2,))
        for num in range(WAIT_FETCH):
            echo ('%2d%s' % (WAIT_FETCH - num - 1, '\b' * 2,))
            if not thread.is_alive():
                return
            thread.join (1)
            if getch(0) == u'q':
                # undocumented: q cancels -- in case it ever goes down D:
                return

def chk_thread(thread):
    # check if bbs-scene.org thread finished
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
            broadcastevent ('oneliner_update')
        return True

def addline(msg):
    #import time
    #udb = DBProxy('oneliner')
    #udb.acquire (timeout=float('inf'), stale=3)
    #udb[max([int(key) for key in udb.keys()] or [0]) + 1] = {
    #    'oneliner': msg,
    #    'alias': session.handle,
    #    'bbsname': ini.CFG.get('system', 'bbsname'),
    #    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    #}
    #udb.release ()
    broadcastevent ('oneliner_update')

def get_oltxt():
    term = getterminal()
    output = list()
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    for idx, onel in sorted(DBProxy('oneliner').items())[BUF_HISTORY * -1:]:
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

def redraw(pager, selector):
    term = getterminal()
    output = term.home + term.normal + term.clear
    flushevent ('oneliner_update')
    # xzip's ansi is line-clean, center-align with terminal width,
    art = open('default/art/ol.ans').readlines()
    max_ans = max([len(Ansi(from_cp437(line))) for line in art])
    for line in art:
        padded = Ansi(from_cp437(line)).center(max_ans)
        output += Ansi(padded).center(term.width).rstrip()
        output += term.normal + '\r\n'
    pager.update(u'\n'.join(get_oltxt()))
    pager.move_end ()
    output += (pager.refresh() + pager.border() +
            selector.refresh() + selector.border ())
    return output

def dummy_pager():
    term = getterminal()
    tail = 10
    indent = 4
    echo ('\r\n\r\n')
    for record in get_oltxt()[(tail * -1):]:
        # convert from record to a width-wrapped, indented
        # text-wrapped record, for real small terminals ^_*
        wrapped = Ansi(record.rstrip()).wrap(term.width - indent)
        echo (('\r\n' + ' ' * indent).join(wrapped.split('\r\n'))+'\r\n')
    echo (term.normal + '\r\n\r\n')
    echo ('SAY SOMEthiNG [yn]  ?!\b\b\b')
    while True:
        ch = getch()
        if ch in (u'n', u'N', u'q', term.KEY_EXIT):
            break
        if ch in (u'y', u'Y'):
            saysomething ()
    return

def saysomething ():
    term = getterminal()
    yloc = term.height - 3
    xloc = min(0, ((term.width / 2) - (MAX_INPUT / 2)))
    echo (term.move(yloc, xloc) or u'\r\n\r\n')
    oneliner = LineEditor(MAX_INPUT).read ()
    if oneliner is not None and 0 != len(oneliner):
        session.user['lastliner'] = time.time()
        if not ini.CFG.has_section('bbs-scene'):
            # always post local,
            addline (oneliner)
            return
        selector = get_selector()
        echo (term.move(selector.yloc-1, selector.xloc) or ('\r\n\r\n'))
        echo ('MAkE AN ASS Of YOURSElf ON bbS-SCENE.ORG?!')
        echo (selector.refresh())
        while not selector.selected and not selector.quit:
            echo (selector.process_keystroke(getch()))
        if selector.quit or selector.selection == selector.right:
            return
        if selector.selection == selector.left:
            url = 'http://bbs-scene.org/api/onelinerz.xml'
            usernm = ini.CFG.get('bbs-scene', 'user')
            passwd = ini.CFG.get('bbs-scene', 'pass')
            bbsname = ini.CFG.get('system', 'bbsname')
            # post to bbs-scene.rog
            req = requests.post (url, auth=(usernm, passwd), data={
                'oneliner': msg, 'alias': session.handle, 'bbsname': bbsname,})
            if (req.status_code != 200 or
                    (xml.etree.ElementTree.XML (req.content)
                        .find('success').text != 'true')):
                echo ('\r\n\r\n%srequest failed,\r\n', term.clear_eol)
                echo (('\r\n%s'%(term.clear_eol,)).join (req.content))
                echo ('\r\n\r\n%s(code : %s).\r\n', term.clear_eol, req.status_code)
                echo ('\r\n%sPress any key ..', term.clear_eol)
                getch ()
                return
            thread = FetchUpdates()
            thread.start ()
            return

def main ():
    session, term = getsession(), getterminal()
    session.activity = 'one-liners'

    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates()
        thread.start ()
        session.activity = 'one-liners [bbs-scene.org]'

    pager, selector = get_pager(), get_selector()
    dirty = True
    waited = False
    while True:
        # 1. calculate and redraw screen
        # screen resize
        if pollevent('refresh'):
            pager, selector = get_pager(), get_selector(selector.selection)
            dirty = True
        # bbs-scene.org update
        if chk_thread (thread):
            thread = None
            dirty = True
        # global signal for new oneliners (like irc!)
        if pollevent('oneliner_update'):
            dirty = True
        # re-draw smart terminal (pager, y/n selector)
        if dirty and (session.env.get('TERM') != 'unknown' and
                not session.user.get('expert', False)
                and term.width >= 78 and term.height >= 20):
            echo (term.home + term.clear)
            echo (redraw(pager, selector))
            dirty = False
        elif dirty:
            # enter dumb terminal mode,
            if thread is not None:
                wait_for (thread)
            if chk_thread (thread):
                thread = None
            echo ('\r\n\r\n')
            return dummy_pager()

        # 2. detect and process keyboard input,
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
