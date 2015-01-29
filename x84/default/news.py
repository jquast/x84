""" news script for x/84. """
# std
import os
import time
import codecs
import logging

# local
from x84.bbs import getterminal, getsession, echo
from x84.bbs import syncterm_setfont, decode_pipe
from common import display_banner, prompt_pager

#: filepath to folder containing this script
here = os.path.dirname(__file__)

#: filepath to news contents persisted to disk
news_file = os.path.join(os.path.dirname(__file__), 'art', 'news.txt')

#: encoding of news_file
news_file_encoding = 'utf8'

#: cached global memory view of news.txt
news_contents = None

#: filepath to artfile displayed for this script
art_file = os.path.join(here, 'art', 'news.ans')

#: encoding used to display artfile
art_encoding = 'cp437'

#: fontset for SyncTerm emulator
syncterm_font = 'topaz'

#: estimated art height (top of pager)
art_height = 8

log = logging.getLogger(__name__)


def main(quick=False):
    """
    Script entry point.

    :param bool quick: When True, returns early if this news has already
                       been read.
    """
    session, term = getsession(), getterminal()

    if not os.path.exists(news_file):
        log.warn('No news file, {0}'.format(news_file))
        echo(u'\r\n\r\n' + term.center(u'No news.').rstrip() + u'\r\n')
        return

    # return early if 'quick' is True and news is not new
    news_mtime = os.stat(news_file).st_mtime
    if quick and news_mtime < session.user.get('news_lastread', 0):
        return

    # set syncterm font, if any
    if syncterm_font and term.kind == 'ansi':
        echo(syncterm_setfont(syncterm_font))

    session.activity = 'Reading news'

    # display banner
    line_no = display_banner(filepattern=art_file, encoding=art_encoding)

    # retrieve news_file contents (decoded as utf8)
    news = decode_pipe(codecs.open(
        news_file, 'rb', news_file_encoding).read()
    ).splitlines()
    echo(u'\r\n\r\n')

    # display file contents, decoded, using a command-prompt pager.
    prompt_pager(content=news,
                 line_no=line_no + 2,
                 colors={'highlight': term.yellow,
                         'lowlight': term.green,
                         },
                 width=min(80, term.width))

    # update user's last-read time of news.
    session.user['news_lastread'] = time.time()
