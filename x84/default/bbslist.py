
"""
bbs lister for x/84, http://github.com/jquast/x84

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
import math
import os

XML_KEYS = ('bbsname', 'sysop', 'software',
            'address', 'port', 'location',
            'notes', 'timestamp', 'ansi')
XML_REQNOTNULL = ('bbsname', 'sysop', 'software',
                  'address', 'location', 'notes')
LWIDE = 25
PWIDE = 80

import sauce
from x84.bbs import echo, ini, getch, getsession, DBProxy, LineEditor, timeago
from x84.bbs import Lightbar, Pager, getterminal, gosub, Ansi, from_cp437


def disp_entry(char, blurb):
    term = getterminal()
    return (term.bold_blue('(') + term.blue_reverse(char)
            + term.bold_blue + ')' + term.bold_white(blurb))


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
            logger.error('bbs-scene.org: %s', req.status_code)
            return
        else:
            logger.info('bbs-scene.org: %d in %2.2fs',
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
            thread.join(1)
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
    session, term = getsession(), getterminal()
    session.flush_event('bbslist_update')

    def get_bysoftware():
        by_group = dict()
        for (key, bbs) in DBProxy('bbslist').iteritems():
            grp = bbs['software']
            if not grp.lower().startswith('the'):
                grp = grp.split()[0].title()
            else:
                grp = grp.title()
            if not grp in by_group:
                by_group[grp] = [(key, bbs)]
                continue
            by_group[grp].append((key, bbs))
        return by_group.items()

    output = list()
    for idx, (bbs_sw, bbs_keys) in enumerate(sorted(get_bysoftware())):
        soft_line = bbs_sw.rjust(max_bbs)[:max_bbs]
        output.append((None, soft_line))
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
    if ansiurl is not None and 0 != len(ansiurl) and ansiurl != 'NONE':
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
        echo(from_cp437(sauce.SAUCE(data=req.content).__str__()))
    else:
        echo('no ansi available (%r)' % (ansiurl,))
    echo(term.move(term.height, 0) + term.normal + '\r\npress any key ..')
    getch()


def get_bbsinfo(key):
    term = getterminal()
    bbs = DBProxy('bbslist')[key]

    def calc_rating(ratings, outof=4):
        if 0 == len(ratings):
            return u'-'
        total = sum([rtg for (hdl, rtg) in ratings])
        stars = int(math.floor((total / len(ratings))))
        return u'%*s' % (outof, u'*' * stars)

    rstr = u''
    rstr += (term.green('bbSNAME')
             + term.bold_green(u': ')
             + bbs['bbsname']
             + term.bold_green('  +o ')
             + bbs['sysop'] + u'\n')
    rstr += (term.green('AddRESS')
             + term.bold_green(': ')
             + bbs['address']
             + term.bold_green(': ')
             + bbs['port'] + u'\n')
    rstr += (term.green('lOCAtiON')
             + term.bold_green(': ')
             + bbs['location'] + '\n')
    rstr += (term.green('SOftWARE')
             + term.bold_green(': ')
             + bbs['software'] + '\n')
    epoch = time.mktime(time.strptime(bbs['timestamp'], '%Y-%m-%d %H:%M:%S'))
    rstr += (term.green('tiMEStAMP')
             + term.bold_green(': ')
             + bbs['timestamp'] + ' ('
             + term.green(timeago(time.time() - epoch))
             + ') ago\n')
    ratings = DBProxy('bbslist', 'ratings')[key]
    rstr += (term.green('RAtiNG') + term.bold_green(': ')
             + '%s (%2.2f of %d)\n' % (
                 term.bold_green(calc_rating(ratings)),
                 0 if 0 == len(ratings) else
                 sum([rtg for (hndl, rtg) in ratings])
                 / len(ratings), len(ratings)))
    rstr += u'\n' + bbs['notes']
    comments = DBProxy('bbslist', 'comments')[key]
    for handle, comment in comments:
        rstr += '\n\n' + term.green(handle)
        rstr += term.bold_green(': ')
        rstr += comment
    return rstr


def get_ui(position=None):
    term = getterminal()
    lbdata = get_bbslist()
    # after banner art, if our terminal was wide enuf for it ..
    yloc = 8 if term.width >= 69 else 1  # after banner art ..
    xpos = max(2, term.height - ((PWIDE - LWIDE - 3) / 2))
    # at least 10 tall, as tall as the screen, not as tall as content
    height = min(term.height - yloc - 2, max(10, len(lbdata)))
    lightbar = Lightbar(height, LWIDE, yloc, xpos)
    lightbar.update(lbdata)
    lightbar.keyset['enter'].extend((u't', u'T'))
    lightbar.colors['selected'] = term.blue_reverse
    # pager is relative xpos and height to lightbar
    xloc = lightbar.xloc + lightbar.width + 3
    width = min(term.width - xloc, PWIDE)
    pager = Pager(height, width, yloc, xloc)
    if position is not None:
        lightbar.position = position
    pager.ypadding = 2
    pager.xpadding = 2
    return (pager, lightbar)


def banner(dumb=False):
    term = getterminal()
    output = u''
    if not dumb:
        output += term.home + term.normal + term.clear
    else:
        output += '\r\n\r\n' + term.normal
    if term.width >= 72:
        # spidy's ascii is 72-wide (and, like spidy, total nonsense ..,)
        for line in open(os.path.join
                        (os.path.dirname(__file__), 'art', 'bbslist.asc')):
            output += line.center(72).center(term.width).rstrip() + '\r\n'
    return output


def redraw_pager(pager, selection, active=True):
    term = getterminal()
    unselected = u'- no selection -'
    output = u''
    pager.colors['border'] = term.blue if active else u''
    output += pager.border()
    output += pager.clear()
    pager.move_home()
    key, entry = selection
    if key is None:
        if entry and entry.strip().lower() == 'enthral':
            output += pager.update(
                "Enthral is a fresh look at the old school art of bbsing. "
                "It's a fresh face to an old favorite. Although Enthral is "
                "still in it's alpha stages, the system is quite stable and "
                "is already very feature rich. Currently available for "
                "Linux, BSD, and Apple's OS X.\n\n"
                "   " + term.bold_blue('http://enthralbbs.com/') + "\n\n"
                "Author: Mercyful Fate\n"
                "IRC: #enthral on irc.bbs-scene.org\n")
            output += pager.title('- about Enthral -')
        elif entry and entry.strip().lower() == 'mystic':
            output += pager.update(
                "Mystic BBS is a bulletin board system (BBS) software in "
                "the vein of other \"forum hack\" style software such as "
                "Renegade, Oblivion/2, and Iniquity. Like many of its "
                "counterparts it features a high degree of relatively "
                "easy customization thanks to its ACS based menu system "
                "along with fully editable strings and ANSI themes. "
                "Mystic also includes its own Pascal like MPL scripting "
                "language for even further flexibility.\n\n"
                "  " + term.bold_blue('http://mysticbbs.com/') + "\n\n"
                "Author: g00r00\n"
                "IRC: #MysticBBS on irc.efnet.org\n")
            output += pager.title('- about Mystic -')
        elif entry and entry.strip().lower() == 'synchronet':
            output += pager.update(
                "Synchronet Bulletin Board System Software is a free "
                "software package that can turn your personal computer "
                "into your own custom online service supporting multiple "
                "simultaneous users with hierarchical message and file "
                "areas, multi-user chat, and the ever-popular BBS door "
                "games.\n\n"
                "Synchronet has since been substantially redesigned as "
                "an Internet-only BBS package for Win32 and Unix-x86 "
                "platforms and is an Open Source project under "
                "continuous development.\n\n"
                "  " + term.bold_blue('http://www.synchro.net/\n') + "\n\n"
                "IRC: ??\n")
            output += pager.title('- about Synchronet -')
        elif entry and entry.strip().lower() == 'the progressive':
            output += pager.update(
                "This bbs features threading, intra-process communication, "
                "and easy scripting in python. X/84 is a continuation of  "
                " this codebase.\n\n"
                "IRC: #prsv on efnet\n")
            output += pager.title('- about The Progressive -')
        elif entry and entry.strip().lower() == 'x/84':
            output += pager.update(
                "X/84 is an open source python utf8 bsd-licensed telnet "
                "server specificly designed for BBS's, MUD's, and high "
                "scriptability. It is a Continuation of 'The Progressive' "
                "and is the only BBS software to support both CP437 and "
                "UTF8 encoding.\n\n"
                "  " + term.bold_blue('http://github.com/jquast/x84/\n')
                + "\n\nIRC: #prsv on efnet\n")
            output += pager.title('- about X/84 -')
        else:
            pager.update(u'')
            output += pager.clear()
            output += pager.title(unselected)
    else:
        bbsname = DBProxy('bbslist')[key]['bbsname']
        ansiurl = DBProxy('bbslist')[key]['ansi']
        output += pager.title(u'- %s -' % (term.bold_blue(bbsname)))
        output += pager.update(get_bbsinfo(key))
        output += pager.footer(
            u'- ' + term.bold_green('t') + '/' + term.green('elnet') +
            u'  ' + term.bold_green('c') + '/' + term.green('omment') +
            u'  ' + term.bold_green('r') + '/' + term.green('rate') +
            (u'  ' + (term.bold_green('v') + '/' + term.green('iew ansi'))
             if ansiurl != 'NONE' and 0 != len(ansiurl) else u'') +
            u'- ')
    return output


def redraw_lightbar(lightbar, active=True):
    term = getterminal()
    output = u''
    lightbar.colors['border'] = term.bold_green if active else u''
    output += lightbar.border()
    s_add = (term.bold_blue('(') + term.blue_reverse('a')
             + term.bold_blue(')') + term.blue('dd') if active else (
                 term.bold_green('(') + term.green_reverse('a')
                 + term.bold_green(')') + term.green('dd')))
    up = term.bold_blue('up') if active else term.bold_green('up')
    down = term.bold_blue('down') if active else term.bold_green('down')
    leftright = term.bold_blue('right') if active else term.bold_green('left')
    s_dir = u' '.join((up, down, leftright))
    output += lightbar.footer(u'- ' + s_add + u' ' + s_dir + ' -')
    output += lightbar.refresh()
    return output


def redraw(pager, lightbar, leftright):
    return (redraw_pager(pager,
                         selection=lightbar.selection,
                         active=(leftright == 1))
            + redraw_lightbar(lightbar, active=(leftright == 0)))


def dummy_pager():
    term = getterminal()
    hindent = 2
    vindent = 5
    prompt_key = u'\r\n\r\nENtER BBS iD: '
    prompt_pak = u'\r\n\r\nPRESS ANY kEY ..'
    msg_badkey = u'\r\n\r\nbbS id iNVAliD!'
    msg_header = u'// bbS liSt'
    nlines = 0
    bbslist = get_bbslist()
    echo(u'\r\n' + msg_header.center(term.width).rstrip() + '\r\n\r\n')
    if 0 == len(bbslist):
        echo(u'\r\n\r\nNO BBSS. a%sdd ONE, q%sUit' % (
            term.bold_blue(':'), term.bold_blue(':')))
        while True:
            inp = getch()
            if inp in (u'q', 'Q'):
                return  # quit
            elif inp in (u'a', 'A'):
                process_keystroke(inp)
                break

    def more(cont=False):
        """
        Returns True if user 'q'uit; otherwise False
        when prompting is complete (moar/next/whatever)
        """
        prompt = u', '.join(disp_entry(char, blurb)
                            for char, blurb in (
                                ('i', 'NfO',), ('a', 'dd',),
                                ('c', 'OMMENt',), ('r', 'AtE',),
                                ('t', 'ElNEt',), ('v', 'iEW ANSi'),
                                ('q', 'Uit',),
                                ('+', 'MOAR!',))) + u' --> '
        while True:
            echo('\r\n\r\n' + Ansi(prompt).wrap(term.width / 2))
            inp = getch()
            if inp in (u'q', 'Q'):
                return True
            elif inp is not None and type(inp) is not int:
                if cont and inp == u'+':
                    return False
                if inp.lower() in u'acrtviACRTVI':
                    # these keystrokes require a bbs key argument,
                    # prompt the user for one
                    echo(prompt_key)
                    key = LineEditor(5).read()
                    if (key is None or 0 == len(key.strip())
                            or not key in DBProxy('bbslist')):
                        echo(msg_badkey)
                        continue
                    process_keystroke(inp, key)
            echo(u'\r\n')

    while True:
        for (key, line) in bbslist:
            if key is None:  # bbs software
                echo(term.blue_reverse(line.rstrip()) + '\r\n')
                nlines += 1
            else:
                wrapd = Ansi(line).wrap(term.width - hindent)
                echo(term.bold_blue(key) + term.bold_black('. '))
                echo (wrapd + '\r\n')
                nlines += len(wrapd.split('\r\n'))
            if nlines and (nlines % (term.height - vindent) == 0):
                if more(True):
                    break
        # one final prompt before exit
        more (False)
    return


def add_bbs():
    session, term = getsession(), getterminal()
    echo(term.move(term.height, 0))
    empty_msg = u'\r\n\r\nVAlUE iS NOt OPtiONAl.'
    cancel_msg = u"\r\n\r\nENtER 'quit' tO CANCEl."
    saved_msg = u'\r\n\r\nSAVED AS RECORd id %s.'
    logger = logging.getLogger()
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
                  + (term.bold_red('* ') if key in XML_REQNOTNULL else u'')
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
            if key in XML_REQNOTNULL:
                if value is None or 0 == len(value.strip()):
                    echo(term.bold_red(empty_msg))
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
    if ini.CFG.has_section('bbs-scene'):
        # post to bbs-scene.org
        posturl = 'http://bbs-scene.org/api/bbslist.xml'
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        data = {'name': bbs['bbsname'],
                'sysop': bbs['sysop'],
                'software': bbs['software'],
                'address': bbs['address'],
                'port': bbs['port'],
                'location': bbs['location'],
                'notes': bbs['notes'],
                }
        req = requests.post(posturl, auth=(usernm, passwd), data=data)
        if req.status_code != 200:
            echo(u'request failed,\r\n')
            echo(u'%r' % (req.content,))
            echo(u'\r\n\r\n(code : %s).\r\n', req.status_code)
            echo(u'\r\nPress any key ..')
            logger.warn('bbs post failed: %s' % (posturl,))
            getch()
            return
        logger.info('bbs-scene.org api (%d): %r/%r',
                    req.status_code, session.user.handle, bbs)
        # spawn a thread to re-fetch bbs entries,
        thread = FetchUpdates()
        thread.start()
        wait_for(thread)
        return chk_thread(thread)


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
    elif inp.lower() == u'i' and key is not None:
        echo(get_bbsinfo(key) + '\r\n')
    elif inp.lower() == u'v' and key is not None:
        view_ansi(key)
    elif inp.lower() == u'd' and session.user.is_sysop and key is not None:
        del DBProxy('bbslist')[key]
    else:
        return False  # unhandled
    return True


def add_comment(key):
    session, term = getsession(), getterminal()
    prompt_comment = u'\r\n\r\nWhAt YOU GOt tO SAY? '
    prompt_chg = u'\r\n\r\nChANGE EXiStiNG ? [yn] '
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
    prompt_rating = u'\r\n\r\nRAtE 0.0 - 4.0: '
    prompt_chg = u'\r\n\r\nChANGE EXiStiNG ? [yn] '
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

    def is_dumb():
        return (session.env.get('TERM') != 'unknown' and
                not session.user.get('expert', False)
                and term.width >= 72 and term.height >= 20)

    dirty = True
    session.buffer_event('refresh', ('init',))
    leftright = 0  # 'left'

    while True:
        # check if screen requires refresh of any kind,
        if session.poll_event('refresh'):
            pager, lightbar = get_ui(lightbar.position)
            echo(banner(is_dumb()))
            dirty = True
        if chk_thread(thread):
            thread = None
            dirty = True
        if session.poll_event('bbslist_update'):
            dirty = True

        # refresh advanced screen with lightbar and pager
        if dirty:
            if not is_dumb():
                echo(redraw(pager, lightbar, leftright))
                dirty = False
            else:
                # or .. provide dumb terminal with hotkey prompt
                if thread is not None:
                    wait_for(thread)
                if chk_thread(thread):
                    thread = None
                return dummy_pager()
            echo(redraw(pager, lightbar, leftright))
            dirty = False

        # detect and process keyboard input for advanced screen
        inp = getch(1)
        if inp == term.KEY_LEFT:
            # full refresh for border chang ;/
            leftright = 0
            echo(redraw_pager(
                pager, lightbar.selection, active=(leftright == 1)))
            echo(redraw_lightbar(
                lightbar, active=(leftright == 0)))
        elif inp == term.KEY_RIGHT:
            # full refresh for border chang ;/
            leftright = 1
            echo(redraw_pager(pager,
                              lightbar.selection, active=(leftright == 1)))
            echo(redraw_lightbar(lightbar,
                                 active=(leftright == 0)))
        elif inp is not None:
            # process as pager or lightbar keystroke,
            echo(lightbar.process_keystroke(inp)
                 if leftright == 0 else
                 pager.process_keystroke(inp))

            # full refresh after rate/comment/elnet/view etc.
            if process_keystroke(inp, lightbar.selection[0]):
                session.buffer_event('refresh', ('redraw',))
                continue

            # quit 'q'
            if (lightbar.quit or pager.quit):
                return

            # pressed return, telnet!
            if lightbar.selected and lightbar.selection[0] is not None:
                bbs = DBProxy('bbslist')[lightbar.selection[0]]
                gosub('telnet', bbs['address'], bbs['port'])
                # buffer full refresh after telnet
                session.buffer_event('refresh', ('redraw',))

            # selected new entry, refresh entire pager, a little bit
            # bandwidth excessive as bbs name is part of border title.
            if lightbar.moved:
                echo(redraw_pager(pager, lightbar.selection,
                                  active=(leftright == 1)))
                lightbar.moved = False
