"""
Post-login screen for x/84.

When handle is None or u'', an in-memory account 'anonymous' is created
and assigned to the session.
"""
# std
import functools
import logging
import time
import glob
import os

# local
from x84.bbs import getterminal, showart, echo, get_ini
from x84.bbs import getsession, get_user, User, LineEditor
from x84.bbs import goto, gosub, DBProxy, syncterm_setfont
from x84.default.common import (
    coerce_terminal_encoding,
    show_description,
    waitprompt,
)

# 3rd
from sauce import SAUCE

here = os.path.dirname(__file__)
log = logging.getLogger(__name__)

#: glob of art files
art_files = glob.glob(os.path.join(here, 'art', 'top', '*'))

#: encoding used for artwork
art_encoding = 'cp437_art'

#: font used for syncterm
syncterm_font = 'cp437'

#: time to pause while displaying
art_speed = 0.04

#: which sauce records to display
sauce_records = set(['author', 'title', 'group', 'date', 'filename'])

#: ssh port configured, this is displayed to the user, if you're using NAT port
#: forwarding or something like that, you'll want to set the configuration
#: value of section [ssh] for key 'advertise_port'.
ssh_port = (get_ini(section='ssh', key='advertise_port') or
            get_ini(section='ssh', key='port'))

#: maximum number of sauce columns for wide displays
max_sauce_columns = 2

#: iterator returns each line of art with given settings
idisplay_art = functools.partial(showart, encoding=art_encoding,
                                 auto_mode=False, center=True,
                                 poll_cancel=art_speed)


def _show_opt(term, keys):
    """ Display characters ``key`` highlighted as keystroke """
    return u''.join((term.bold_black(u'['),
                     term.bold_red_underline(keys),
                     term.bold_black(u']')))


def get_art_detail(art_file):
    """
    Return list of tuple (key, value) of ``art_file`` details.

    at least key and value of filename is produced, and additional
    details when ``art_file`` contains sauce records.
    """
    parsed = SAUCE(art_file)
    value = ()
    if parsed.record:
        # parse all 'sauce_records' except 'filename',
        value = tuple((attr, getattr(parsed, attr).strip())
                      for attr in sauce_records ^ set(['filename'])
                      if getattr(parsed, attr).strip())
    # inject 'filename' in return value
    return value + (('filename', os.path.basename(art_file)),)


def display_sauce(term, art_file):

    # total number of columns
    sauce_columns = min(len(sauce_records), max_sauce_columns)

    # 'value' column size
    val_adjust = 20

    # 'key' column size
    key_adjust = max(len(val) for val in sauce_records)

    # will the current tabulation fit?
    sauce_width = lambda: (
        ((key_adjust + val_adjust) * sauce_columns)
        + (len(u':' * sauce_columns))
        + (len(u' ') * sauce_columns))

    # resize until it does !
    while sauce_columns > 1 and sauce_width() >= term.width:
        sauce_columns -= 1

    # construct formatted tabular sauce data
    sauce_disp = [u'{key}{colon}{space}{value}'
                  .format(key=term.bold_black(key.rjust(key_adjust)),
                          colon=term.bold_black_underline(u':'),
                          space=u' ',
                          value=term.red(value.ljust(val_adjust)))
                  for key, value in get_art_detail(art_file)]

    # justify last row for alignment
    if sauce_disp:
        while len(sauce_disp) % sauce_columns != 0:
            sauce_disp.append(u'{key}{colon}{space}{value}'
                              .format(key=u' ' * key_adjust,
                                      colon=u' ',
                                      space=u' ',
                                      value=u' ' * val_adjust))

    # display sauce / filename data
    for idx in range(0, len(sauce_disp), sauce_columns):
        echo(term.center(
            u''.join(sauce_disp[idx:idx + sauce_columns])
        ).rstrip() + u'\r\n')


def display_prompt(term):
    """ Display prompt of user choices. """
    # show prompt
    echo(u'\r\n\r\n')
    echo(term.center(u'{0} previous - {1} change encoding - next {2}'
                     .format(_show_opt(term, u'<'),
                             _show_opt(term, u'!'),
                             _show_opt(term, u'>'))
                     ).rstrip())
    echo(term.move_up() + term.move_up() + term.move_x(0))
    echo(term.center(u'quick login {0} ?\b\b'
                     .format(_show_opt(term, u'yn'))
                     ).rstrip())


def display_intro(term, index):
    """ Display art, '!' encoding prompt, and quick login [yn] ? """

    # clear screen
    echo(term.normal)
    echo(term.move_x(0) + term.clear_eol + '\r\n\r\n' + term.clear_eol)
    echo(term.normal + ('\r\n' * (term.height + 1)) + term.home)

    # show art
    art_file = art_files[index % len(art_files)]
    line = u''
    for line in idisplay_art(art_file):
        echo(line)
    if line.strip():
        # write newline only if last line was artful
        echo(u'\r\n')
    display_sauce(term, art_file)
    echo(u'\r\n')


def get_user_record(handle):
    """
    Find and return User class instance by given ``handle``.

    If handle is ``anonymous``, Create and return a new User object.
    """
    if handle == u'anonymous':
        log.debug('anonymous login')
        return User(u'anonymous')

    log.debug('login by {0!r}'.format(handle))
    return get_user(handle)


def login(session, user):
    """
    Assign ``user`` to ``session`` and return time of last call.

    performs various saves and lookups of call records
    """
    session.user = user

    # assign timeout preference
    timeout = session.user.get('timeout', None)
    if timeout is not None:
        session.send_event('set-timeout', timeout)

    # update call records
    user.calls += 1
    user.lastcall = time.time()

    # store "from" (session id, telnet-<host>:<port>, fe.)
    user['last_from'] = session.sid

    # save user record
    if user.handle != u'anonymous':
        user.save()

    # update 'lastcalls' database
    lc_db = DBProxy('lastcalls')
    with lc_db:
        previous_call, _, _ = lc_db.get(user.handle, (0, 0, 0,))
        lc_db[user.handle] = (user.lastcall, user.calls, user.location)

    return previous_call


def do_intro_art(term, session):
    """
    Display random art file, prompt for quick login.

    Bonus: allow chosing other artfiles with '<' and '>'.
    """
    # set syncterm font, if any
    if syncterm_font and term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    index = int(time.time()) % len(art_files)
    dirty = True
    echo(u'\r\n')
    while True:
        session.activity = 'top'
        if session.poll_event('refresh') or dirty:
            display_intro(term, index)
            display_prompt(term)
            dirty = False
        dirty = True
        inp = LineEditor(1, colors={'highlight': term.normal}).read()
        if inp is None or inp.lower() == u'y':
            # escape/yes: quick login
            return True
        elif inp.lower() == u'n':
            break

        if len(inp) == 1:
            echo(u'\b')
        if inp == u'!':
            echo(u'\r\n' * 3)
            gosub('charset')
            dirty = True
        elif inp == u'<':
            index -= 1
        elif inp == u'>':
            index += 1
        else:
            dirty = False


def describe_ssh_availability(term, session):
    from x84.bbs.ini import CFG
    if session.kind == 'ssh':
        # what a good citizen!
        return

    if not (CFG.has_section('ssh') and
            not CFG.has_option('ssh', 'enabled')
            or CFG.getboolean('ssh', 'enabled')):
        # ssh not enabled
        return

    about_key = (u"You may even use an ssh key, which you can configure from "
                 u"your user profile, " if not session.user.get('pubkey')
                 else u'')
    big_msg = term.bold_blue("Big Brother is Watching You")
    description = (
        u"\r\n\r\n"
        u"    {term.red}You are using {session.kind}, but ssh is available "
        u"on port {ssh_port} of this server.  If you want a secure connection "
        u"with shorter latency, we recommend instead to use ssh!  {about_key}"
        u"Remember: {big_msg}!\r\n\r\n".format(
            term=term, session=session, ssh_port=ssh_port,
            about_key=about_key, big_msg=big_msg))

    show_description(term, description, color=None)
    waitprompt(term)


def main(handle=None):
    """ Main procedure. """
    # pylint: disable=R0914,R0912,R0915
    #         Too many local variables
    #         Too many branches
    #         Too many statements
    session, term = getsession(), getterminal()
    session.activity = 'top'

    # attempt to coerce encoding of terminal to match session.
    coerce_terminal_encoding(term, session.encoding)

    # fetch user record and register, or "log" call
    login(session, get_user_record(handle))

    # display art and prompt for quick login
    quick = do_intro_art(term, session)

    echo(term.move_down() * 3)

    if not quick:
        describe_ssh_availability(term, session)

        gosub('msgarea', quick=True)

        # only display news if the account has not
        # yet read the news since last update.
        gosub('news', quick=True)

        # display last 10 callers
        gosub('lc')

        # one-liners
        gosub('ol')

    goto('main')
