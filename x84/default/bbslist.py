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

DB_KEYS = ('bbsname', 'sysop', 'software',
           'address', 'port', 'location',
           'notes', 'timestamp', 'ansi')
XML_REQNOTNULL = ('bbsname', 'sysop', 'software',
                  'address', 'location', 'notes')

import sauce


def fancy_blue(char, blurb=u''):
    """ Diplay '(char)blurb' in fancy blue. """
    from x84.bbs import getterminal
    term = getterminal()
    return u''.join((
        term.bold_blue('('),
        term.blue_reverse(char),
        term.bold_blue(')'),
        term.bold_white(blurb),))


def fancy_green(char, blurb=u''):
    """ Diplay '(char)blurb' in fancy green. """
    from x84.bbs import getterminal
    term = getterminal()
    return u''.join((
        term.bold_green('('),
        term.green_reverse(char),
        term.bold_green(')'),
        term.bold_white(blurb),))


class FetchUpdates(threading.Thread):
    """ Fetch bbs-scene.org bbs list as thread. """
    url = 'http://bbs-scene.org/api/bbslist.php'
    content = list()

    def run(self):
        """ Begin fetch, results are stored in self.content """
        from x84.bbs import ini
        logger = logging.getLogger()
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        logger.info('fetching %s ..', self.url)
        # pylint: disable=E1103
        req = requests.get(self.url, auth=(usernm, passwd))
        if 200 != req.status_code:
            logger.error(req.content)
            logger.error('bbs-scene.org: %s', req.status_code)
            return
        logger.info('bbs-scene.org: %d', req.status_code)

        # some byte-level pre-parsing sanitization
        buf = ''.join((byte for byte in req.content
                       if ord(byte) >= 0x20
                       or ord(byte) in (0x09, 0x0a, 0x0d)))

        # append elements into self.content (bbs_id, dict(attributes))
        for node in xml.etree.ElementTree.XML(buf).findall('node'):
            bbs_id = node.find('id').text.strip()
            record = dict([(key,
                ((node.find(key).text or u'').strip()
                    if node.find(key) is not None else u''))
                for key in DB_KEYS])
            self.content.append((bbs_id, record))


def wait_for(thread):
    """ for dummy pager, wait for return value before listing, """
    from x84.bbs import echo, getch
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
    """
    for asyncronous lightbar, return False if thread is still running,
    'dirty' if thread completed and new entries were found, 'None' if thread
    completed and no no entries were discovered.
    """
    from x84.bbs import getsession, DBProxy
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
    if nlc > 0:
        logger.info('%d new entries', nlc)
        session.send_event('global', ('bbslist_update', None))
        session.buffer_event('bbslist_update')
        return 'dirty'
    else:
        logger.info('no new bbs-scene.org entries')
    return None


def get_bbslist(max_len=23):
    """
    Returns tuple, (bbs_key, display_string), grouped by bbs software !
    """
    from x84.bbs import getsession, DBProxy, getterminal
    session, term = getsession(), getterminal()
    session.flush_event('bbslist_update')

    def get_bysoftware():
        """
        Group bbs list by software
        """
        by_group = dict()
        for (key, bbs) in DBProxy('bbslist').iteritems():
            grp = bbs['software'].decode('iso8859-1', 'replace')
            if 'citadel' in grp.lower():
                grp = u'Citadel'
            elif 'mystic' in grp.lower():
                grp = u'Mystic'
            elif 'synchronet' in grp.lower():
                grp = u'Synchronet'
            if not grp.lower().startswith('the'):
                grp = grp.split()[0].title()
            else:
                grp = grp.title().split()[1]
            if not grp in by_group:
                by_group[grp] = [(key, bbs)]
                continue
            by_group[grp].append((key, bbs))
        return by_group.items()
    def strip_name(key):
        if len(key) >= max_len:
            key = key[:(max_len - 2)] + ' $'
        return key
    output = list()
    for _grp, _value in sorted(get_bysoftware()):
        output.append((None, term.blue(_grp.rjust(max_len))))
        for key, bbs in sorted(_value):
            output.append((key, strip_name(bbs['bbsname'])))
    return output


def view_ansi(key):
    """ fetch and view a bbs ansi. They're not often very good ...
    """
    from x84.bbs import getterminal, echo, DBProxy, ini, getch, from_cp437
    term = getterminal()
    ansiurl = DBProxy('bbslist')[key]['ansi']
    logger = logging.getLogger()
    echo(u'\r\n\r\n')
    if ansiurl is not None and 0 != len(ansiurl) and ansiurl != 'NONE':
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        req = requests.get(ansiurl, auth=(usernm, passwd))
        if req.status_code != 200:
            echo(u'\r\n\r\nrequest failed,\r\n')
            echo(u'%r' % (req.content,))
            echo(u'\r\n\r\n(code : %s).\r\n' % (req.status_code,))
            echo(u'\r\nPress any key ..')
            logger.warn('ansiurl request failed: %s' % (ansiurl,))
            getch()
            return
        ansi_txt = from_cp437(sauce.SAUCE(data=req.content).__str__())
        echo(ansi_txt)
    else:
        echo('no ansi available (%s)' % (ansiurl,))
    # move to bottom of screen and getch
    echo(u''.join((
        term.move(term.height, 0),
        term.normal,
        u'\r\n\r\nPRESS ANY kEY ...'),))
    getch()


def calc_rating(ratings, outof=4):
    """ Given set of ratings, return ucs \*, of 1 to *outouf*, star rating. """
    if 0 == len(ratings):
        return u'-'
    total = sum([_rating for (_handle, _rating) in ratings])
    stars = int(math.floor((total / len(ratings))))
    return u'%*s' % (outof, u'*' * stars)


def get_bbsinfo(key, active=True):
    """
    given a bbs key, fetch detailed information for use in pager
    """
    # pylint: disable=R0914
    #        Too many local variables.
    from x84.bbs import getterminal, DBProxy, timeago
    rstr = u''
    term = getterminal()
    highlight = term.bold_blue if active else term.blue
    lowlight = term.bold_black
    bbs = DBProxy('bbslist')[key]
    epoch = time.mktime(time.strptime(bbs['timestamp'], '%Y-%m-%d %H:%M:%S'))
    ratings = DBProxy('bbslist', 'ratings')[key]
    comments = DBProxy('bbslist', 'comments')[key]
    rstr += (lowlight('bbSNAME')
             + highlight(u': ')
             + bbs['bbsname']
             + highlight('  +o ')
             + bbs['sysop'] + u'\r\n')
    rstr += (lowlight('AddRESS')
             + highlight(': ')
             + bbs['address']
             + highlight(': ')
             + bbs['port'] + u'\r\n')
    rstr += (lowlight('lOCAtiON')
             + highlight(': ')
             + bbs['location'] + '\r\n')
    rstr += (lowlight('SOftWARE')
             + highlight(': ')
             + bbs['software'] + '\r\n')
    rstr += (lowlight('tiMEStAMP')
             + highlight(':')
             + lowlight(timeago(time.time() - epoch))
             + ' ago\r\n')
    rstr += (lowlight('RAtiNG') + highlight(': ')
             + '%s (%2.2f of %d)\r\n' % (
                 highlight(calc_rating(ratings)),
                 0 if 0 == len(ratings) else
                 sum([_rating for (_handle, _rating) in ratings])
                 / len(ratings), len(ratings)))
    rstr += u'\r\n' + bbs['notes']
    for handle, comment in comments:
        rstr += '\r\n\r\n' + lowlight(handle)
        rstr += highlight(': ')
        rstr += comment
    return rstr


def get_swinfo(entry, pager):
    """
    given a normalized bbs software name,
    fetch a description paragraph for use in pager
    """
    from x84.bbs import getterminal
    from x84.bbs.output import Ansi
    term = getterminal()
    output = pager.clear()
    if entry:
        entry = Ansi(entry).seqfill().strip()
    if entry and entry.strip().lower() == 'enthral':
        output += pager.update(
            "Enthral is a fresh look at the old school art of bbsing. "
            "It's a fresh face to an old favorite. Although Enthral is "
            "still in it's alpha stages, the system is quite stable and "
            "is already very feature rich. Currently available for "
            "Linux, BSD, and Apple's OS X.\r\n\r\n"
            "   " + term.bold_blue('http://enthralbbs.com/') + "\r\n\r\n"
            "Author: Mercyful Fate\n"
            "IRC: #enthral on irc.bbs-scene.org\r\n")
        output += pager.title(u'- about ' + term.blue('Enthral') + u' -')
    elif entry and entry.strip().lower() == 'citadel':
        output += pager.update(
            "Ancient history.\r\n\r\n")
        output += pager.title(u'- about ' + term.blue('Citadel') + u' -')
    elif entry and entry.strip().lower() == 'mystic':
        output += pager.update(
            "Mystic BBS is a bulletin board system (BBS) software in "
            "the vein of other \"forum hack\" style software such as "
            "Renegade, Oblivion/2, and Iniquity. Like many of its "
            "counterparts it features a high degree of relatively "
            "easy customization thanks to its ACS based menu system "
            "along with fully editable strings and ANSI themes. "
            "Mystic also includes its own Pascal like MPL scripting "
            "language for even further flexibility.\r\n\r\n"
            "  " + term.bold_blue('http://mysticbbs.com/') + "\r\n\r\n"
            "Author: g00r00\r\n"
            "IRC: #MysticBBS on irc.efnet.org\r\n")
        output += pager.title(u'- about ' + term.blue('Mystic') + u' -')
    elif entry and entry.strip().lower() == 'synchronet':
        output += pager.update(
            "Synchronet Bulletin Board System Software is a free "
            "software package that can turn your personal computer "
            "into your own custom online service supporting multiple "
            "simultaneous users with hierarchical message and file "
            "areas, multi-user chat, and the ever-popular BBS door "
            "games.\r\n\r\n"
            "Synchronet has since been substantially redesigned as "
            "an Internet-only BBS package for Win32 and Unix-x86 "
            "platforms and is an Open Source project under "
            "continuous development.\r\n\r\n"
            "  " + term.bold_blue('http://www.synchro.net/\r\n') + "\r\n\r\n"
            "Author: Deuce\r\n"
            "IRC: #synchronet on irc.bbs-scene.org")
        output += pager.title(u'- about ' + term.blue('Synchronet') + u' -')
    elif entry and entry.strip().lower() == 'progressive':
        output += pager.update(
            "This bbs features threading, intra-process communication, "
            "and easy scripting in python. X/84 is a continuation of "
            "this codebase.\r\n\r\n"
            + "Author: jojo\r\n"
            "IRC: #prsv on irc.efnet.org")
        output += pager.title(u'- about ' + term.blue('The Progressive -'))
    elif entry and entry.strip().lower() == 'x/84':
        output += pager.update(
            "X/84 is an open source python utf8 bsd-licensed telnet "
            "server specificly designed for BBS's, MUD's, and high "
            "scriptability. It is a Continuation of 'The Progressive' "
            "and is the only BBS software to support both CP437 and "
            "UTF8 encoding.\r\n\r\n"
            "  " + term.bold_blue('https://github.com/jquast/x84/\r\n')
            + "\r\n\r\nAuthor: dingo, jojo\r\n"
            "IRC: #prsv on irc.efnet.org")
        output += pager.title(u'- about ' + term.blue('X/84') + u' -')
    else:
        output += pager.update(u' no information about %s.'
                               % (entry or u'').title(),)
        output += pager.title(u'- about ' + term.blue(entry or u'') + u' -')
    return output


def get_ui(position=None):
    """
    Returns user interface (lightbar, pager).
    Optional argument position is tuple position of prior lightbar instance.
    """
    from x84.bbs import getterminal, Lightbar, Pager
    term = getterminal()
    assert term.height > 10 and term.width >= 40
    # +-+ +----+
    # |lb |pager
    # +-+ +----+
    height = term.height - 7
    lb_width = int(term.width * .3)
    pg_width = term.width - (lb_width)
    lb_xloc = (term.width / 2) - (term.width / 2)
    pg_xloc = lb_xloc + lb_width
    lightbar = Lightbar(height, lb_width, (term.height - height - 1), lb_xloc)
    pager = Pager(height, pg_width, (term.height - height - 1), pg_xloc)
    pager.ypadding = 2
    pager.xpadding = 2
    lightbar.update(get_bbslist(max_len=lightbar.visible_width))
    ## pressing Return is same as 't'elnet
    lightbar.keyset['enter'].extend((u't', u'T'))
    ## re-select previous selection
    if position is not None:
        lightbar.position = position
    return (pager, lightbar)


def banner():
    """ Display banner/art. """
    from x84.bbs import getterminal
    term = getterminal()
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'bbslist.asc')
    return u''.join((
        u'\r\n\r\n',
        u'\r\n'.join([line.center(term.width)[:term.width].rstrip()
                      for line in open(artfile)]) if os.path.exists(artfile)
        else u'',))


def redraw_pager(pager, selection, active=True):
    """
    Display bbs information in pager window for given selection.
    """
    from x84.bbs import getterminal, DBProxy
    term = getterminal()
    output = u''
    pager.colors['border'] = term.blue if active else term.bold_black
    output += pager.border()
    output += pager.clear()
    pager.move_home()
    key, entry = selection
    if key is None:
        output += get_swinfo((entry or u'?').strip(), pager)
        output += pager.footer(u'-'
                               + fancy_green('a', 'dd') + u' -')
    else:
        # describe bbs in pager
        bbsname = DBProxy('bbslist')[key]['bbsname']
        ansiurl = DBProxy('bbslist')[key].get('ansi', 'NONE')
        output += pager.title(u'- %s -' % (
            term.bold_blue(bbsname) if active else term.blue(bbsname)))
        output += pager.update(get_bbsinfo(key, active))
        ans = u''
        if ansiurl != 'NONE' and 0 != len(ansiurl):
            ans = u'.' + fancy_green('v', 'ansi')
        output += pager.footer(u'- '
                               + fancy_green('a', 'dd') + u'.'
                               + fancy_green('t', 'ElNEt') + u'.'
                               + fancy_green('c', 'OMNt') + u'.'
                               + fancy_green('r', 'AtE') + ans + u' -')
        output += pager.pos(pager.height - 2, pager.width - 4)
    # pager scroll indicator ..
    output += pager.pos(pager.height - 2, pager.width - 4)
    if pager.bottom != pager.position:
        output += fancy_green('+') if active else fancy_blue('+')
    else:
        output += '   '
    return output


def redraw_lightbar(lightbar, active=True):
    """
    Display bbs listing in lightbar.
    """
    from x84.bbs import getterminal
    term = getterminal()
    lightbar.colors['border'] = term.bold_green if active else term.bold_black
    output = lightbar.border()
    if active:
        lightbar.colors['selected'] = term.green_reverse
    else:
        lightbar.colors['selected'] = term.blue_reverse
#        output += lightbar.footer(u''.join((
#            u'- ',
#            fancy_green('up', '.'),
#            fancy_green('down', '.'),
#            fancy_green('right', u''),
#            u' -')))
#        output += lightbar.footer(u''.join((
#            u'- ',
#            fancy_blue('up', '.'),
#            fancy_blue('down', '.'),
#            fancy_green('left', u''),
#            u' -')))
    output += lightbar.title(u'- ' + fancy_green('a', 'add') + ' -')
    output += lightbar.refresh()
    return output


def redraw(pager, lightbar, leftright):
    """
    Redraw pager and lightbar.
    """
    return (redraw_pager(pager,
                         selection=lightbar.selection,
                         active=(leftright == 1))
            + redraw_lightbar(lightbar, active=(leftright == 0)))


def more(cont=False):
    """
    Returns True if user 'q'uit; otherwise False
    when prompting is complete (moar/next/whatever)
    """
    from x84.bbs import echo, getch, Ansi, getterminal, LineEditor, DBProxy
    prompt_key = u'\r\n\r\nENtER BBS iD: '
    msg_badkey = u'\r\n\r\nbbS id iNVAliD!'
    term = getterminal()
    prompt = u', '.join(fancy_blue(char, blurb)
                        for char, blurb in
                        (('i', 'NfO',),
                         ('a', 'dd',),
                         ('c', 'OMMENt',),
                         ('r', 'AtE',),
                         ('t', 'ElNEt',),
                         ('v', 'ANSi'),
                         ('q', 'Uit',)))
    if cont:
        prompt += u', ' + fancy_blue(' ', 'more')
    prompt += u': '
    while True:
        echo('\r\n' + Ansi(prompt).wrap(term.width - (term.width / 3)))
        inp = getch()
        if inp in (u'q', 'Q'):
            return True
        elif inp is not None and type(inp) is not int:
            if cont and inp == u' ':
                echo('\r\n\r\n')
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


def dummy_pager():
    """
    Provide interface without pager/lightbar.
    """
    # pylint: disable=R0912
    #        Too many branches
    from x84.bbs import getterminal, echo, getch, Ansi
    term = getterminal()
    msg_header = u'// bbS liSt'
    hindent = 2
    vindent = 5
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
    while True:
        for (key, line) in bbslist:
            if key is None:  # bbs software
                echo(term.blue_reverse(line.rstrip()) + '\r\n')
                nlines += 1
            else:
                wrapd = Ansi(line).wrap(term.width - hindent)
                echo(term.bold_blue(key) + term.bold_black('. '))
                for num, line in enumerate(wrapd.split('\r\n')):
                    if num != 0:
                        echo(' ' * hindent)
                    echo(line + '\r\n')
                    nlines += 1
            if nlines and (nlines % (term.height - vindent) == 0):
                if more(True):
                    return
        # one final prompt before exit
        if more(False):
            return
    return


def add_bbs():
    """
    Prompt user for details and to add bbs to list.
    """
    # pylint: disable=R0914,R0915
    #        Too many local variables
    #        Too many statements
    from x84.bbs import getsession, getterminal, echo, LineEditor, DBProxy, ini
    from x84.bbs import getch
    session, term = getsession(), getterminal()
    echo(term.move(term.height, 0))
    empty_msg = u'\r\n\r\nVAlUE iS NOt OPtiONAl.'
    cancel_msg = u"\r\n\r\nENtER 'quit' tO CANCEl."
    saved_msg = u'\r\n\r\nSAVED AS RECORd id %s.'
    logger = logging.getLogger()
    bbs = dict()
    for bkey in DB_KEYS:
        if bkey == 'timestamp':
            value = time.strftime('%Y-%m-%d %H:%M:%S')
            bbs[bkey] = value
            continue
        elif bkey == 'ansi':
            # todo: upload ansi with xmodem .. lol !?
            value = u''
            continue
        splice = len(bkey) - (len(bkey) / 3)
        prefix = (u'\r\n\r\n  '
                  + (term.bold_red('* ') if bkey in XML_REQNOTNULL else u'')
                  + term.bold_blue(bkey[:splice])
                  + term.bold_black(bkey[splice:])
                  + term.bold_white(': '))
        led = LineEditor(40)  # !?
        led.highlight = term.green_reverse
        while True:
            echo(prefix)
            value = led.read()
            if value is not None and (value.strip().lower() == 'quit'):
                return
            if bkey in XML_REQNOTNULL:
                if value is None or 0 == len(value.strip()):
                    echo(term.bold_red(empty_msg))
                    echo(u'\r\n' + cancel_msg)
                    continue
            if bkey in ('port') and value is None or 0 == len(value):
                value = u'23'
            # TODO: telnet connect test, of course !
            bbs[bkey] = value
            break
    key = max([int(_key) for _key in DBProxy('bbslist').keys()] or [0]) + 1
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
            echo(u'\r\n\r\nrequest failed,\r\n')
            echo(u'%r' % (req.content,))
            echo(u'\r\n\r\n(code : %s).\r\n' % (req.status_code,))
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
    """ Process general keystroke and call routines.  """
    from x84.bbs import getsession, DBProxy, gosub, echo
    session = getsession()
    if inp is None:
        return False
    elif type(inp) is int:
        return False
    elif inp in (u't', u'T') and key is not None:
        bbs = DBProxy('bbslist')[key]
        gosub('telnet', bbs['address'], bbs['port'],)
    elif inp in (u'a', u'A'):
        add_bbs()
    elif inp in (u'c', u'C') and key is not None:
        add_comment(key)
    elif inp in (u'r', u'R') and key is not None:
        rate_bbs(key)
    elif inp in (u'i', u'I') and key is not None:
        echo(get_bbsinfo(key) + '\r\n')
    elif inp in (u'v', u'V') and key is not None:
        view_ansi(key)
    elif inp in (u'd', u'D') and key is not None and (
            'sysop' in session.user.groups):
        del DBProxy('bbslist')[key]
    else:
        return False  # unhandled
    return True


def add_comment(key):
    """ Prompt user to add a comment about a bbs. """
    # pylint: disable=R0914
    #        Too many local variables.
    from x84.bbs import getsession, getterminal, echo, DBProxy, LineEditor
    from x84.bbs import getch
    session, term = getsession(), getterminal()
    prompt_comment = u'\r\n\r\nWhAt YOU GOt tO SAY? '
    prompt_chg = u'\r\n\r\nChANGE EXiStiNG ? [yn] '
    echo(term.move(term.height, 0))
    echo(prompt_comment)
    comment = LineEditor(max(10, term.width - len(prompt_comment) - 5)).read()
    if comment is None or 0 == len(comment.strip()):
        return
    new_entry = (session.handle, comment)
    comments = DBProxy('bbslist', 'comments')
    comments.acquire()
    existing = comments[key]
    if session.handle in (_nick for (_nick, _cmt) in comments[key]):
        # change existing comment,
        echo(prompt_chg)
        if getch() not in (u'y', u'Y'):
            comments.release()
            return
        # re-define list without existing entry, + new entry
        comments[key] = [(_enick, _ecmt) for (_enick, _ecmt) in existing
                         if session.handle != _enick] + [new_entry]
        comments.release()
        return
    # re-define as existing list + new entry
    comments[key] = existing + [new_entry]
    comments.release()


def rate_bbs(key):
    """ Prompt user to rate a bbs. """
    # pylint: disable=R0914
    #        Too many local variables
    from x84.bbs import getsession, getterminal, echo, LineEditor, DBProxy
    from x84.bbs import getch
    session, term = getsession(), getterminal()
    prompt_rating = u'\r\n\r\nRAtE 0.0 - 4.0: '
    prompt_chg = u'\r\n\r\nChANGE EXiStiNG ? [yn] '
    msg_invalid = u'\r\n\r\niNVAlid ENtRY.\r\n'
    echo(term.move(term.height, 0) + '\r\n')
    echo(prompt_rating)
    s_rating = LineEditor(3).read()
    if s_rating is None or 0 == len(s_rating.strip()):
        return
    try:
        f_rating = float(s_rating)
    except ValueError:
        echo(msg_invalid)
        return
    if f_rating < 0 or f_rating > 4:
        echo(msg_invalid)
        return
    entry = (session.handle, f_rating)
    ratings = DBProxy('bbslist', 'ratings')
    ratings.acquire()
    if session.handle in (_handle for (_handle, _rating) in ratings[key]):
        echo(prompt_chg)
        if getch() not in (u'y', u'Y'):
            ratings.release()
            return
        # re-define list without existing entry, + new entry
        ratings[key] = [(__handle, __rating)
                        for (__handle, __rating) in ratings[key]
                        if session.handle != __handle] + [entry]
        ratings.release()
        return
    # re-define as existing list + new entry
    ratings[key] = ratings[key] + [entry]
    ratings.release()


def main():
    """ Main procedure. """
    # pylint: disable=R0914,R0912,R0915
    #        Too many local variables
    #        Too many branches
    #        Too many statements
    from x84.bbs import getsession, getterminal, echo, ini, getch, gosub
    from x84.bbs import DBProxy
    session, term = getsession(), getterminal()
    pager, lightbar = get_ui(None)

    echo(u'\r\n\r\n')
    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates()
        thread.start()
        session.activity = u'bbs lister [bbs-scene.org]'
        echo(u'fetching bbs-scene.org updates ...')
    else:
        session.activity = u'bbs lister'

    dirty = True
    # session.buffer_event('refresh', ('init',))
    leftright = 0  # 'left'

    while True:
        # check if screen requires refresh of any kind,
        if session.poll_event('refresh'):
            dirty = True
        if thread is not None:
            t_val = chk_thread(thread)
            if t_val != False:
                thread = None
                if t_val == 'dirty':
                    dirty = True
        if session.poll_event('bbslist_update'):
            while session.read_event('bbslist_update', 0.15):
                # pylint: disable=W0104
                #         Statement seems to have no effect
                None
            dirty = True

        # refresh advanced screen with lightbar and pager
        if dirty:
            if session.user.get('expert', False):
                # provide dumb terminal with hotkey prompt
                if thread is not None:
                    wait_for(thread)
                if chk_thread(thread) != False:
                    thread = None
                return dummy_pager()
            else:
                pager, lightbar = get_ui(lightbar.position)
                echo(banner())
                echo(u'\r\n' * lightbar.height)
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
