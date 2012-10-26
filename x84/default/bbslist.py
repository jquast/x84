
""" bbs lister for x/84, http://github.com/jquast/x84

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

# ideal pager window width, can be smaller tho !
PAGER_WIDTH = 100
# MAX BBS NAME
MAX_BBSNAME = 30
# MAX LOCATION
MAX_LOCATION = 20
# a good union choie of bbs-scene fetch and local keys,
XML_KEYS = ('bbsname', 'sysop', 'software', 'address', 'port', 'location',)
# how long to wait in dummy mode
WAIT_FETCH = 8

#pylint: disable=W0614
#        Unused import from wildcard import
from bbs import *

class FetchUpdates(threading.Thread):
    url = 'http://bbs-scene.org/api/bbslist.php'
    content = list ()

    def run(self):
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
    if thread is not None and not thread.is_alive():
        udb = DBProxy('bbslist')
        udbkeys = udb.keys()
        nlc = 0
        for key, value in thread.content:
            if key not in udbkeys:
                udb[key] = value
                nlc += 1
        if nlc:
            logger.info ('%d new entries', nlc)
            broadcastevent ('bbslist_update')
        else:
            logger.info ('no new bbs-scene.org entries')
        return True


#            echo ('%-27s %-16s %-18s %s' \
#              % ('- BBS Name', 'Software', '+o', 'rating -'))

def calc_rating(ratings):
    term = getterminal()
    #pylint: disable=W0612
    total = sum([float(rating) for (usr, rating) in ratings] or [0.0])
    stars = total / (len(ratings) or 1)
    return ((term.bright_green('*') * int(max(4, stars))
                + term.bold_black('-') * int(4 - stars)) if stars > 3.5
            else (term.bright_white('*') * int(max(4, stars))
                + term.bold_black('-') * int(4 - stars)) if stars > 2.9
            else (term.bright_blue('*') * int(max(4, stars))
                + term.bold_black('-') * int(4 - stars)))


#            elif bbsname and data in u'iI':
#                dirty = True
#                p = ParaClass (y=10, x=2, w=76, h=14, xpad=1, ypad=1)
#                p.lowlight ()
#                cr = ''
#                for nick, comment in comments:
#                    rating = None
#                    for r_nick, rating in ratings:
#                        if r_nick == nick:
#                            break
#                        rating = None
#                    cr += '%s%s%s%s\n  %s\n' % \
#                        (term.bold_blue, nick, term.normal,
#                            ' %s%s%s:' % (term.bold_red,'*'
# *rating,term.normal)
#                            if rating else ':',
#                         comment)
#                p.update ('%saddress: telnet://%s%s\nsysop: %s\n' \
#                           '%ssoftware:%s\n%s%s' \
#                           % (term.normal, host,
#                             ':%s' % (port,) if port not in (23, None)
# else '',
#                             sysop,
#                             'number of ratings: %i\n' % (len(ratings)) \
#                                 if ratings else '',
#                             software, '\n' if comments else '', cr ))
#                p.title ('<return/spacebar> return to list', align='top')
#                k = getch()
#                if k in (' ',term.KEY_ENTER, term.KEY_ESCAPE):
#                    continue
#                p.run (k)
#

def get_bbslist():
    """
    Returns tuple, (bbs_key, display_string)
    """
    output = list()
    term = getterminal()
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    flushevent ('bbslist_update')
    bbslist = DBProxy('bbslist').items()
    by_software = dict()

    # sort by bbs software ^_*
    def abbr(software):
        return u''.join((ch.lower()
            for ch in software.split()[0]
            if ch.isalpha()))
    for key, bbs in bbslist:
        group_by = abbr(bbs['software'])
        by_software[group_by] = (by_software.get(group_by, list())
                + [(key, bbs)])
    for idx, (bbs_sw, bbs_keys) in enumerate(sorted(by_software.items())):
        color = colors[int(idx) % len(colors)]
        output.append ((None, term.bold_black('-' * 4),
            term.white('-'), term.bold_white('-('),
            color('%2d' % (len(bbs_keys))), term.bold_white(')'),
            color(bbs_sw),))
        for key, bbs in bbslist:
            output.append ((key, u''.join((
                ( bbs['bbsname'].rjust(MAX_BBSNAME)),
                u'  ', bbs['location'].rjust(MAX_LOCATION),
                u'  ', bbs['sysop'].rjust(ini.CFG.getint('nua', 'max_user')),
                u'  ', calc_rating (bbs.get('ratings', list())),
                u' %-2d' % (len(bbs.get('comments', list()))),)) ))
    return output

def get_bbsinfo(key):
    if key is None:
        return u'no selection ..'
    # XX theres that 50 again
    if not key in DBProxy('bbslist'):
        return u' -    n/a   -'.center(50)
    return u'xidk'

def get_lightbar(selection=None):
    term = getterminal ()
    # 50 is just estimated ...
    lightbar = Lightbar(height=max(5, term.height - 15), width=50,
            yloc=10, xloc=max(0, (term.width / 2) - (50 / 2)))
    lightbar.keyset['enter'].extend((u't', u'T'))
    lightbar.update (get_bbslist())
    lightbar.colors['selected'] = term.green_reverse
    lightbar.colors['border'] = term.green
# how do we select an item?
#    if selection is not None:
#        for key, value in selection.content:
#            if key == selection:
#                lightbar.selection =
    return lightbar

def get_pager():
    term = getterminal ()
    # calc bottom-edge of lightbar (see: get_lightbar!)
    yloc = min(16, 10 + max(5, term.height - 15))
    xloc = max(3, (term.width / 2) - (PAGER_WIDTH / 2))
    width = min(term.width - 6, PAGER_WIDTH)
    height = min(3, (term.height - yloc - 3))
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
        for line in open('default/art/bbslist.asc'):
            output += line.center(72).rstrip() + '\r\n'
    return output + term.normal

def redraw(pager, lightbar):
    output = u''
    pager.update(u'\n'.join(get_bbsinfo(lightbar.selected)))
    output += lightbar.refresh() + pager.refresh()
    output += lightbar.border() + pager.border()
    return output

def dummy_pager():
    term = getterminal()
    indent = 6
    def disp_entry(char, blurb):
        return (term.bold_blue('(') + term.blue_reverse(char)
                + term.bold_blue + ')' + term.bright_white (' '+blurb))
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
    term = getterminal()
    echo (term.move(term.height, 0))
    empty_msg = u'VAlUE iS NOt OPtiONAl.'
    cancel_msg = u"ENtER 'quit' tO CANCEl."
    saved_msg = u'SAVED AS RECORd id %s.'
    bbs = dict ()
    for key in XML_KEYS:
        splice = len(key) - (len(key) / 3)
        prefix = (u'\r\n\r\n  '
                + term.boldblue(key[:splice])
                + term.bold_black(key[splice:])
                + term.bright_white(': '))
        led = LineEditor(40) # !?
        led.highlight = term.green_reverse
        while True:
            echo (prefix)
            value = led.read()
            if value is not None and (
                    value.strip().lower().replace(',','') == 'quit'):
                return
            if key in (u'bbsname', u'software', u'address'):
                if value is None or 0 == len(value):
                    echo (u'\r\n' + term.bold_red(empty_msg))
                    echo (u'\r\n' + cancel_msg)
                    continue
            if key in (u'port') and value is None or 0 == len(value):
                value = '23'
            # TODO: telnet test
            bbs[key] = value
            break
    bdb = DBProxy('bbslist')
    bdb.acquire ()
    max_id = max([int(key) for key in bdb.iterkeys()])
    bdb[max_id + 1] = bbs
    bdb.release ()
    echo ('\r\n\r\n' + saved_msg % (max_id + 1) + '\r\n')
    broadcastevent ('bbslist_update')
    return

        # post to bbs-scene.org
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


def process_keystroke(inp, key):
    session = getsession ()
    if key is None:
        return None
    elif inp is None:
        return False
    elif type(inp) is int:
        return False
    elif inp.lower() == 't':
        bbs = DBProxy('bbslist')[key]
        gosub ('telnet', bbs['address'], bbs['port'],)
    elif inp.lower() == 'a':
        add_bbs ()
    elif inp.lower() == 'c':
        add_comment (key)
    elif inp.lower() == 'r':
        rate_bbs (key)
    elif inp.lower() == 'd' and session.user.is_sysop:
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
        if pollevent('refresh'):
            pager, lightbar = get_pager(), get_lightbar()
            echo (banner())
            dirty = True
        if chk_thread (thread):
            thread = None
        if pollevent('bbslist_update'):
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
            logger.info ('selected key, output (%s, %r)', key, output)
            # pressed return, 'telnet !'
            if (lightbar.selected):
                #pylint: disable=W0612
                #        Unused variable, 'output'
                bbs = DBProxy('bbslist')[lightbar.selection[0]]
                gosub ('telnet', bbs['address'], bbs['port'])
                # undo 'selected' state of lightbar
                lightbar.selected = False
                # force screen clear to erase prompts/etc,
                session.buffer_event ('refresh', ('redraw',))
            elif process_keystroke(inp, lightbar.selection[0]):
                # processed as bbs-lister keystroke ('r'ate, etc.,)
                session.buffer_event('refresh', ('redraw',))

