""" news script for x/84, https://github.com/jquast/x84 """
# std
from __future__ import division
import codecs
import math
import time
import os

# local
from x84.bbs import getterminal, getsession, echo, getch, gosub, Pager

#: filepath to folder containing this script
here = os.path.dirname(__file__)

#: filepath to news contents persisted to disk
news_file = os.path.join(os.path.dirname(__file__), 'art', 'news.txt')
#: cached global memory view of news.txt
news_contents = None
#: last modified time of news.txt
news_age = 0

#: filepath to artfile displayed for this script
art_file = os.path.join(here, 'art', 'news.ans')
#: encoding used to display artfile
art_encoding = 'cp437_art'
#: estimated art height (top of pager)
art_height = 6
#: maximum width of pager, matching with art banner
art_width = 75

#: scroller percentage glyph
scroller_glyph = u'\u25c4'
scroller_backfill = (u'\u2502' * 10) + u'\u2321 \u2320'


def get_pager(term, position=None):
    """
    Return Pager instance with content ``news_txt``.
    """
    #: pager_top: allow art to 'bleed' above border
    pager_top = (art_height - 1)
    #: use remaining window space, clipped at 40 rows.
    height = min(40, term.height - pager_top)
    width = min(art_width, term.width - 1)
    xloc = int((term.width / 2) - (width / 2))
    pager = Pager(height=height, width=width, yloc=pager_top, xloc=xloc,
                  glyphs={'left-vert': u'', 'right-vert': u''},
                  colors={'border': term.blue, },
                  content=news_contents,
                  position=position)
    #pager.xpadding = 1  # TODO: allow xpadding as kwarg, also! its broken!
    return pager


def redraw(term, pager=None):
    """ Returns string suitable for refreshing screen. """
    from x84.bbs import getterminal, showart, echo

    term = getterminal()

    # clear screen
    echo(term.pos(term.height) + term.normal + ('\r\n' * (term.height + 1)))

    # get and refresh pager
    pager = get_pager(term, pager and pager.position)
    echo(pager.border() + pager.refresh())

    # show art
    echo(term.home)
    map(echo, showart(art_file, encoding=art_encoding,
                      auto_mode=False, center=True))

    # top-right: display 'quit' hotkey
    echo(u''.join((
        pager.pos(0, pager.width - 8),
        u'{lp}{q}{colon}{uit}{rp}'
        .format(lp=term.blue(u'('),
                q=u'q',
                colon=term.bold_blue(u':'),
                uit=term.blue(u'uit'),
                rp=term.blue(u')')),
    )))

    # bottom-left: display 'hotkey mode'
    echo(u''.join((
        pager.pos(pager.height - 1, 3),
        u'{lt} {msg} {gt}'
        .format(lt=term.bold_blue(u'\\'),
                msg=term.yellow(u'hotkey mode'),
                gt=term.bold_blue(u'//')),
    )))

    # bottom-right: display keys
    echo(u''.join((
        pager.pos(pager.height - 1, pager.width - 30),
        u'{lt} {keys}{colon} {lb}up{slash}k{rb} {lb}down{slash}j{rb} {gt}'
        .format(lt=term.bold_blue('\\'),
                keys=term.yellow(u'keys'),
                colon=term.blue(u':'),
                slash=term.yellow(u'/'),
                lb=term.yellow(u'['),
                rb=term.yellow(u']'),
                gt=term.bold_blue(u'//'),)
    )))
    fixate(term, pager)
    return pager


def fixate(term, pager):
    """ Simple pct. scroller effect and fixate cursor to bottom-right. """
    marker_ypos = (pager.position / max(1, pager.bottom)) * (pager.height - 3)
    marker_ypos = pager.height - int(round(marker_ypos)) - 2

    xpos = pager.width - 1

    echo(term.blue)
    for ypos in range(1, pager.height - 1):
        offset = len(scroller_backfill) // 2
        l_indicie = (ypos - pager.position) % len(scroller_backfill)
        r_indicie = (ypos - pager.position - offset) % len(scroller_backfill)
        echo(pager.pos(ypos, 0))
        echo(scroller_backfill[l_indicie])
        echo(pager.pos(ypos, pager.width - 1))
        echo(scroller_backfill[r_indicie])
        if ypos == marker_ypos:
            echo(pager.pos(ypos, xpos - 1))
            echo(term.bold(scroller_glyph))
            echo(term.blue)
    echo(term.normal)
    echo(pager.pos(pager.height, pager.width))


def check_news():
    global news_contents, news_age
    if (news_contents is None or os.stat(news_file).st_mtime > news_age):
        news_contents = codecs.open(news_file, 'rb', 'utf8').read()
        news_age = time.time()
        return True


def has_seen(user):
    """ Returns True if news has already been read by ``user``. """
    return news_age < user.get('news_lastread', 0)


def main(quick=False):
    """
    Script entry point.

    :param quick: When True, returns early if this news has already been read.
    :type quick: bool
    """
    session, term = getsession(), getterminal()

    if not os.path.exists(news_file):
        echo(u'\r\n\rn')
        echo(term.center(u'No news.').rstrip())
        echo(u'\r\n\r\n')
        return

    pager = None
    dirty = True
    with term.hidden_cursor():
        while pager is None or not pager.quit:
            session.activity = 'Reading news'
            if check_news() or session.poll_event('refresh') or dirty:
                if quick and has_seen(session.user):
                    break
                pager = redraw(term, pager=pager)
                dirty = False
            inp = term.inkey(1)
            if inp.lower() == u'e' and session.user.is_sysop:
                new_news = gosub('editor', continue_draft=news_contents)
                if new_news:
                    codecs.open(news_file, 'wb', 'utf8').write(new_news)
                dirty = True
            else:
                echo(pager.process_keystroke(inp))
                if pager.moved:
                    fixate(term, pager)
    session.user['news_lastread'] = time.time()
