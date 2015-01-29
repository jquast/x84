""" Userlister for x/84. """
# std
import collections
import time
import os

# local
from x84.bbs import getsession, getterminal
from x84.bbs import echo, timeago, get_ini
from x84.bbs import get_user, list_users

from common import display_banner, prompt_pager

#: filepath to folder containing this script
here = os.path.dirname(__file__)

#: filepath to artfile displayed for this script
art_file = get_ini(
    section='userlist', key='art_file'
) or os.path.join(here, 'art', 'userlist.ans')

#: encoding of artfile
art_encoding = get_ini(
    section='userlist', key='art_encoding'
) or 'cp437'

#: preferred fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='userlist', key='syncterm_font'
) or 'topaz'

#: maximum length of user handles
username_max_length = get_ini(
    section='nua', key='max_user', getter='getint'
) or 10

#: maximum length of location, hard-coded to match art_file.
#: maximum length of user 'location' field
location_max_length = get_ini(
    section='nua', key='max_location', getter='getint'
) or 25


def iter_userlist():
    handles = sorted(list_users(), key=unicode.lower)
    timenow = time.time()
    user_record = collections.namedtuple('userlist', [
        'handle', 'location', 'timeago'])
    return (user_record(handle=user.handle,
                        location=user.location,
                        timeago=timenow - user.lastcall)
            for user in (get_user(handle) for handle in handles))


def main():
    session, term = getsession(), getterminal()
    session.activity = 'Viewing Userlist'

    colors = {'highlight': term.red,
              'lowlight': term.green, }

    line_no = display_banner(filepattern=art_file, encoding=art_encoding)

    def make_header(fmt):
        return fmt.format(
            handle=term.bold('handle'.ljust(username_max_length)),
            location=term.bold('location'.ljust(location_max_length)),
            lastcall=term.bold('time ago').ljust(8))

    userlist_fmt = u'| {handle} | {location} | {lastcall} |'

    header = make_header(userlist_fmt)
    header_length = term.length(header)

    # for smaller screens, remove 'location' field.
    if header_length > term.width:
        userlist_fmt = u'| {handle} | {lastcall} |'
        header = make_header(userlist_fmt)
        header_length = term.length(header)

    userlist = [header] + ['-' * header_length]

    for _ur in iter_userlist():
        location_txt = u''
        if 'location' in userlist_fmt:
            location_txt = colors['lowlight'](
                _ur.location.ljust(location_max_length))
        timeago_txt = timeago(_ur.timeago).ljust(8)
        handle_txt = _ur.handle.ljust(username_max_length)

        userlist.append(userlist_fmt.format(
            handle=handle_txt,
            location=location_txt,
            lastcall=timeago_txt))

    echo(u'\r\n')

    # display users, using a command-prompt pager.
    prompt_pager(content=userlist,
                 line_no=line_no + 1,
                 colors={'highlight': term.red,
                         'lowlight': term.green,
                         },
                 width=80, breaker=None)
