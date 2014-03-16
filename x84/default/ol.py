""" oneliners for x/84, http://github.com/jquast/x84

  To use the (optional) http://bbs-scene.org API,
  configure a section in your .ini file:

    [bbs-scene]
    user = my@email-addr.ess
    pass = my-plaintext-password
"""
import threading

# bbs-scene.org API is 50-character limit max
MAX_INPUT = 50
# scrollback / database limit
BUF_HISTORY = 500
# XML/API requests limit
XML_HISTORY = 84
# in dumb terminal mode or expert mode, wait up to
# this long for bbs-scene.org updates ('x' cancels)
WAIT_FETCH = 5


class FetchUpdates(threading.Thread):
    """ Fetch bbs-scene.org oneliners as a background thread. """
    url = 'http://bbs-scene.org/api/onelinerz?limit=%d' % (XML_HISTORY,)
    content = list()

    def run(self):
        import logging
        import time
        import requests
        import xml.etree.ElementTree
        from x84.bbs import ini
        logger = logging.getLogger()
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        logger.debug('fetching %r ..', self.url)
        stime = time.time()
        req = requests.get(self.url, auth=(usernm, passwd))
        if 200 != req.status_code:
            logger.error(req.content)
            logger.error('bbs-scene.org returned %s', req.status_code)
            return
        else:
            logger.info('bbs-scene.org returned %d in %2.2fs',
                        req.status_code, time.time() - stime)

        # can throw exceptions when xml is invalid, as a thread, nobody needs
        # to catch it. theres some things that should be CDATA wrapped .. these
        # break even viewing it in firefox, but upstream doesn't seem to
        # notice, probably upstream does print('<xml_node>' + var +
        # '</xml_node>'), i've found more than a few nasty escape flaws,
        # we're breaking the shit out of encoding here, but most other bbs's
        # are US-ASCII (cp437)-only, and bbs-api doesn't care
        buf = ''.join(filter(lambda byte: 0x20 <= ord(byte) <= 0x7d,
                             req.content))
        xml_nodes = xml.etree.ElementTree.XML(buf).findall('node')
        for node in xml_nodes:
            self.content.append(
                (node.find('id').text, dict(
                    ((key, (node.find(key).text
                            if (node.find(key) is not None and
                                node.find(key).text is not None)
                            else u'').strip()) for key in
                     ('oneliner', 'alias', 'bbsname', 'timestamp',))),))


def wait_for(thread):
    """
    for dummy or small terminals, wait until a request thread has
    gotten content before continuing, up to t WAIT_FETCH seconds.
    """
    from x84.bbs import echo, getch
    if thread.is_alive():
        echo(u"\r\n\r\nfetching bbs-scene.org oneliners .. "
             "(%s)s\b\b%s" % (' ' * 2, '\b' * 2,))
        for num in range(WAIT_FETCH):
            echo(u'%2d%s' % (WAIT_FETCH - num - 1, '\b' * 2,))
            if not thread.is_alive():
                return
            thread.join(1)  # block 1 second on thread
            if getch(0) == u'q':
                return     # allow cancel using 'q'


def chk_thread(thread):
    """
    check if bbs-scene.org thread finished, if so, farm
    its data and send updates via event 'oneliner_update' if there
    are any.
    """
    from x84.bbs import getsession, DBProxy
    import logging
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
            logger.debug('%d new entries', nlc)
            session.buffer_event('oneliner_update', True)
        else:
            logger.debug('no new bbs-scene.org entries')
        return True


def add_oneline(msg):
    """
    Add a oneliner to the local database.
    """
    import time
    from x84.bbs import getsession, DBProxy, ini
    session = getsession()
    udb = DBProxy('oneliner')
    udb.acquire()
    udb[max([int(key) for key in udb.keys()] or [0]) + 1] = {
        'oneliner': msg,
        'alias': getsession().handle,
        'bbsname': ini.CFG.get('system', 'bbsname'),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    udb.release()
    session.buffer_event('oneliner_update', True)
    session.send_event('global', ('oneliner_update', True))


def get_oltxt():
    """ Return unicode terminal string of oneliners. """
    import time
    from x84.bbs import getterminal, DBProxy, timeago, Ansi
    term = getterminal()
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    hist = [(int(k), v) for (k, v) in DBProxy('oneliner').items()]
    hist.sort()
    output = list()
    for idx, onel in hist[BUF_HISTORY * -1:]:
        color = colors[int(idx) % len(colors)]
        atime = timeago(time.time() - time.mktime(
            time.strptime(onel['timestamp'], '%Y-%m-%d %H:%M:%S'))).strip()
        output.append(u''.join((
            term.bold_white('('),
            color(atime), term.bold_black(u' ago'),
            term.bold_black(u' '),
            color(onel['alias']),
            term.bold_black(u'/'), onel['bbsname'],
            term.bold_white(u')'), color(u': '),
            Ansi(onel['oneliner']).decode_pipe(),
        )))
    return output[(BUF_HISTORY * -1):]


def get_selector(selection=u'No'):
    """ Return yes/no selector """
    from x84.bbs import getterminal, Selector
    term = getterminal()
    selector = Selector(
        yloc=term.height - 1, xloc=(term.width / 2) - 25,
        width=50, left=u'Yes', right=u'No')
    selector.keyset['left'].extend((u'y', u'Y'))
    selector.keyset['right'].extend((u'y', u'Y'))
    selector.selection = selection
    selector.colors['selected'] = term.green_reverse
    return selector


def get_pager():
    """ Returns pager window for oneliners content. """
    from x84.bbs import getterminal, Pager
    term = getterminal()
    xloc = max(3, (term.width / 2) - 50)
    width = min(term.width - 6, 100)
    pager = Pager(yloc=9, xloc=xloc, height=term.height - 12, width=width)
    pager.colors['border'] = term.blue
    return pager


def banner():
    """ Return banner """
    from x84.bbs import getterminal, Ansi, from_cp437
    import os
    term = getterminal()
    output = u''
    output += u'\r\n\r\n'
    if term.width >= 78:
        output += term.home + term.normal + term.clear
        # xzip's ansi is line-clean, center-align with terminal width,
        artfile = os.path.join(os.path.dirname(__file__), 'ol.ans')
        art = open(artfile).readlines()
        max_ans = max([len(Ansi(from_cp437(line.rstrip()))) for line in art])
        for line in art:
            padded = Ansi(from_cp437(line.rstrip())).center(max_ans)
            output += term.normal + term.blue  # minor fix for this art ;/
            output += Ansi(padded).center(term.width).rstrip() + '\r\n'
    return output + term.normal


def redraw(pager, selector):
    """ Redraw pager and selector """
    from x84.bbs import getsession, getterminal, echo
    session, term = getsession(), getterminal()
    session.flush_event('oneliner_update')
    pager.colors['border'] = term.white
    pager.glyphs['left-vert'] = u' '
    pager.glyphs['right-vert'] = u' '
    prompt_ole = u'SAY somethiNG ?!'
    pager.update(u'\n\n\nFetching ...')
    echo(u''.join((
        pager.refresh(),
        pager.border(),
        term.move(selector.yloc - 2, selector.xloc),
        term.bold_green(prompt_ole.center(selector.width).rstrip()),
        term.clear_eol,
        selector.refresh(),)))
    pager.update(u'\n'.join(get_oltxt()))
    pager.move_end()
    echo(pager.refresh())


def dummy_pager():
    """ Display oneliners for dummy terminals and prompt to saysomething """
    from x84.bbs import getterminal, Ansi, echo, getch
    term = getterminal()
    tail = term.height - 4
    indent = 3
    prompt_ole = u'\r\n\r\nSAY somethiNG ?! [yn]'
    buf = list()
    for record in get_oltxt():
        buf.extend(Ansi(record.rstrip()).wrap(
            term.width - indent).split('\r\n'))
    echo((u'\r\n' + term.normal).join(buf[tail * -1:]))
    echo(prompt_ole)
    while True:
        inp = getch()
        if inp in (u'n', u'N', u'q', term.KEY_EXIT):
            break
        if inp in (u'y', u'Y'):
            return saysomething(dumb=True)
    return


def saysomething(dumb=True):
    """
    Prompt user to post oneliner, also prompt user to post
    to bbs-scene.org if configured, returning background Thread.
    """
    import time
    from x84.bbs import getsession, getterminal, echo, LineEditor, ini
    session, term = getsession(), getterminal()
    prompt_say = u'SAY WhAt ?! '
    # heard_msg = u'YOUR MESSAGE hAS bEEN VOiCEd.'

    yloc = term.height - 3
    xloc = max(0, ((term.width / 2) - (MAX_INPUT / 2)))
    if dumb:
        echo(u'\r\n\r\n' + term.bold_blue(prompt_say))
    else:
        echo(term.move(yloc, xloc) or u'\r\n\r\n')
        echo(term.bold_blue(prompt_say))
    ole = LineEditor(MAX_INPUT)
    ole.highlight = term.green_reverse
    oneliner = ole.read()
    if oneliner is None or 0 == len(oneliner.strip()):
        if not dumb:
            # clear input line,
            echo(term.normal + term.move(yloc, 0) + term.clear_eol)
        return None

    session.user['lastliner'] = time.time()
    # post local-onlyw hen bbs-scene.org is not configured
    if not ini.CFG.has_section('bbs-scene'):
        add_oneline(oneliner.strip())
        return None
    return post_bbs_scene(oneliner, dumb)


def post_bbs_scene(oneliner, dumb=True):
    """
    Prompt for posting to bbs-scene.org oneliners API,
    returning thread if posting occured.
    """
    # pylint: disable=R0914
    #        Too many local variables
    import logging
    import xml.etree.ElementTree
    import requests
    from x84.bbs import echo, getch, getterminal, getsession, ini
    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    prompt_api = u'MAkE AN ASS Of YOURSElf ON bbS-SCENE.ORG?!'
    heard_api = u'YOUR MESSAGE hAS bEEN brOAdCAStEd.'
    yloc = term.height - 3
    if dumb:
        # post to bbs-scene.org ?
        echo('\r\n\r\n' + term.bold_blue(prompt_api) + u' [yn]')
        inp = getch(1)
        while inp not in (u'y', u'Y', u'n', u'N'):
            inp = getch()
        if inp in (u'n', u'N'):
            #  no? then just post locally
            add_oneline(oneliner.strip())
            return None
    else:
        # fancy prompt, 'post to bbs-scene.org?'
        sel = get_selector()
        sel.colors['selected'] = term.red_reverse
        echo(term.move(sel.yloc - 1, sel.xloc) or ('\r\n\r\n'))
        echo(term.blue_reverse(prompt_api.center(sel.width)))
        echo(sel.refresh())
        while not sel.selected and not sel.quit:
            echo(sel.process_keystroke(getch()))
        session.buffer_event('refresh', 'dirty')
        if sel.quit or sel.selection == sel.right:
            echo(term.normal + term.move(yloc, 0) + term.clear_eol)
            echo(term.move(sel.yloc, 0) + term.clear_eol)
            return None

    # This is an AJAX effect.
    # Dispatch a thread to fetch updates, whose callback
    # will cause the database and pager to update.
    url = 'http://bbs-scene.org/api/onelinerz.xml'
    usernm = ini.CFG.get('bbs-scene', 'user')
    passwd = ini.CFG.get('bbs-scene', 'pass')
    data = {
            'bbsname': ini.CFG.get('system', 'bbsname'),
            'alias': session.user.handle,
            'oneliner': oneliner.strip(),
            }
    # post to bbs-scene.rog
    req = requests.post(url, auth=(usernm, passwd), data=data)
    if (req.status_code != 200 or
            (xml.etree.ElementTree.XML(req.content)
                .find('success').text != 'true')):
        echo(u'\r\n\r\n%srequest failed,\r\n' % (term.clear_eol,))
        echo(u'%r' % (req.content,))
        echo(u'\r\n\r\n%s(code: %s).\r\n' % (
            term.clear_eol, req.status_code,))
        echo(u'\r\n%sPress any key ..' % (term.clear_eol,))
        logger.warn('bbs-scene.org api request failed')
        getch()
        return None
    logger.info('bbs-scene.org api (%d): %r/%r', req.status_code,
                session.user.handle, oneliner.strip())
    thread = FetchUpdates()
    thread.start()
    if not dumb:
        # clear line w/input bar,
        echo(term.normal + term.move(yloc, 0) + term.clear_eol)
        # clear line w/selector
        echo(term.move(sel.yloc, 0) + term.clear_eol)
    else:
        echo('\r\n\r\n' + heard_api)
        getch(2)
    return thread


def main():
    """ Main procedure. """
    # pylint: disable=R0912
    #        Too many branches
    from x84.bbs import getsession, getterminal, ini, echo, getch
    session, term = getsession(), getterminal()
    pager, selector = get_pager(), get_selector()

    thread = None
    if ini.CFG.has_section('bbs-scene'):
        thread = FetchUpdates()
        thread.start()
        session.activity = u'one-liners [bbs-scene.org]'
    else:
        session.activity = u'one-liners'

    # flag a pager update,
    dirty = True
    # force screen clear on first loop,
    session.buffer_event('refresh', ('init',))
    while True:
        # 1. calculate and redraw screen,
        # or enter dumb pager mode (no scrolling)
        if session.poll_event('refresh'):
            pager, selector = get_pager(), get_selector(selector.selection)
            echo(banner())
            dirty = True
        if chk_thread(thread):
            thread = None
        while session.read_event('oneliner_update', 0.15):
            dirty = True
        if dirty and (session.env.get('TERM') != 'unknown'
                      and not session.user.get('expert', False)
                      and term.width >= 78 and term.height >= 20):
            # smart terminal
            redraw(pager, selector)
            dirty = False
        elif dirty:
            # dumb terminal
            if thread is not None:
                wait_for(thread)
            if chk_thread(thread):
                thread = None
            echo(u'\r\n\r\n')
            return dummy_pager()

        # 2. detect and process keyboard input,
        inp = getch(1)
        if inp is not None:
            # input is multiplexed to both interfaces
            echo(pager.process_keystroke(inp))
            echo(selector.process_keystroke(inp))

            # selected 'yes' & return, 'say something'
            if (selector.selected and selector.selection == selector.left):
                # re-assign thread so that it is checked for updates
                thread = saysomething(dumb=False)
                # undo 'selected' state of yes/no bar,
                selector.selected = False

            # quit 'q', or selected 'no' & return
            elif (selector.selected and selector.selection == selector.right
                    or pager.quit):
                return
