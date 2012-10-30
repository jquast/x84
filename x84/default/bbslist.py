
""" bbs lister for x/84, http://github.com/jquast/x84

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

# a good union choie of bbs-scene fetch and local keys,
XML_KEYS = ('bbsname', 'sysop', 'software', 'address', 'port', 'location',)
# how long to wait in dummy mode
WAIT_FETCH = 8

#pylint: disable=W0614
#        Unused import from wildcard import
from x84.bbs import *

class FetchUpdates(threading.Thread):
    url = 'http://bbs-scene.org/api/bbslist.php'
    content = list ()

    def run(self):
        logger = logging.getLogger()
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        logger.info ('fetching %r ..', self.url)
        stime = time.time()
        #pylint: disable=E1103
        req = requests.get (self.url, auth=(usernm, passwd))
        if 200 != req.status_code:
            logger.error (req.content)
            logger.error ('bbs-scene.org returned %s', req.status_code)
            return
        else:
            logger.info ('bbs-scene.org returned %d in %2.2fs',
                    req.status_code, time.time() - stime)

        # can throw exceptions when xml is invalid
        xml_nodes = xml.etree.ElementTree.XML(req.content).findall('node')
        for node in xml_nodes:
            self.content.append ((node.find('id').text, dict(
                ((key, node.find(key).text.strip()) for key in XML_KEYS)),))

def wait_for(thread):
    if thread.is_alive():
        echo ("\r\n\r\nfetching bbs-scene.org bbs list.. "
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
    logger = logging.getLogger()
    session = getsession()
    if thread is not None and not thread.is_alive():
        udbkeys = DBProxy('bbslist').keys()
        nlc = 0
        for key, value in thread.content:
            if key not in udbkeys:
                DBProxy('bbslist')[key] = value
                #DBProxy('bbslist', 'comments')[key] = dict()
                #DBProxy('bbslist', 'ratings')[key] = dict()
                print "SAVED", repr(DBProxy('bbslist')[key])
                nlc += 1
        if nlc:
            logger.info ('%d new entries', nlc)
            session.send_event ('global', ('bbslist_update', True))
            session.buffer_event ('bbslist_update', True)
        else:
            logger.info ('no new bbs-scene.org entries')
        return True


def calc_rating(ratings):
    total = sum([float(rating) for (usr, rating) in ratings] or [0.0])
    stars = max(4, total / (len(ratings) or 1))
    return u' ' + u'*' * (stars - (4 - stars))
    #return ((term.bold_green('*') * int(min(4, stars))
    #            + term.bold_black('-') * int(4 - stars)) if stars > 3.5
    #        else (term.bold_white('*') * int(min(4, stars))
    #            + term.bold_black('-') * int(4 - stars)) if stars > 2.9
    #        else (term.bold_blue('*') * int(min(4, stars))
    #            + term.bold_black('-') * int(4 - stars)))

def get_bbslist():
    """
    Returns tuple, (bbs_key, display_string)
    """
    session, term = getsession(), getterminal()
    output = list()
    #colors = (term.bold_white, term.bold_green, term.bold_blue)
    session.flush_event ('bbslist_update')
    bbslist = DBProxy('bbslist').items()
    #ratings = DBProxy('bbslist', 'ratings').items()
    ratings = list()
    comments = list()
    by_software = dict()
    max_bbs = 25
    max_loc = 20
    max_sysop = 15



    # sort by bbs software ^_*
    def abbr(software):
        return u''.join((ch.lower()
            for ch in software.split()[0]
            if ch.isalpha()))
    for key, bbs in bbslist:
        group_by = abbr(bbs['software'])
        by_software[group_by] = (by_software.get(group_by, list())
                + [(key, bbs)])
    max_sysop = ini.CFG.getint('nua', 'max_user')
    for idx, (bbs_sw, bbs_keys) in enumerate(sorted(by_software.items())):
        output.append ((None, (u' %s  %2d ' % (bbs_sw,
            len(bbs_keys))).rjust(64, '-')))
        for key, bbs in bbs_keys:
            location = bbs['location'].strip()
            while len(location) > max_loc and ' ' in location:
                location = u' '.join(location.split()[:-1])
            location = location[:max_loc].strip()
            bbsname = bbs['bbsname'].strip()
            if len(bbsname) > max_bbs:
                bbsname = bbsname[:max_bbs-1] + '$'
            sysop = bbs['sysop'].strip()
            while len(sysop) > max_sysop and ' ' in sysop:
                sysop= u' '.join(sysop.split()[:-1])
            if len(sysop) > max_sysop:
                sysop = sysop[:max_sysop-1] + '$'
            output.append ((key,
                bbsname.ljust(max_bbs)
                + location.ljust(max_loc)
                + sysop.rjust(max_sysop)
                + calc_rating (ratings)
                + u' %-2d' % (len(comments))))
    #print output
    return output

def get_bbsinfo(key):
    term = getterminal()
    bbs = DBProxy('bbslist')[key]
    rstr = u''
    rstr += (term.blue('bbsname')
            + term.bold_blue(u': ')
            + bbs['bbsname']
            + term.bold_blue('  +o ')
            + bbs['sysop'] + u'\n')
    rstr += (term.blue('address')
            + term.bold_blue(': ')
            + bbs['address']
            + term.bold_blue(':')
            + bbs['port'] + u'\n')
    rstr += (term.blue('software')
            + term.bold_blue(': ')
            + bbs['software']
            + u', ' + term.blue('location')
            + term.bold_blue(': ')
            + bbs['location'] + '\n')
    rstr += u'\n'
    comments = DBProxy('bbslist', 'comments')[key]
    for handle, comment in comments.iteritems():
        rstr += '\n' + term.green(handle)
        rstr += term.bold_green(':')
        rstr += comment
    rstr += u'\n'

def get_lightbar(position=None):
    term = getterminal ()
    lightbar = Lightbar(height=max(5, term.height - 20), width=67, yloc=8,
            xloc=max(1, (term.width / 2) - (67 / 2)))
    lightbar.keyset['enter'].extend((u't', u'T'))
    lightbar.update (get_bbslist())
    lightbar.colors['selected'] = term.green_reverse
    lightbar.colors['border'] = term.green
    if position is not None:
        lightbar.position = position
    return lightbar

def get_pager():
    term = getterminal ()
    # calc bottom-edge of lightbar (see: get_lightbar!)
    yloc = 15
    xloc = max(1, (term.width/2)-(50/2))
    width = max(term.width-2, 50)
    height = max(3, (term.height - yloc - 2))
    pager = Pager(height, width, yloc, xloc)
    pager.colors['border'] = term.blue
    return pager

def banner():
    term = getterminal()
    output = u''
    output += '\r\n\r\n'
    if term.width >= 72:
        output += term.home + term.normal + term.clear
        # spidy's ascii is 72-wide (and, like spidy, total nonsense ..,)
        for line in open(os.path.join
                (os.path.dirname(__file__), 'art', 'bbslist.asc')):
            output += line.center(72).center(term.width).rstrip() + '\r\n'
    return output + term.normal

def redraw(pager, lightbar):
    term = getterminal()
    output = u''
    if lightbar.selection != (None, None):
        print 'key', lightbar.selection
        info = get_bbsinfo(lightbar.selection[0])
        print repr(info)
        pager.update (info)
    else:
        pager.update (u' -- no selection --'.center(pager.visible_width))
    output += lightbar.refresh()
    output += pager.refresh()
    output += lightbar.border()
    #output += pager.border()
    output += lightbar.footer (
            term.bold_green(' a') + '/' + term.green('dd')
            + term.bold_green(' c') + '/' + term.green('omment')
            + term.bold_green(' r') + '/' + term.green('rate')
            + term.bold_green(' t') + '/' + term.green('elnet'))
    return output + term.nroaml

def dummy_pager():
    term = getterminal()
    indent = 6
    def disp_entry(char, blurb):
        return (term.bold_blue('(') + term.blue_reverse(char)
                + term.bold_blue + ')' + term.bold_white (' '+blurb))
    prompt = u', '.join(disp_entry(char, blurb) for char, blurb in (
        ('a', 'add',), ('c', 'comment',), ('r', 'rate',),
        ('t', 'telnet',), ('q', 'quit',)))
    prompt_bye = u'press any key ..'
    echo (u'\r\n\r\n')
    for num, (key, line) in enumerate(get_bbslist()):
        # convert from record to a width-wrapped, indented
        # text-wrapped record, for real small terminals ^_*
        wrapped = (u'%s. ' % (key, ) +  Ansi(line.rstrip())
                .wrap(term.width - indent))
        echo ((u'\r\n' + u' ' * indent).join(wrapped.split(u'\r\n')) + u'\r\n')
        if num and (num % (term.height - 4) == 0):
            # moar prompt,
            while True:
                echo ('\r\n' + prompt)
                echo (u' -- ' + disp_entry('[m]', 'moar'))
                inp = getch()
                if inp in (u'q', 'Q'):
                    return # quit
                if process_keystroke(inp, key):
                    # noop, if call performed action (True),
                    # re-display prompt again,
                    continue
                break # any other key is default ('m'oar)
    echo (u'\r\n\r\n')
    echo (prompt_bye)
    getch ()
    return

def add_bbs():
    session, term = getsession(), getterminal()
    echo (term.move(term.height, 0))
    empty_msg = u'VAlUE iS NOt OPtiONAl.'
    cancel_msg = u"ENtER 'quit' tO CANCEl."
    saved_msg = u'SAVED AS RECORd id %s.'
    bbs = dict ()
    for key in XML_KEYS:
        splice = len(key) - (len(key) / 3)
        prefix = (u'\r\n\r\n  '
                + term.bold_blue(key[:splice])
                + term.bold_black(key[splice:])
                + term.bold_white(': '))
        led = LineEditor(40) # !?
        led.highlight = term.green_reverse
        while True:
            echo (prefix)
            value = led.read()
            if value is not None and (
                    value.strip().lower().replace(',','') == 'quit'):
                return
            if key in ('bbsname', 'software', 'address'):
                if value is None or 0 == len(value):
                    echo (u'\r\n' + term.bold_red(empty_msg))
                    echo (u'\r\n' + cancel_msg)
                    continue
            if key in ('port') and value is None or 0 == len(value):
                value = '23'
            # TODO: telnet connect test, of course !
            bbs[key] = value
            break
    bdb = DBProxy('bbslist')
    #cdb = DBProxy('bbslist', 'comments')
    #rdb = DBProxy('bbslist', 'ratings')
    bdb.acquire ()
    #cdb.acquire ()
    #rdb.acquire ()
    key = max([int(key) for key in bdb.keys()] or [0]) + 1
    bdb[key] = bbs
    print 'saved', repr(bdb[key])
    #cdb[key] = dict()
    #rdb[key] = dict()
    bdb.release ()
    #cdb.release ()
    #rdb.release ()
    echo ('\r\n\r\n' + saved_msg % (key) + '\r\n')
    session.send_event ('global', ('bbslist_update', True))
    session.buffer_event ('bbslist_update', True)
    return

#        # post to bbs-scene.org
#        url = 'http://bbs-scene.org/api/onelinerz.xml'
#        usernm = ini.CFG.get('bbs-scene', 'user')
#        passwd = ini.CFG.get('bbs-scene', 'pass')
#        data = {u'oneliner': oneliner.strip(),
#                u'alias': session.user.handle,
#                u'bbsname': ini.CFG.get('system', 'bbsname')}
#        # post to bbs-scene.rog
#        req = requests.post (url, auth=(usernm, passwd), data=data)
#        if (req.status_code != 200 or
#                (xml.etree.ElementTree.XML (req.content)
#                    .find('success').text != 'true')):
#            echo (u'\r\n\r\n%srequest failed,\r\n', term.clear_eol)
#            echo (u'%r' % (req.content,))
#            echo (u'\r\n\r\n%s(code : %s).\r\n', term.clear_eol,
#                     req.status_code)
#            echo (u'\r\n%sPress any key ..', term.clear_eol)
#            logger.warn ('bbs-scene.org api request failed')
#            getch ()
#            return
#        logger.info ('bbs-scene.org api (%d): %r/%r', req.status_code,
#                session.user.handle, oneliner.strip())
#        thread = FetchUpdates()
#        thread.start ()
#        if not dumb:
#            # clear line w/input bar,
#            echo (term.normal + term.move(yloc, 0) + term.clear_eol)
#            # clear line w/lightbar
#            echo (term.move (sel.yloc, 0) + term.clear_eol)
#        else:
#            echo ('\r\n\r\n' + heard_api)
#            getch (2)
#        return thread


def process_keystroke(inp, key=None):
    session = getsession ()
    if inp is None:
        return False
    elif type(inp) is int:
        return False
    elif inp.lower() == u't' and key is not None:
        bbs = DBProxy('bbslist')[key]
        gosub ('telnet', bbs['address'], bbs['port'],)
    elif inp.lower() == u'a':
        add_bbs ()
    elif inp.lower() == u'c' and key is not None:
        add_comment (key)
    elif inp.lower() == u'r' and key is not None:
        rate_bbs (key)
    elif inp.lower() == u'd' and session.user.is_sysop and key is not None:
        del DBProxy('bbslist')[key]
    else:
        return False # unhandled
    return True

def add_comment(key):
#            elif bbsname and data in u'Cc': # comment on bbs board
#                dirty=True
#                lightbar.clear ()
#                echo (lightbar.pos(2, 2) + term.normal)
#                echo ('comment: ')
#                echo (term.blue + term.reverse)
#                echo (' '*65 + '\b'*65)
#                new_comment = readline(65).strip()
#                if not new_comment:
#                    continue
#                echo (lightbar.pos(2, 8) + term.normal)
#                if session.handle in [u for u,c in comments]:
#                    echo ('change your comment for %s? [yn]' % (bbsname,))
#                else:
#                    echo ('add comment for %s? [yn] ' % (bbsname,))
#                yn=getch()
#                if yn not in 'yY':
#                    continue
#                new_comments = \
#                  [(u,c) for u,c in comments if u != session.handle] \
#                  + [(session.handle, new_comment)]
#                udb[bbsname] = (host, port, software, sysop, ratings,
#                  new_comments)
    pass


def rate_bbs(key):
#            elif bbsname and data in u'Rr': # rate a bbs board
#                dirty=True
#                lightbar.clear ()
#                echo (lightbar.pos(2, 6) + term.normal)
#                echo ('rate bbs [1-4]: ')
#                echo (term.blue + term.reverse)
#                echo (' '*1 + '\b'*1)
#                rate = getch()
#                if not rate.isdigit(): continue
#                try: rate = int(rate)
#                except ValueError: continue
#                echo (str(rate) + lightbar.pos(2, 8) + term.normal)
#                if session.handle in [u for u, rating in ratings]:
#                    echo (u'change your rating for %s to %i stars? [yn] ' \
#                      % (bbsname, rate,))
#                else:
#                    echo (u'rate %s with %i stars? [yn] ' % (bbsname, rate,))
#                yn=getch()
#                if type(yn) is int or yn not in u'Yy':
#                    continue
#                new_rating = \
#                  [(u,r) for u, r in ratings if u != session.handle] \
#                  + [(session.handle, rate)]
#                udb[bbsname] = (host, port, software, sysop, new_rating,
#                    comments)
    pass

def main ():
    session, term = getsession(), getterminal()
    pager, lightbar = get_pager(), get_lightbar()
    logger = logging.getLogger()

    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates()
        thread.start ()
        session.activity = u'bbs lister [bbs-scene.org]'
    else:
        session.activity = u'bbs lister'

    # flag a pager update,
    dirty = True
    # force screen clear on first loop,
    session.buffer_event ('refresh', ('init',))
    while True:
        # 1. calculate and redraw screen,
        # or enter dumb pager mode (no scrolling)
        if session.poll_event('refresh'):
            pager, lightbar = get_pager(), get_lightbar(lightbar.position)
            echo (banner())
            dirty = True
        if chk_thread (thread):
            thread = None
        if session.poll_event('bbslist_update'):
            dirty = True
        if dirty and (session.env.get('TERM') != 'unknown' and
                not session.user.get('expert', False)
                and term.width >= 72 and term.height >= 20):
            # smart terminal
            echo (redraw(pager, lightbar))
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
            # process as lightbar keystroke
            echo (lightbar.process_keystroke (inp))
            # process as pager keystroke
            echo (pager.process_keystroke (inp))
            # quit 'q',
            if (lightbar.quit or pager.quit):
                return
            key, output = lightbar.selection
            #echo (output)
            if process_keystroke(inp, key):
                # processed as bbs-lister keystroke ('r'ate, etc.,)
                logger.info ('handled %s, %s', inp, key)
                session.buffer_event('refresh', ('redraw',))
            #logger.info ('selected key, output (%s, %r)', key, output)
            # pressed return, 'telnet !'
            if lightbar.selected:
                #pylint: disable=W0612
                #        Unused variable, 'output'
                bbs = DBProxy('bbslist')[lightbar.selection[0]]
                gosub ('telnet', bbs['address'], bbs['port'])
                # undo 'selected' state of lightbar
                lightbar.selected = False
                # force screen clear to erase prompts/etc,
                session.buffer_event ('refresh', ('redraw',))
            else:
                logger.info

