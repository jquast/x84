""" Hacker news browser for x/84.  """

from x84.bbs import getsession, getterminal, echo, LineEditor, showart, getch
import feedparser
import html2text
import urllib2
import socket
from textwrap import wrap
from common import waitprompt

__author__ = 'Hellbeard'
__version__ = 1.01

# -----------------------------------------------------------------------------


def articlereader(article):
    term = getterminal()
    text = []
    offset = 0
    keypressed = ''
    dirty = True
    inverted_text = False

    echo(term.clear + term.move(0, 0) + term.normal)
    echo(term.hide_cursor)

    for line in article:      # the string list named text will be zerobased
        # split line if it's longer than 79 columns.. when html2text screws up
        if len(line) > 79:
            tempstring = []
            tempstring = wrap(line, 79, break_long_words=True)
            for i in range(0, len(tempstring)):
                text.append(tempstring[i] + '\n')
        else:
            text.append(line + '\n')

    while True:
        if dirty == True:
            echo(term.normal + term.move(term.height, 0) + term.on_blue + term.clear_eol + term.bold('(up/down/pgup/pgdn)') +
                 term.on_blue + ' scrolls ' + term.bold('(i)') + term.on_blue + ' invert colour ' + term.bold('(q/escape) ') +
                 term.on_blue + 'quits' + term.move(term.height, term.width - 15) + term.cyan_on_blue + 'line: ' +
                 str(offset + term.height - 1) + '/' + str(len(text)))
            echo(term.move(0, 0) + term.normal)

            if inverted_text == True:
                echo(term.black_on_white)
            else:
                echo(term.white)
            for i in range(0, term.height - 1):
                if len(text) > i + offset:
                    echo(
                        term.move_x(0) +
                        term.clear_eol +
                        term.move_x(
                            (term.width /
                             2) -
                            40) +
                        text[
                            i +
                            offset])

        keypressed = getch()
        dirty = True

        if keypressed == 'q' or keypressed == 'Q' or keypressed == term.KEY_ESCAPE or keypressed == term.KEY_ENTER:
            echo(term.normal_cursor)
            break
        elif keypressed == 'i':
            if inverted_text == True:
                inverted_text = False
            else:
                inverted_text = True
        elif keypressed == term.KEY_HOME:
            offset = 0
        elif keypressed == term.KEY_END:
            if len(text) < term.height:
                offset = 0
            else:
                offset = len(text) - term.height + 1
        elif keypressed == term.KEY_DOWN:
            if len(text) > offset + term.height - 1:
                offset = offset + 1
        elif keypressed == term.KEY_UP:
            if offset > 0:
                offset = offset - 1
        elif keypressed == term.KEY_LEFT or keypressed == term.KEY_PGUP:
            if offset > term.height:
                offset = offset - term.height + 2
            else:
                offset = 0
        elif keypressed == term.KEY_RIGHT or keypressed == term.KEY_PGDOWN:
            if (offset + term.height * 2) - 1 < len(text):
                offset = offset + term.height - 2
            else:
                if len(text) < term.height:
                    offset = 0
                else:
                    offset = len(text) - term.height + 1
        else:
            dirty = False

# -----------------------------------------------------------------------------


def main():
    session, term = getsession(), getterminal()
    session.activity = 'reading news from ycombinator.com'
    echo(term.clear + term.yellow + 'firing up hACKER nEWS! *')

    feed = feedparser.parse('https://news.ycombinator.com/rss')
    article = []
    link = []
    dirty = True
    offset = 0
    wrappedarticle = []               # if the article header needs wrapping..
    # the amount of rows that a description is estimated to use.
    amount = term.height / 5

    echo(u'*')

    # buffers the articles titels, summarys and links.
    for post in feed.entries:
        article.append(post.title)
        link.append(post.link)

    while True:
        if dirty == True:
            echo(term.normal)
            for i in range(1, term.height - 1):
                echo(term.move(i, 0) + term.clear_eol)
            echo(term.move(2, 0))

            for i in range(0, amount):
                if len(article) > i + offset:
                    echo(term.magenta + str(i + offset) + '. ')
                    if len(article[i + offset]) > 79 - 4:
                        wrappedarticle = wrap(
                            article[
                                i +
                                offset],
                            79 -
                            4,
                            break_long_words=True)
                        for i2 in range(0, len(wrappedarticle)):
                            echo(term.cyan + wrappedarticle[i2] + '\r\n')
                    else:
                        echo(term.cyan + article[i + offset] + '\r\n')
                    echo(
                        term.white +
                        link[
                            i +
                            offset] +
                        '\r\n\r\n' +
                        term.normal)
            echo(term.normal + term.move(term.height, 0) + term.on_blue + term.clear_eol + '(' + term.bold('up/down') +
                 term.on_blue + ') next/previous  (' + term.bold('q/escape') + term.on_blue + ') quits  (' +
                 term.bold('enter') + term.on_blue + ') select' + term.move(term.height, term.width - 20) + term.cyan +
                 term.move(0, 0) + term.clear_eol + term.cyan + '** hacker news on ycombinator.com **' + term.normal)

        keypressed = getch()
        dirty = True

        if keypressed == 'q' or keypressed == 'Q' or keypressed == term.KEY_ESCAPE:
            break
        elif keypressed == term.KEY_DOWN:
            if (offset + amount) < len(article):
                offset = offset + amount
            else:
                # checks wheter the article has fewer lines than the screen or
                # not..
                if len(article) < amount:
                    offset = 0
        elif keypressed == term.KEY_UP:
            if offset > amount:
                offset = offset - amount
            else:
                offset = 0
        elif keypressed == term.KEY_ENTER:
            echo(
                term.move(
                    term.height,
                    0) +
                term.clear_eol +
                term.white +
                'choose your article no#: ')
            le = LineEditor(10)
            le.colors['highlight'] = term.cyan
            inp = le.read()
            if inp.isnumeric() and int(inp) < len(article):
                echo(
                    term.clear +
                    term.yellow +
                    'fetching the latest news just for you..' +
                    term.normal)
                choosenurl = link[int(inp)]
                h = html2text.HTML2Text()
                h.ignore_links = True
                h.ignore_images = True
                h.escape_all = True
                h.body_width = 79
                req = urllib2.Request(
                    choosenurl, headers={
                        'User-Agent': 'Mozilla'})  # identify as mozilla
                try:
                    text = urllib2.urlopen(req, timeout=10).read()
                except socket.timeout as e:
                    echo(
                        term.clear() +
                        term.yellow +
                        'request timed out.. try again.')
                    waitprompt()
                except urllib2.URLError as e:
                    echo(
                        term.clear() +
                        term.yellow +
                        'faulty http link.. try again.')
                    waitprompt()
                else:
                    text = unicode(h.handle(text.decode(errors='ignore')))
                    articlereader(text.split('\n'))
        else:
            dirty = False
