# coding=utf-8
"""
one-liners script for x/84.

To use the (optional) http://shroo.ms API,
which provides something of an intra-bbs oneliners,
configure a section in your .ini file::

    [shroo-ms]
    enabled = yes
    idkey = id-key-here-ask-frost-lol
    restkey = rest-key-here-ask-frost-too

You'll have to contact a guy named 'frost',
more than likely found on telnet://bbs.shroo.ms.
"""
import threading
import logging
import time

from x84.bbs import getsession, getterminal, echo, syncterm_setfont, LineEditor
from x84.bbs import timeago, decode_pipe
from x84.bbs import DBProxy, get_ini
from common import display_banner

#: maximum username length of bbs
username_max_length = get_ini(
    section='nua', key='max_user', getter='getint'
) or 10

#: filepath to artfile displayed for this script
art_file = get_ini(
    section='oneliners', key='art_file'
) or 'art/oneliner.ans'

#: encoding used to display artfile
art_encoding = get_ini(
    section='oneliners', key='art_encoding'
) or 'cp437'

#: fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='oneliners', key='syncterm_font'
) or 'topaz'

#: alternating colors for oneliners text
color_palette = get_ini(
    section='oneliners', key='color_palette', split=True
) or ['bright_white', 'bright_cyan', 'bright_magenta']

#: maximum length of message posting
MAX_MSGLEN = get_ini(
    section='oneliners', key='max_msglen', getter='getint'
) or 50

#: minimum seconds elapsed between posts, 0 to disable
MIN_ELAPSED = get_ini(
    section='oneliners', key='min_elapsed', getter='getint'
) or 0

#: maximum records to display, no matter the screen size
MAX_HISTORY = get_ini(
    section='oneliners', key='max_history', getter='getint'
) or 1000

#: whether shroo.ms api is enabled
shroo_ms_enabled = get_ini(
    section='shroo-ms', key='enabled', getter='getboolean')

#: shroo.ms api url
shroo_ms_api_url = get_ini(
    section='shroo-ms', key='api_url'
) or 'https://api.parse.com/1/classes/wall'

#: shroo.ms api key
shroo_ms_api_key = get_ini(
    section='shroo-ms', key='idkey')

#: shroo.ms rest key
shroo_ms_restkey = get_ini(
    section='shroo-ms', key='restkey')

#: shroo.ms named bbs for posts
system_bbsname = get_ini(
    section='system', key='bbsname')

#: returns time of given timestamp for keysort
keysort_by_datetime = lambda oneliner: (
    time.strptime(oneliner['timestamp'], '%Y-%m-%d %H:%M:%S'))


# prevents: ImportError: Failed to import _strptime because the import lock is
# held by another thread. http://bugs.python.org/issue7980
_ = time.strptime('20110101', '%Y%m%d')  # noqa


class FetchUpdatesShrooMs(threading.Thread):

    """ Fetch shroo.ms onliners as a background thread. """

    def __init__(self):
        # It's not safe to receive data from a database from
        # within a thread ... something we should address ..
        # so we do it in __init__, bug #154
        self.existing_content = DBProxy('oneliner').copy()
        self.new_content = None
        self.log = logging.getLogger(__name__)
        super(FetchUpdatesShrooMs, self).__init__()

    def run(self):
        import requests
        params = {'limit': MAX_HISTORY, 'order': '-createdAt'}
        headers = {
            'X-Parse-Application-Id': shroo_ms_api_key,
            'X-Parse-REST-API-Key': shroo_ms_restkey,
            'Content-Type': 'application/json'
        }
        # It's ok for a thread to raise an exception naturally on request,
        result = requests.get(shroo_ms_api_url, params=params, headers=headers)
        if 200 != result.status_code:
            # log non-200 error code
            self.log.error('[shroo.ms] returned %d:', result.status_code)
            self.log.error(result.content)
            return
        content = self.transform_result(result)
        self.notify_update_database(content)

    def notify_update_database(self, content):
        new_content = {}
        for key, oneliner in content:
            if str(key) not in self.existing_content:
                new_content[key] = oneliner
        if new_content:
            self.log.info('[shroo.ms] %d new entries', len(new_content))
            self.new_content = new_content
            getsession().buffer_event('oneliner', True)
        else:
            self.log.debug('[shroo.ms] no new entries')

    def transform_result(self, result):
        # strangely, convert... base-36 integers .. haliphax's work ?
        content = [(str(int(item['objectId'], 36)), dict(
            oneliner=item['bbstagline'],
            alias=item['bbsuser'],
            bbsname=self.parse_bbsname(item['bbsname']),
            timestamp=self.parse_iso8601(item['createdAt'])
        )) for item in result.json()['results']]
        return content

    @staticmethod
    def parse_bbsname(bbsname):
        # I like the aliases, rename hellbeard's
        if bbsname == 'Blood Island/x':
            return 'BI/X'
        # and maze's
        elif bbsname == 'Random Noize':
            return 'RNz'
        # and spidy's
        elif bbsname == 'BO':
            return 'BoF'
        return bbsname

    @staticmethod
    def parse_iso8601(timestamp):
        from dateutil.parser import parse
        from dateutil.tz import tzlocal
        as_localtime = parse(timestamp).astimezone(tzlocal())
        return as_localtime.strftime('%Y-%m-%d %H:%M:%S')


def post_shroo_ms(message, username):
    """ Post to shroo.ms oneliners API. """
    # std
    import json

    # 3rd-party
    import requests

    log = logging.getLogger(__name__)

    headers = {
        'X-Parse-Application-Id': shroo_ms_api_key,
        'X-Parse-REST-API-Key': shroo_ms_restkey,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        'bbsname': system_bbsname,
        'bbsuser': username,
        'bbstagline': message,
        # There is an ability to post as an alternative identity, presumably so
        # cap'n'hood of black flag bbs can impersonate people?  Anyway, we
        # always just set False, and we don't care on receipt whether the user
        # is impersonated.
        'bbsfakeuser': False,
    })
    try:
        result = requests.post(shroo_ms_api_url, data=payload, headers=headers)
    except Exception as err:
        # log exception string, cause message to post locally
        log.warn(err)
        return False
    else:
        if result.status_code >= 400:
            # log exceptions string, cause message to post locally
            log.error('[shroo.ms] returned %d:', result.status_code)
            log.error(result.content)
            return False
        log.info('(%d) OK [shroo.ms]: %s', result.status_code, message)

        # fetch our own post on shroo-ms in background
        thread = FetchUpdatesShrooMs()
        thread.start()
        return thread


# -- database functions


def do_merge_shroo_ms(new_content):
    """ Add oneliners from shroo-ms to local database. """
    udb = DBProxy('oneliner')
    with udb:
        udb.update(new_content)
    maybe_expunge_records()


def maybe_expunge_records():
    """ Check ceiling of database keys; trim-to MAX_HISTORY. """
    udb = DBProxy('oneliner')
    expunged = 0
    with udb:
        if len(udb) > MAX_HISTORY + 10:
            contents = DBProxy('oneliner').copy()
            _sorted = sorted(
                ((value, key) for (key, value) in contents.items()),
                key=lambda _valkey: keysort_by_datetime(_valkey[0]))
            for expunged, (_, key) in enumerate(
                    _sorted[len(udb) - MAX_HISTORY:]):
                del udb[key]
    if expunged:
        log = logging.getLogger(__name__)
        log.info('expunged %d records from database', expunged)


def add_oneline(session, message):
    """ Add a oneliner to the local database. """
    udb = DBProxy('oneliner')
    with udb:
        key = max([int(key) for key in udb.keys()] or [0]) + 1
        udb[key] = {
            'oneliner': message,
            'alias': getsession().user.handle,
            'bbsname': get_ini('system', 'bbsname'),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
    maybe_expunge_records()

    # tell everybody a new oneliner was posted, including our
    # -- allows it to work something like a chatroom.
    session.send_event('global', ('oneliner', True))


# -- ui functions


def get_keymap(term, offset, height):
    """ Returns a tuple of keystroke: offset mappings """
    seq = {
        term.KEY_BACKSPACE: offset + 1,
        term.KEY_DELETE: offset + 1,
        term.KEY_UP: offset + 1,
        term.KEY_DOWN: offset + -1,
        term.KEY_ENTER: offset + -1,
        term.KEY_PGUP: offset + height - 1,
        term.KEY_PGDOWN: offset + ((height - 1) * -1),
        term.KEY_HOME: MAX_HISTORY,
        term.KEY_END: 0,
    }
    # vanilla keymap is just a mapping of ascii characters and their simulated
    # keystroke codes, which just maps back into seq{}.
    van = {
        u'k': term.KEY_UP,
        u'j': term.KEY_DOWN,
        u'b': term.KEY_PGUP,
        u'f': term.KEY_PGDOWN,
        u' ': term.KEY_PGDOWN,
        u'G': term.KEY_END,
        u'0': term.KEY_HOME,
    }
    return seq, van


def say_something(term, session):
    """ Prompt user to post a 'oneliner' entry. """
    # use same line as previous prompt, clearing it first,
    echo(term.move_x(0) + term.clear_eol)
    colors = {'highlight': term.red_reverse}

    xpos = max((term.width / 2) - ((MAX_MSGLEN / 2) + 3), 0)
    echo(term.move_x(xpos))
    if MIN_ELAPSED:
        lastliner = session.user.get('lastliner', 0)
        if lastliner and time.time() - lastliner > MIN_ELAPSED:
            echo(term.red_bold("You've said enough already!"))
            term.inkey(timeout=1)
            echo(term.move_x(0))
            # only re-draw prompt (user canceled)
            return False

    echo(term.move_x(xpos))
    echo(term.red('say ') + term.bold_red('>') + u' ')
    inp = LineEditor(MAX_MSGLEN, colors=colors).read()
    if not inp or not len(inp.strip()):
        # canceled
        echo(term.move_x(0) + term.clear_eol)
        return False

    echo(term.move_x(xpos) + term.clear_eol)
    session.user['lastliner'] = time.time()

    # optionally post to shroo.ms 'global oneliners'
    if shroo_ms_enabled:
        echo(term.red_reverse('Burning, please wait ...'))
        return post_shroo_ms(message=inp, username=session.user.handle)

    # or, post locally
    add_oneline(session=session, message=inp.strip())
    return True


def display_prompt(term, yloc):
    """ Display prompt of 'say something? [yn]'. """
    # display 'Say something? [yn]', with punctuation
    # in bold and 'n' underlined (default), then move
    # cursor backwards after '?' -- centered.
    echo(term.move(yloc, 0) + term.clear_eol)
    echo(term.center(
        u''.join(('Say something',
                  term.bold_white('? ['),
                  'y',
                  term.underline('N'),
                  term.bold_white(']'),
                  '\b\b\b\b\b'))
    ).rstrip())


def get_timeago(now, given_datestr):
    """ Return '3m' or some such as 'ago' time for given datestr. """
    return timeago(now - time.mktime(
        time.strptime(given_datestr, '%Y-%m-%d %H:%M:%S'))
    ).strip()


def generate_recent_oneliners(term, n_liners, offset):
    """ return string of all oneliners, its vert. hieght and adj. offset. """
    # generate a color palette
    palette = [getattr(term, _color) for _color in color_palette]

    # for relative 'time ago'
    now = time.time()

    # fetch all liners in database, sorted ascending by time
    oneliners = sorted(DBProxy('oneliner').values(), key=keysort_by_datetime)

    # decide the start/end by given offset, to allow paging, bounds check to
    # ensure that it does not scroll out of range
    offset = min(offset, len(oneliners))
    start, end = len(oneliners) - (n_liners + offset), len(oneliners) - offset
    if start < 0:
        offset += start
        start, end = 0, end - start
    if offset < 0:
        start, end = start + offset, end + offset
        offset = 0

    # build up one large text field; refresh is smoother when
    # all text is received as a single packet
    final_text_field = u''
    count = 0
    for count, oneliner in enumerate(oneliners[start:end]):
        _color = palette[count % len(palette)]
        ago = get_timeago(now, oneliner.get('timestamp'))
        alias = oneliner.get('alias', 'anonymous')
        bbsname = ('' if not shroo_ms_enabled else
                   oneliner.get('bbsname', 'untergrund'))
        content = (oneliner.get('oneliner', u''))
        max_msglen = MAX_MSGLEN
        if len(alias) > username_max_length:
            max_msglen -= (len(alias) - username_max_length)
        for _ in range(10):
            left_part = u'{0}: {1} '.format(
                alias.rjust(username_max_length),
                term.ljust(decode_pipe(content[:max_msglen]), max_msglen)
            )
            right_part = '{0} {1}'.format(_color(bbsname.rjust(4)), ago)
            txt_field = left_part + right_part
            if term.length(txt_field) < term.width:
                break
            elif term.length(left_part) < term.width:
                txt_field = left_part
                break
            max_msglen -= 2
        final_text_field = u''.join((
            final_text_field,
            term.move_x(max(0, (term.width / 2) - 45)),
            txt_field,
            term.clear_eol,
            u'\r\n')
        )

    # return text, vertical height, and adjusted offset
    return final_text_field, count, offset


def display_oneliners(term, top_margin, offset):
    """ Display recent oneliners, return bottom margin and adj. offset. """
    _padding = 3
    n_liners = term.height - _padding - top_margin
    txt, count, offset = generate_recent_oneliners(term, n_liners, offset)
    echo(u''.join((term.move(top_margin + 1, 0),
                   txt, u'\r\n')))
    bot_margin = top_margin + count + _padding
    return bot_margin, offset


def do_prompt(term, session):
    thread = None
    if shroo_ms_enabled:
        # fetch shroo-ms api oneliners
        thread = FetchUpdatesShrooMs()
        thread.start()
    dirty = -1
    top_margin = bot_margin = 0
    offset = 0
    do_quit = False
    while not do_quit:
        if dirty == -1:
            # re-display entire screen on-load, only. there
            # should never be any need to re-draw the art here-forward.
            top_margin = display_banner(art_file, encoding=art_encoding)
            echo(u'\r\n')
            top_margin += 1
            dirty = 1

        if dirty == 1:
            # re-display all oneliners on update, or dirty == 1
            # if any shroo-ms oneliners were received, merge them
            # into the database from the main thread.
            if thread is not None and not thread.is_alive():
                if thread.new_content:
                    echo(term.move_x(0) + term.clear_eol)
                    echo(term.center(term.bold_red('This just in!')).rstrip())
                    do_merge_shroo_ms(thread.new_content)
                thread = None

            with term.hidden_cursor():
                bot_margin, offset = display_oneliners(
                    term, top_margin, offset)
            dirty = 1

        if dirty:
            # always re-prompt on any dirty flag
            session.activity = u'Viewing Oneliners'
            display_prompt(term, yloc=bot_margin)
            dirty = 0

        event, data = session.read_events(
            ('input', 'oneliner', 'refresh'))
        if event == 'refresh':
            dirty = -1
            continue
        elif event == 'oneliner':
            dirty = 1
            continue
        elif event == 'input':
            session.buffer_input(data, pushback=True)

            inp = term.inkey(0)
            while inp:
                if inp.lower() in (u'y',):
                    # say something, refresh after
                    echo(inp)
                    say_retval = say_something(term, session)
                    if isinstance(say_retval, FetchUpdatesShrooMs):
                        # a rather strange hack, we track the thread of
                        # api calls so that we can merge its final content
                        # into our local database. See __init__ for
                        # bug id and description
                        thread = say_retval
                    elif say_retval:
                        # user has said something to the local database,
                        # refresh it so that they can beam with pride ...
                        dirty = 1
                        continue

                    # only redraw prompt (user canceled)
                    dirty = 2
                elif inp.lower() in (u'n', u'q', u'\r', u'\n'):
                    echo(inp + u'\r\n')
                    do_quit = True
                    break

                elif len(inp):
                    # maybe scroll, really quite convoluted ...
                    height = bot_margin - top_margin
                    sequence_keymap, keymap = get_keymap(term, offset, height)
                    if ((inp.is_sequence and inp.code in sequence_keymap) or
                            inp in keymap):
                        _noff = sequence_keymap.get(
                            keymap.get(inp, None), offset)
                        n_offset = sequence_keymap.get(
                            inp.code, _noff)
                        if n_offset != offset:
                            offset = n_offset
                            dirty = 1
                inp = term.inkey(0)


def main():
    """ Script entry point. """
    session, term = getsession(), getterminal()

    echo(u'\r\n')

    # set syncterm font, if any
    if syncterm_font and term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))
        echo(term.move_x(0) + term.clear_eol)

    do_prompt(term, session)
