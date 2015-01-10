"""
Hacker news script for x/84.

Lets you browse and read popular articles on news.ycombinator.com
"""
# std imports
from __future__ import division
import collections
import urlparse
import textwrap
import math

# local
from x84.bbs import getsession, getterminal, echo, LineEditor

# 3rd-party
import feedparser
import html2text
import requests

__author__ = 'Hellbeard'
__version__ = 1.01

USER_AGENT = 'Lynx/2.8.7rel.2 libwww-FM/2.14 SSL-MM/1.4.1 OpenSSL/1.0.0a'
RSS_URL = 'https://news.ycombinator.com/rss'
RSS_TITLE = 'Hacker News'
COLOR_MAIN = "black_on_red"
COLOR_VIEW = "black_on_magenta"
ARTICLE_LIMIT = 100
REQUEST_TIMEOUT = 10

Article = collections.namedtuple(
    'Article', ['title', 'link', 'comments', 'netloc'])


def get_article(term, articles):
    echo(term.move(term.height, 0) + getattr(term, COLOR_MAIN))
    echo(term.center(''))
    echo(term.move(term.height, 0))
    echo(':: enter article #: ')
    article_idx = LineEditor(
        width=len(str(ARTICLE_LIMIT)),
        colors={'highlight': getattr(term, COLOR_MAIN)}
    ).read()
    if article_idx is None:
        # pressed escape
        return None
    try:
        return articles[int(article_idx) - 1]
    except (ValueError, IndexError):
        # not an integer, or out of range
        return None


def render_article(term, html_text):
    """ Render html text to article. """
    html_renderer = html2text.HTML2Text(bodywidth=term.width - 1)
    html_renderer.ignore_links = True
    html_renderer.ignore_images = True

    text_wrapped = []
    for line in html_renderer.handle(html_text).splitlines():
        if len(line) < term.width:
            text_wrapped.append(line)
        else:
            # html2text does not always honor `bodywidth',
            # calculate indentation (line up with previous indent)
            # and textwrap again.
            _subsq_indent = 0
            for _subsq_indent, char in enumerate(line):
                if not char.isspace():
                    break
            _indent = u' '*_subsq_indent
            text_wrapped.extend(textwrap.wrap(line, term.width - 1,
                                              subsequent_indent=_indent))
    final = [_text.rstrip() for _text in text_wrapped]
    if not final or not any(_line for _line in final):
        final = [''] * (term.height // 2)
        final.extend(
            textwrap.wrap("I'm sorry, the page you requested cannot be "
                          "displayed in textmode.  It's probably not worth "
                          "*readying* anyway ...", term.width - 1)
        )
    return final


def render_article_summaries(term, articles):
    results = []
    for idx, article in enumerate(articles, 1):
        _idx = '{0}{1}'.format(idx, term.bold_black('.'))
        _title = article.title
        _netloc = term.bold_black('({0})'.format(article.netloc))
        results.append(u' '.join((_idx, _title, _netloc)))
    return results


def render_summary(term, scroll_idx, height, articles):
    # _vpadd: larger terminals get an extra space between summaries
    _vpadd= 2 if term.height > 25 else 1
    _endline = term.clear_eol + u'\r\n'

    line_no = 0

    # render all articles,
    output = u''
    _start, _end = scroll_idx, (scroll_idx + (height // _vpadd))
    for line in articles[_start:_end]:
        # calculate indentation (after first ' ').
        _subsq_indent = ((term.strip_seqs(line[:30]).find(' ') or -1) + 1)

        # render each line, wrapping to terminal width
        for subline in term.wrap(line, subsequent_indent=u' ' * _subsq_indent):
            if line_no < height:
                output = u''.join((output, subline, _endline))
                line_no += 1

        # add additional padding between articles if room remains
        if line_no + (_vpadd - 1) < height:
            output = u''.join((output, _endline * (_vpadd- 1)))
            line_no += (_vpadd- 1)

        else:
            # no more room remains; break early.
            break

    return output


def view_article(term, session, url, title, encoding):
    # context help
    keyset_help = (u'[r]eturn - (pg)up/down - [{0}%] - [s]hare')

    # display 'fetching ...'
    echo(term.move(term.height, 0))
    fetch_txt = 'fetching {0}'.format(url)
    echo(term.center(fetch_txt[:term.width]))

    # perform get request,
    headers = {'User-Agent': USER_AGENT}
    req = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

    if 200 != req.status_code:
        # display 404, 500, or whatever non-200 code returned.
        echo(term.move(term.height, 0))
        echo(term.center('failed: status_code={0}'.format(req.status_code)))
        term.inkey()
        return

    # translate to our session-native encoding,
    req.encoding = encoding
    html_text = req.text

    _endline = term.clear_eol + u'\r\n'
    bottom = -1
    article_text = u''
    scroll_idx = 0
    last_width, last_height = -1, -1
    quit = False
    dirty = True
    while not quit:
        if dirty:
            if last_width != term.width or last_height != term.height:
                # screen size has changed, re-calculate rendered contents
                page_height = term.height - 2
                article_text = render_article(term, html_text)
                last_width, last_height = term.width, term.height
                bottom = len(article_text) - page_height

            # display titlebar
            echo(term.home)
            echo(getattr(term, COLOR_VIEW)(
                title[:term.width].center(term.width)))

            # display page at offset
            echo(term.move(1, 0))
            page = slice(scroll_idx, scroll_idx + page_height)
            for line in article_text[page]:
                echo(line + _endline)
            echo(term.clear_eos)

            # calculate pct
            pct = min(int(math.ceil(((scroll_idx + page_height)
                                     / len(article_text)) * 100)
                          ), 100)

            # display context help
            echo(term.move(term.height, 0))
            echo(getattr(term, COLOR_VIEW)(
                keyset_help.format(pct)[:term.width]
                .center(term.width)))

            dirty = False

        # block until screen refresh or keyboard input
        event, data = session.read_events(('refresh', 'input'))

        if event == 'refresh':
            dirty = 2
            continue

        elif event == 'input':
            session.buffer_input(data, pushback=True)
            inp = term.inkey(0)
            while inp:
                if inp == u'\x0c':
                    # refresh (^L)
                    dirty = 2
                elif inp.lower() in (u'r', u'q',):
                    quit = True
                    break
                elif (inp.code in (term.KEY_DOWN,) or inp in (u'j',)):
                    if scroll_idx < bottom:
                        scroll_idx += 1
                        dirty = 2
                elif (inp.code in (term.KEY_UP,) or inp in (u'k',)):
                    if scroll_idx > 0:
                        scroll_idx -= 1
                        dirty = 2
                elif (inp.code in (term.KEY_PGDOWN, term.KEY_ENTER,) or
                      inp in (u'f',)):
                    if scroll_idx < bottom:
                        scroll_idx = min(scroll_idx + page_height, bottom)
                        dirty = 2
                elif (inp.code in (term.KEY_PGUP,) or inp in (u'b',)):
                    if scroll_idx > 0:
                        scroll_idx = max(scroll_idx - page_height, 0)
                        dirty = 2
                elif (inp.code in (term.KEY_HOME,) or inp in (u'0',)):
                    if scroll_idx != 0:
                        scroll_idx = 0
                        dirty = 2
                elif (inp.code in (term.KEY_END,) or inp in (u'G',)):
                    if scroll_idx != bottom:
                        scroll_idx = bottom
                        dirty = 2
                elif inp.lower() in (u'r', u'q',):
                    quit = True
                    break
                elif inp in ('s',):
                    # share url
                    echo(term.move(term.height, 0))
                    echo(term.center(url))
                    dirty = True
                    term.inkey()
                inp = term.inkey(0)


def main(rss_url=None, rss_title=None):
    session, term = getsession(), getterminal()
    session.activity = 'reading hackernews'
    rss_url = rss_url or RSS_URL
    rss_title = rss_title or RSS_TITLE
    keyset_help = (u'[q]uit - up/down - [v]iew - [c]omments')

    # move to bottom of screen, reset attribute
    echo(term.move(term.height, 0) + term.normal)

    # create a new, empty screen
    echo(u'\r\n' * (term.height + 1))

    # fetch rss feed articles
    echo(term.move(term.height // 2, 0))
    echo(term.center('Fetching {0} ...'.format(term.bold(rss_url))).rstrip())
    result = feedparser.parse(rss_url)
    assert result['status'] == 200

    articles = [Article(title=post.title,
                        link=post.link,
                        comments=post.comments,
                        netloc=urlparse.urlparse(post.link).netloc)
                for post in result.entries][:ARTICLE_LIMIT]

    dirty = 2
    quit = False
    bottom = -1
    rendered_articles = []
    scroll_idx = 0
    last_width, last_height = -1, -1

    while not quit:

        if dirty == 2:
            # dirty value of '2' is full screen refresh,
            if last_width != term.width or last_height != term.height:
                # screen size has changed, re-calculate rendered contents
                page_height = term.height - 2
                rendered_articles = render_article_summaries(term, articles)
                last_width, last_height = term.width, term.height

            # display titlebar
            echo(term.home)
            echo(getattr(term, COLOR_MAIN)(
                rss_title[:term.width].center(term.width)))

            # display page summary of articles by scroll index
            echo(render_summary(
                term=term, scroll_idx=scroll_idx,
                height=page_height, articles=rendered_articles))
            echo(term.clear_eos)

        if dirty > 0:
            # dirty value of '1' or more is context-bar refresh
            echo(u''.join((
                term.move(term.height, 0),
                getattr(term, COLOR_MAIN)(
                    keyset_help[:term.width].center(term.width)))
            ))
            dirty = 0

        # block until screen refresh or keyboard input
        event, data = session.read_events(('refresh', 'input'))

        if event == 'refresh':
            dirty = 2
            continue

        elif event == 'input':
            session.buffer_input(data, pushback=True)
            inp = term.inkey(0)
            while inp:
                if inp == u'\x0c':
                    # refresh (^L)
                    dirty = 2
                elif (inp.code in (term.KEY_DOWN,) or
                        inp in (u'j',)):
                    if scroll_idx < bottom:
                        scroll_idx += 1
                        dirty = 2
                elif (inp.code in (term.KEY_UP,) or
                        inp in (u'k',)):
                    if scroll_idx > 0:
                        scroll_idx -= 1
                        dirty = 2
                elif inp.lower() in (u'q',):
                    quit = True
                    break
                elif inp in (u'v', 'c'):
                    article = get_article(term, articles)
                    if article is not None:
                        url = {u'v': article.link,
                               u'c': article.comments
                               }[inp]
                        view_article(term=term, session=session,
                                     url=url, title=article.title,
                                     encoding=session.encoding)
                        dirty = 2
                    else:
                        # refresh only input bar
                        dirty = 1
                    break

                inp = term.inkey(0)
