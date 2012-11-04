
"""
bbs lister for x/84, http://github.com/jquast/x84

  To use the (optional) http://bbs-scene.org API,
  configure a section in your .ini file:

    [bbs-scene]
    user = my@email-addr.ess
    pass = my-plaintext-password

  Highly recommended.
"""
import xml.etree.ElementTree
import threading
import requests
import logging
import time
import math
import os

XML_KEYS = ('bbsname', 'sysop', 'software',
            'address', 'port', 'location',
            'notes', 'timestamp', 'ansi')
LWIDE = 25
PWIDE = 80

from x84.bbs import echo, ini, getch, getsession, DBProxy, LineEditor
from x84.bbs import Lightbar, Pager, getterminal, gosub, Ansi, from_cp437


class FetchUpdates(threading.Thread):
    url = 'http://bbs-scene.org/api/bbslist.php'
    content = list()

    def run(self):
        logger = logging.getLogger()
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        logger.info('fetching %r ..', self.url)
        stime = time.time()
        #pylint: disable=E1103
        req = requests.get(self.url, auth=(usernm, passwd))
        if 200 != req.status_code:
            logger.error(req.content)
            logger.error('bbs-scene.org returned %s', req.status_code)
            return
        else:
            logger.info('bbs-scene.org returned %d in %2.2fs',
                        req.status_code, time.time() - stime)
        for node in xml.etree.ElementTree.XML(req.content).findall('node'):
            bbs_id = node.find('id').text.strip()
            record = dict()
            for key in XML_KEYS:
                if node.find(key) is not None:
                    record[key] = (node.find(key).text or u'').strip()
                else:
                    logger.warn('bbs-scene: %s. missing node %s', bbs_id, key)
                    record[key] = u''
            self.content.append((bbs_id, record))


def wait_for(thread):
    # for dummy threads, wait for return value before listing,
    wait_fetch = 8
    if thread.is_alive():
        echo(u"\r\n\r\nfEtchiNG bbS-SCENE.ORG bbS liSt.. "
             u"(%s)s\b\b%s" % (' ' * 2, '\b' * 2,))
        for num in range(wait_fetch):
            echo('%2d%s' % (wait_fetch - num - 1, u'\b' * 2,))
            if not thread.is_alive():
                return
            thread.join(0.1)
            if getch(0) == u'q':
                # undocumented: q cancels -- in case it ever goes down D:
                return


def chk_thread(thread):
    if thread is None or thread.is_alive():
        return False

    # check if bbs-scene.org thread finished, silly hack
    logger = logging.getLogger()
    session = getsession()
    udbkeys = DBProxy('bbslist').keys()
    nlc = 0
    for key, value in thread.content:
        if key not in udbkeys:
            DBProxy('bbslist')[key] = value
            DBProxy('bbslist', 'comments')[key] = list()
            DBProxy('bbslist', 'ratings')[key] = list()
            nlc += 1
        else:
            # update anyway (fe. port changed), we don't
            # detect this as an update.
            DBProxy('bbslist')[key] = value
    if nlc:
        logger.info('%d new entries', nlc)
        session.send_event('global', ('bbslist_update', None))
        session.buffer_event('bbslist_update')
    else:
        logger.info('no new bbs-scene.org entries')
    return True


def get_bbslist():
    """
    Returns tuple, (bbs_key, display_string), grouped by bbs software !
    """
    max_bbs = 23
    session = getsession()
    session.flush_event('bbslist_update')

    def get_bysoftware():
        by_group = dict()
        for (key, bbs) in DBProxy('bbslist').iteritems():
            grp = bbs['software'].split()[0].title()
            if not grp in by_group:
                by_group[grp] = [(key, bbs)]
                continue
            by_group[grp].append((key, bbs))
        return by_group.items()

    output = list()
    for idx, (bbs_sw, bbs_keys) in enumerate(sorted(get_bysoftware())):
        output.append((None, (u' %s (%2d)' % (
            bbs_sw, len(bbs_keys)))[:max_bbs].rjust(max_bbs, ' ')))
        for key, bbs in sorted(bbs_keys):
            output.append((key, bbs['bbsname'][:max_bbs - 2]
                           + (' $' if len(bbs['bbsname']) >= (max_bbs - 2)
                              else u'')))
    return output


def view_ansi(key):
    term = getterminal()
    echo(term.move(term.height, 0) + '\r\n\r\n')
    ansiurl = DBProxy('bbslist')[key]['ansi']
    logger = logging.getLogger()
    if ansiurl is not None and 0 != len(ansiurl):
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        req = requests.get(ansiurl, auth=(usernm, passwd))
        if req.status_code != 200:
            echo(u'request failed,\r\n')
            echo(u'%r' % (req.content,))
            echo(u'\r\n\r\n(code : %s).\r\n', req.status_code)
            echo(u'\r\nPress any key ..')
            logger.warn('ansiurl request failed: %s' % (ansiurl,))
            getch()
            return
        echo(from_cp437(req.content))


def get_bbsinfo(key):
    term = getterminal()
    bbs = DBProxy('bbslist')[key]
    rstr = u''

    def calc_rating(ratings, outof=4):
        if 0 == len(ratings):
            return u'-'
        total = sum([rtg for (hdl, rtg) in ratings])
        stars = int(math.floor((total / len(ratings))))
        return u'%*s' % (outof, u'*' * stars)

    rstr += (term.green('bbSNAME')
             + term.bold_green(u': ')
             + bbs['bbsname']
             + term.bold_green('  +o ')
             + bbs['sysop'] + u'\n')
    rstr += (term.green('AddRESS')
             + term.bold_green(': ')
             + bbs['address']
             + term.bold_green(':')
             + bbs['port'] + u'\n')
    rstr += (u', ' + term.green('lOCAtiON')
             + term.bold_green(': ')
             + bbs['location'] + '\n')
    rstr += (term.green('SOftWARE')
             + term.bold_green(': ')
             + bbs['software'] + '\n')
    ratings = DBProxy('bbslist', 'ratings')[key]
    rstr += u'RAtiNG: %s (%2.2f of %d)\n' % (
        term.bold_green(calc_rating(ratings)),
        0 if 0 == len(ratings) else
        sum([rtg for (hndl, rtg) in ratings]) / len(ratings),
        len(ratings))
    rstr += u'\n' + bbs['notes']
    comments = DBProxy('bbslist', 'comments')[key]
    for handle, comment in comments:
        rstr += '\n\n' + term.green(handle)
        rstr += term.bold_green(':')
        rstr += comment
    return rstr


def get_ui(position=None):
    term = getterminal()
    lbdata = get_bbslist()
    # after banner art, if our terminal was wide enuf for it ..
    yloc = 8 if term.width >= 69 else 1  # after banner art ..
    # at least 10 tall, as tall as the screen, not as tall as content
    height = min(term.height - yloc - 2, max(10, lbdata))
    lightbar = Lightbar(height, LWIDE, yloc, 2)
    lightbar.update(lbdata)
    lightbar.keyset['enter'].extend((u't', u'T'))
    lightbar.colors['selected'] = term.blue_reverse
    # pager is relative xpos and height to lightbar
    xloc = lightbar.xloc + lightbar.width + 3
    width = min(term.width - xloc, PWIDE)
    pager = Pager(height, width, yloc, xloc)
    if position is not None:
        lightbar.position = position
    return (pager, lightbar)


def banner():
    term = getterminal()
    output = u''
    output += '\r\n\r\n'
    if term.width >= 69:
        output += term.home + term.normal + term.clear
        # spidy's ascii is 72-wide (and, like spidy, total nonsense ..,)
        for line in open(os.path.join
                         (os.path.dirname(__file__), 'art', 'bbslist.asc')):
            output += line.center(72).center(term.width).rstrip() + '\r\n'
    return output + term.normal


def redraw_pager(pager, key, active=True):
    term = getterminal()
    unselected = u' -- ' + term.bold_green('no selection') + u' -- '
    output = u''
    pager.colors['border'] = term.blue if active else u''
    output += pager.border()
    output += pager.clear()
    print repr(pager.clear())
    pager.glyphs['erase'] = u'-'
    if key is None:
        pager.update(u'')
        output += pager.title(unselected)
    else:
        bbsname = DBProxy('bbslist')[key]['bbsname']
        output += pager.title(u' -- %3s. %s -- ' % (
            term.bold_green(key), term.bold_green(bbsname)))
        output += pager.update(get_bbsinfo(key))
        output += pager.footer(
            u'- ' + term.bold_green('t') + '/' + term.green('elnet') +
            u'  ' + term.bold_green('c') + '/' + term.green('omment') +
            u'  ' + term.bold_green('r') + '/' + term.green('rate') +
            u'  ' + term.bold_green('v') + '/' + term.green('iew ansi') +
            u'- ')
    return output


def redraw_lightbar(lightbar, active=True):
    term = getterminal()
    output = u''
    lightbar.colors['border'] = term.bold_green if active else u''
    output += lightbar.border()
    output += lightbar.footer(
        u'- ' + term.bold_blue('a') + '/' + term.blue('dd') + u' -')
    output += lightbar.refresh()
    return output


def redraw(pager, lightbar, leftright):
    return (redraw_pager(pager,
                         key=lightbar.selection[0],
                         active=(leftright == 1))
            + redraw_lightbar(lightbar, active=(leftright == 0)))


def dummy_pager():
    term = getterminal()
    indent = 6

    def disp_entry(char, blurb):
        return (term.bold_blue('(') + term.blue_reverse(char)
                + term.bold_blue + ')' + term.bold_white(' ' + blurb))

    prompt = u', '.join(disp_entry(char, blurb) for char, blurb in (
        ('a', 'add',), ('c', 'comment',), ('r', 'rate',),
        ('t', 'telnet',), ('v', 'view ansi'), ('q', 'quit',)))
    prompt_bye = u'press any key ..'
    echo(u'\r\n\r\n')
    for num, (key, line) in enumerate(get_bbslist()):
        # <3 for dummy terms--convert from record to a width-wrapped,
        # indented text-wrapped record, for real small terminals ^_*
        wrapped = ((u'%s. ' % (key, )) if key is not None else ''
                   + Ansi(line.rstrip()).wrap(term.width - indent))
        echo((u'\r\n' + u' ' * indent).join(wrapped.split(u'\r\n')) + u'\r\n')
        if num and (num % (term.height - 4) == 0):
            # moar prompt,
            while True:
                echo('\r\n' + prompt)
                echo(u' -- ' + disp_entry('[m]', 'moar'))
                inp = getch()
                if inp in (u'q', 'Q'):
                    return  # quit
                if process_keystroke(inp, key):
                    # noop, if call performed action (True),
                    # re-display prompt again,
                    continue
                break  # any other key is default ('m'oar)
    echo(u'\r\n\r\n')
    echo(prompt_bye)
    getch()
    return


def add_bbs():
    session, term = getsession(), getterminal()
    echo(term.move(term.height, 0))
    empty_msg = u'VAlUE iS NOt OPtiONAl.'
    cancel_msg = u"ENtER 'quit' tO CANCEl."
    saved_msg = u'SAVED AS RECORd id %s.'
    bbs = dict()
    for key in XML_KEYS:
        if key == 'timestamp':
            value = time.strftime('%Y-%m-%d %H:%M:%S')
            bbs[key] = value
            continue
        elif key == 'ansi':
            # todo: upload ansi with xmodem .. lol !?
            value = u''
            continue
        splice = len(key) - (len(key) / 3)
        prefix = (u'\r\n\r\n  '
                  + term.bold_blue(key[:splice])
                  + term.bold_black(key[splice:])
                  + term.bold_white(': '))
        led = LineEditor(40)  # !?
        led.highlight = term.green_reverse
        while True:
            echo(prefix)
            value = led.read()
            if value is not None and (value.strip().lower() == 'quit'):
                return
            if key in ('bbsname', 'software', 'address'):
                if value is None or 0 == len(value):
                    echo(u'\r\n' + term.bold_red(empty_msg))
                    echo(u'\r\n' + cancel_msg)
                    continue
            if key in ('port') and value is None or 0 == len(value):
                value = '23'
            # TODO: telnet connect test, of course !
            bbs[key] = value
            break
    key = max([int(key) for key in DBProxy('bbslist').keys()] or [0]) + 1
    DBProxy('bbslist')[key] = bbs
    DBProxy('bbslist', 'comments')[key] = list()
    DBProxy('bbslist', 'ratings')[key] = list()
    echo('\r\n\r\n' + saved_msg % (key) + '\r\n')
    session.send_event('global', ('bbslist_update', None,))
    session.buffer_event('bbslist_update')
    return

#TODO
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
    session = getsession()
    if inp is None:
        return False
    elif type(inp) is int:
        return False
    elif inp.lower() == u't' and key is not None:
        bbs = DBProxy('bbslist')[key]
        gosub('telnet', bbs['address'], bbs['port'],)
    elif inp.lower() == u'a':
        add_bbs()
    elif inp.lower() == u'c' and key is not None:
        add_comment(key)
    elif inp.lower() == u'r' and key is not None:
        rate_bbs(key)
    elif inp.lower() == u'v' and key is not None:
        view_ansi(key)
    elif inp.lower() == u'd' and session.user.is_sysop and key is not None:
        del DBProxy('bbslist')[key]
    else:
        return False  # unhandled
    return True


def add_comment(key):
    session, term = getsession(), getterminal()
    prompt_comment = u'\r\nWhAt YOU GOt tO SAY? '
    prompt_chg = u'\r\nChANGE EXiStiNG ? [yn] '
    echo(term.move(term.height, 0))
    echo(prompt_comment)
    comment = LineEditor(max(10, term.width - len(prompt_comment) - 5)).read()
    if comment is None or 0 == len(comment.strip()):
        return
    entry = (session.handle, comment)
    comments = DBProxy('bbslist', 'comments')
    comments.acquire()
    existing = comments[key]
    if session.handle in (handle for (handle, cmt) in comments[key]):
        echo(prompt_chg)
        if getch() not in (u'y', u'Y'):
            comments.release()
            return
        # re-define list without existing entry, + new entry
        comments[key] = [(handle, cmt) for (handle, cmd) in existing
                         if session.handle != handle] + [entry]
        comments.release()
        return
    # re-define as existing list + new entry
    comments[key] = existing + [entry]
    comments.release()


def rate_bbs(key):
    session, term = getsession(), getterminal()
    prompt_rating = u'\r\nRAtE 0.0 - 4.0: '
    prompt_chg = u'\r\nChANGE EXiStiNG ? [yn] '
    echo(term.move(term.height, 0) + '\r\n')
    echo(prompt_rating)
    rating = LineEditor(3).read()
    if rating is None or 0 == len(rating.strip()):
        return
    try:
        f_rating = float(rating)
    except ValueError:
        return
    entry = (session.handle, f_rating)
    ratings = DBProxy('bbslist', 'ratings')
    ratings.acquire()
    if session.handle in (handle for (handle, rtg) in ratings[key]):
        echo(prompt_chg)
        if getch() not in (u'y', u'Y'):
            ratings.release()
            return
        # re-define list without existing entry, + new entry
        ratings[key] = [(handle, rtg)
                        for (handle, rtg) in ratings[key]
                        if session.handle != handle] + [entry]
        ratings.release()
        return
    # re-define as existing list + new entry
    ratings[key] = ratings[key] + [entry]
    ratings.release()


def main():
    session, term = getsession(), getterminal()
    pager, lightbar = get_ui(None)

    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates()
        thread.start()
        session.activity = u'bbs lister [bbs-scene.org]'
    else:
        session.activity = u'bbs lister'

    dirty = True
    session.buffer_event('refresh', ('init',))
    leftright = 0  # 'left'

    while True:
        # check if screen requires refresh of any kind,
        if session.poll_event('refresh'):
            pager, lightbar = get_ui(lightbar.position)
            echo(banner())
            dirty = True
        if chk_thread(thread):
            thread = None
            dirty = True
        if session.poll_event('bbslist_update'):
            dirty = True

        # refresh advanced screen with lightbar and pager
        if dirty and (session.env.get('TERM') != 'unknown' and
                      not session.user.get('expert', False)
                      and term.width >= 72 and term.height >= 20):
            echo(redraw(pager, lightbar, leftright))
            dirty = False

        # or .. provide dumb terminal with hotkey prompt
        elif dirty:
            if thread is not None:
                wait_for(thread)
            if chk_thread(thread):
                thread = None
            echo(u'\r\n\r\n')
            return dummy_pager()

        # detect and process keyboard input for advanced screen
        inp = getch(1)
        if inp == term.KEY_LEFT:
            # full refresh for border chang ;/
            leftright = 0
            echo(redraw_pager(
                pager, lightbar.selection[0], active=(leftright == 1)))
            echo(redraw_lightbar(
                lightbar, active=(leftright == 0)))
        elif inp == term.KEY_RIGHT:
            # full refresh for border chang ;/
            leftright = 1
            echo(redraw_pager(
                pager, lightbar.selection[0], active=(leftright == 1)))
            echo(redraw_lightbar(
                lightbar, active=(leftright == 0)))
        elif inp is not None:
            # process as pager or lightbar keystroke,
            echo(lightbar.process_keystroke(inp)
                 if leftright == 0 else
                 pager.process_keystroke(inp))

            # get current entry
            key, output = lightbar.selection

            # full refresh after rate/comment/elnet/view etc.
            if process_keystroke(inp, key):
                session.buffer_event('refresh', ('redraw',))
                continue

            # quit 'q'
            if (lightbar.quit or pager.quit):
                return

            # pressed return, telnet!
            if lightbar.selected:
                bbs = DBProxy('bbslist')[lightbar.selection[0]]
                gosub('telnet', bbs['address'], bbs['port'])
                # buffer full refresh after telnet
                session.buffer_event('refresh', ('redraw',))

            # selected new entry, refresh entire pager, a little bit
            # bandwidth excessive as bbs name is part of border title.
            if lightbar.moved:
                echo(redraw_pager(pager, key, active=(leftright == 1)))
