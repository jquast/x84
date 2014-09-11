""" oneliners for x/84, http://github.com/jquast/x84

  To use the (optional) http://bbs-scene.org API,
  configure a section in your .ini file:

    [bbs-scene]
    user = my@email-addr.ess
    pass = my-plaintext-password

  To use the (optional) http://shroo.ms API,
  configure a section in your .ini file:

    [shroo-ms]
    idkey = id-key-here-ask-frost-lol
    restkey = rest-key-here-ask-frost-too
"""
import threading
import time

# bbs-scene.org API is 50-character limit max
MAX_INPUT = 50
# scrollback / database limit
BUF_HISTORY = 500
# XML/API requests limit
XML_HISTORY = 84
# in dumb terminal mode or expert mode, wait up to
# this long for bbs-scene.org updates ('x' cancels)
WAIT_FETCH = 5


def _sort_oneliner(a, b):
    return cmp(
        time.strptime(a[1]['timestamp'], '%Y-%m-%d %H:%M:%S'),
        time.strptime(b[1]['timestamp'], '%Y-%m-%d %H:%M:%S'),
    )


class FetchUpdates(threading.Thread):
    """ Fetch bbs-scene.org oneliners as a background thread. """
    ident = 'bbs-scene.org'
    url = 'http://bbs-scene.org/api/onelinerz?limit=%d' % (XML_HISTORY,)
    content = list()

    def run(self):
        import logging
        import time
        import requests
        import xml.etree.ElementTree
        from x84.bbs import ini
        log = logging.getLogger(__name__)
        usernm = ini.CFG.get('bbs-scene', 'user')
        passwd = ini.CFG.get('bbs-scene', 'pass')
        log.debug('fetching %r ..', self.url)
        stime = time.time()
        try:
            req = requests.get(self.url, auth=(usernm, passwd))
        except requests.ConnectionError as err:
            log.error(err)
            return
        if 200 != req.status_code:
            log.error(req.content)
            log.error('bbs-scene.org returned %s', req.status_code)
            return
        else:
            log.info('bbs-scene.org returned %d in %2.2fs',
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


class FetchUpdatesShrooMs(threading.Thread):
    """ Fetch shroo.ms onliners as a background thread. """
    ident = 'shroo.ms'
    url = 'https://api.parse.com'
    api_version = 1
    content = list()

    def run(self):
        import logging
        import requests
        import time
        from x84.bbs import ini

        log = logging.getLogger(__name__)
        idkey = ini.CFG.get('shroo-ms', 'idkey')
        restkey = ini.CFG.get('shroo-ms', 'restkey')
        log.debug('fetching %r ..', self.url)

        stime = time.time()
        params = {'order': 'createdAt'}
        headers = {
            'X-Parse-Application-Id': idkey,
            'X-Parse-REST-API-Key': restkey,
        }
        result = requests.get(
            '{url}/{api_version}/classes/wall'.format(
                url=self.url,
                api_version=self.api_version,
            ),
            params=params,
            headers=headers,
        )
        if 200 != result.status_code:
            log.error(result.content)
            log.error('parse.com [shroo.ms] returned %s', result.status_code)
            return
        else:
            log.info('parse.com [shroo.ms] returned %d in %2.2fs',
                     result.status_code, time.time() - stime)
        for item in result.json()['results']:
            self.content.append((
                self.parse_object_id(item['objectId']),
                dict(
                    oneliner=item['bbstagline'],
                    alias=item['bbsuser'],
                    bbsname=item['bbsname'],
                    timestamp=self.parse_timestamp(item['createdAt']),
                )
            ))

        self.content.sort(_sort_oneliner)

    def parse_object_id(self, object_id):
        '''
        Converts a parse.com object ID to int.
        '''
        return int(object_id, 36) # lulz

    def parse_timestamp(self, timestamp):
        '''
        Converts a parse.com timestamp to a UNIX timestamp.
        '''
        zulu = time.mktime(time.strptime(timestamp[:19], '%Y-%m-%dT%H:%M:%S'))
        here = zulu - [time.timezone, time.altzone][time.daylight]
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(here))


def wait_for(thread):
    """
    for dummy or small terminals, wait until a request thread has
    gotten content before continuing, up to t WAIT_FETCH seconds.
    """
    from x84.bbs import echo, getch
    if thread.is_alive():
        echo(u"\r\n\r\nfetching %s oneliners .. "
             "(%s)s\b\b%s" % (thread.ident, ' ' * 2, '\b' * 2,))
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
    log = logging.getLogger(__name__)
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
            log.debug('%d new entries', nlc)
            session.buffer_event('oneliner_update', True)
        else:
            log.debug('no new %s entries'.format(thread.ident))
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
    from x84.bbs import getterminal, DBProxy, timeago, decode_pipe
    term = getterminal()
    colors = (term.bold_white, term.bold_green, term.bold_blue)
    hist = [(int(k), v) for (k, v) in DBProxy('oneliner').items()]
    hist.sort(_sort_oneliner)
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
            decode_pipe(onel['oneliner']),
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
    """ Return centered banner """
    from x84.bbs import getterminal, from_cp437, showcp437
    import os
    term = getterminal()
    output = u''
    output += u'\r\n\r\n' + term.normal
    if term.width >= 78:
        output += term.home + term.normal + term.clear
        artfile = os.path.join(os.path.dirname(__file__), 'art', 'ol.ans')

        for line in showcp437(artfile):
           output = output + term.move_x((term.width/2)-40)+line
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
    from x84.bbs import getterminal, echo, getch
    term = getterminal()
    tail = term.height - 4
    indent = 3
    prompt_ole = u'\r\n\r\nSAY somethiNG ?! [yn]'
    buf = list()
    for record in get_oltxt():
        buf.extend(term.wrap(term.rstrip(record),
                             term.width - indent))
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
    if ini.CFG.has_section('bbs-scene'):
        return post_bbs_scene(oneliner, dumb)
    elif ini.CFG.has_section('shroo-ms'):
        return post_shroo_ms(oneliner, dumb)
    else:
        add_oneline(oneliner.strip())
        return None


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
    log = logging.getLogger(__name__)
    session, term = getsession(), getterminal()
    prompt_api = u'MAkE AN ASS Of YOURSElf ON bbS-SCENE.ORG?!'
    heard_api = u'YOUR MESSAGE hAS bEEN brOAdCAStEd.'
    yloc = term.height - 3
    if dumb:
        # post to bbs-scene.org ?
        echo(u'\r\n\r\n' + term.bold_blue(prompt_api) + u' [yn]')
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
    try:
        req = requests.post(url, auth=(usernm, passwd), data=data)
    except requests.ConnectionError as err:
        log.warn(err)
        return
    else:
        if (req.status_code != 200 or
                (xml.etree.ElementTree.XML(req.content)
                    .find('success').text != 'true')):
            echo(u'\r\n\r\n%srequest failed,\r\n' % (term.clear_eol,))
            echo(u'%r' % (req.content,))
            echo(u'\r\n\r\n%s(code: %s).\r\n' % (
                term.clear_eol, req.status_code,))
            echo(u'\r\n%sPress any key ..' % (term.clear_eol,))
            log.warn('bbs-scene.org api request failed')
            getch()
            return None
        log.info('bbs-scene.org api (%d): %r/%r', req.status_code,
                 session.user.handle, oneliner.strip())
        thread = FetchUpdates()
        thread.start()
    if not dumb:
        # clear line w/input bar,
        echo(term.normal + term.move(yloc, 0) + term.clear_eol)
        # clear line w/selector
        echo(term.move(sel.yloc, 0) + term.clear_eol)
    else:
        echo(u'\r\n\r\n' + heard_api)
        getch(2)
    return thread


def post_shroo_ms(oneliner, dumb=True):
    """
    Prompt for posting to shroo.ms oneliners API,
    returning thread if posting occured.
    """
    # pylint: disable=R0914
    #        Too many local variables
    import json
    import logging
    import requests
    from x84.bbs import echo, getch, getterminal, getsession, ini
    log = logging.getLogger(__name__)
    session, term = getsession(), getterminal()
    prompt_api = u'MAkE AN ASS Of YOURSElf ON sHroO.mS?!'
    heard_api = u'YOUR MESSAGE hAS bEEN brOAdCAStEd.'
    yloc = term.height - 3
    if dumb:
        # post to shroo.ms ?
        echo(u'\r\n\r\n' + term.bold_blue(prompt_api) + u' [yn]')
        inp = getch(1)
        while inp not in (u'y', u'Y', u'n', u'N'):
            inp = getch()
        if inp in (u'n', u'N'):
            #  no? then just post locally
            add_oneline(oneliner.strip())
            return None
    else:
        # fancy prompt, 'post to shroo.ms?'
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
    url = 'https://api.parse.com/1/classes/wall'
    idkey = ini.CFG.get('shroo-ms', 'idkey')
    restkey = ini.CFG.get('shroo-ms', 'restkey')
    payload = json.dumps({
        'bbsname': ini.CFG.get('system', 'bbsname'),
        'bbsuser': session.user.handle,
        'bbsfakeuser': False,
        'bbstagline': oneliner.strip(),
    })
    headers = {
        'X-Parse-Application-Id': idkey,
        'X-Parse-REST-API-Key': restkey,
        'Content-Type': 'application/json'
    }
    try:
        result = requests.post(url, data=payload, headers=headers)
    except requests.ConnectionError as err:
        log.warn(err)
        return
    else:
        if result.status_code >= 400:
            log.error(result.content)
            log.error('parse.com [shroo.ms] returned %s', result.status_code)
            echo(u'\r\n\r\n%srequest failed,\r\n' % (term.clear_eol,))
            echo(u'%r' % (result.content,))
            echo(u'\r\n\r\n%s(code: %s).\r\n' % (
                term.clear_eol, result.status_code,))
            echo(u'\r\n%sPress any key ..' % (term.clear_eol,))
            getch()
            return None
        log.info('parse.com [shroo.ms] api (%d): %r/%r', result.status_code,
                 session.user.handle, oneliner.strip())
        thread = FetchUpdates()
        thread.start()
    if not dumb:
        # clear line w/input bar,
        echo(term.normal + term.move(yloc, 0) + term.clear_eol)
        # clear line w/selector
        echo(term.move(sel.yloc, 0) + term.clear_eol)
    else:
        echo(u'\r\n\r\n' + heard_api)
        getch(2)
    return thread


def main():
    """ Main procedure. """
    # pylint: disable=R0912
    #        Too many branches
    import logging
    from x84.bbs import getsession, getterminal, ini, echo, getch
    session, term = getsession(), getterminal()
    pager, selector = get_pager(), get_selector()
    log = logging.getLogger(__name__)

    thread = None
    if ini.CFG.has_section('bbs-scene'):
        log.info('starting bbs-scene.org oneliners thread...')
        thread = FetchUpdates()
        thread.start()
    elif ini.CFG.has_section('shroo-ms'):
        log.info('starting shroo.ms oneliners thread...')
        thread = FetchUpdatesShrooMs()
        thread.start()
    else:
        log.info('using built-in oneliners...')

    if thread is not None:
        session.activity = u'one-liners [%s]' % (thread.ident,)
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
        if dirty and (not session.user.get('expert', False)
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
