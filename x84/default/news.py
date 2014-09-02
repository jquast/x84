""" news script for x/84, https://github.com/jquast/x84 """
# std
from __future__ import division
import codecs
import math
import time
import os

# local
from x84.bbs import getterminal, getsession, gosub
from x84.bbs import Pager, LineEditor, decode_pipe
from x84.bbs import echo, showart

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
                  glyphs={'left-vert': u'', 'right-vert': u'',
                          'top-horiz': u'-', 'bot-horiz': u'-',
                          'bot-left': u'+', 'bot-right': u'+',
                          'top-left': u'+', 'top-right': u'+'},
                  colors={'border': term.blue, },
                  content=news_contents,
                  position=position)
    #pager.xpadding = 1  # TODO: allow xpadding as kwarg, also! its broken!
    return pager


def display_banner(term, pager=False):
    # clear screen
    echo(term.pos(term.height) + term.normal + ('\r\n' * (term.height + 1)))

    if pager is not False:
        # get and refresh pager
        pager = get_pager(term, pager and pager.position)
        echo(pager.border() + pager.refresh())

    # show art
    echo(term.home)
    map(echo, showart(art_file, encoding=art_encoding,
                      auto_mode=False, center=True))
    return pager


def redraw(term, pager=None):
    """ Returns string suitable for refreshing screen. """
    pager = display_banner(term, pager=pager)

    # top-right: display 'quit' hotkey
    echo(u''.join((
        pager.pos(0, pager.width - 8),
        u'{lp}{q}{colon}{uit}{rp}'
        .format(lp=term.blue(u'('),
                q=u'q',
                colon=term.bold_blue(u':'),
                uit=term.yellow(u'uit'),
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
    """ Simple Scroll-marker effect and fixate cursor to bottom-right. """
    marker_ypos = (pager.position / max(1, pager.bottom)) * (pager.height - 3)
    marker_ypos = int(round(marker_ypos)) + 1
    xpos = pager.width

    for ypos in range(1, pager.height - 1):
        glyph = scroller_glyph if ypos == marker_ypos else u' '
        echo(pager.pos(ypos, xpos) + term.bold_blue(glyph))


def check_news():
    global news_contents, news_age
    if (news_contents is None or os.stat(news_file).st_mtime > news_age):
        news_contents = codecs.open(news_file, 'rb', 'utf8').read()
        news_age = time.time()
        return True


def has_seen(user):
    """ Returns True if news has already been read by ``user``. """
    return news_age < user.get('news_lastread', 0)


def read_news_hotkeys(session, term):
    """ Read news contents using hotkeys and pager. """
    pager = None
    dirty = True
    with term.hidden_cursor():
        while pager is None or not pager.quit:
            session.activity = 'Reading news'
            if session.poll_event('refresh') or dirty or check_news():
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
        echo(u'\r\n')


def read_news_prompt(session, term):
    """ Read news using command prompt (no hotkeys). """
    session.activity = 'Reading news'
    continuous = False
    line_no = art_height

    display_banner(term, pager=False)
    echo(u'\r\n\r\n')

    colors = {'highlight': term.yellow}

    should_break = lambda line_no: line_no % (term.height - 3) == 0

    for news_line in news_contents.splitlines():
        lines = term.wrap(decode_pipe(news_line)) or [news_line]
        for txt in lines:
            echo(txt.rstrip() + u'\r\n')
            line_no += 1
            if not continuous and should_break(line_no):
                echo(term.yellow(u'- ' * ((term.width // 2) - 1)))
                echo(u'\r\n')
                echo(u'{bl}{s}{br}top, {bl}{c}{br}ontinuous, or '
                     u'{bl}{enter}{br} for next page {br} {bl}\b\b'
                     .format(bl=term.green(u'['), br=term.green(u']'),
                             s=term.yellow(u's'), c=term.yellow(u'c'),
                             enter=term.yellow(u'return')))
                while True:
                    inp = LineEditor(1, colors=colors).read()
                    if inp is None or inp and inp.lower() in u'sqx':
                        # s/q/x/escape: quit
                        echo(u'\r\n')
                        return
                    if len(inp) == 1:
                        echo(u'\b')
                    if inp.lower() == 'c':
                        # c: enable continuous
                        continuous = True
                        break
                    elif inp == u'':
                        break
                echo(term.move_x(0) + term.clear_eol)
                echo(term.move_up() + term.clear_eol)

    echo(u'\r\n\r\nPress {enter}.'.format(enter=term.yellow(u'return')))
    inp = LineEditor(0, colors=colors).read()



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
        echo(u'\r\n')
        return

    check_news()

    if quick and has_seen(session.user):
        return

    if session.user.get('hotkeys', False):
        with term.hidden_cursor():
            read_news_hotkeys(session, term)
    else:
        read_news_prompt(session, term)

    session.user['news_lastread'] = time.time()

