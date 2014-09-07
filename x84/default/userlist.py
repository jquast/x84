""" Userlister for x/84 bbs, https://github.com/jquast/x84 """
__version__ = 1.2
__author__ = 'Hellbeard'

# std
import collections
import time
import os

# local
from x84.bbs import getsession, getterminal
from x84.bbs import echo, timeago
from x84.bbs import get_user, list_users

from common import display_banner, prompt_pager

#: filepath to folder containing this script
here = os.path.dirname(__file__)

#: filepath to artfile displayed for this script
art_file = os.path.join(here, 'art', 'userlist.ans')

#: encoding used to display artfile
art_encoding = 'topaz'

#: fontset for SyncTerm emulator
syncterm_font = 'topaz'


#: maximum length of user handles, hard-coded to match art_file.
username_max_length = 27

#: maximum length of location, hard-coded to match art_file.
location_max_length = 26

user_record = collections.namedtuple('userlist', [
    'handle', 'location', 'timeago'])


def iter_userlist():
    handles = sorted(list_users(), key=unicode.lower)
    timenow = time.time()
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

    # get and format userlist
    userlist = (
        u'{sp}{handle} {location} {lastcall}'
        .format(sp=u' ' * 4,
                handle=ur.handle.ljust(username_max_length),
                location=colors['lowlight'](
                    ur.location.ljust(location_max_length)),
                lastcall=timeago(ur.timeago))
        for ur in iter_userlist())

    echo(u'\r\n')

    # display users, using a command-prompt pager.
    prompt_pager(content=userlist,
                 line_no=line_no + 1,
                 colors={'highlight': term.red,
                         'lowlight': term.green,
                         },
                 width=80, breaker=None)
