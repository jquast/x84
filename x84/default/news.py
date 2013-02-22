""" news script for x/84, https://github.com/jquast/x84 """
NEWS_ART = None
NEWSAGE = 0
NEWS = None


def dummy_pager(news_txt):
    """
    Given news_txt as unicode string, display using a dummy pager.
    """
    from x84.bbs import getterminal, echo, getch
    term = getterminal()
    prompt_msg = u'\r\n[%s]ontinue, [%s]top, [%s]on-stop  ?\b\b' % (
        term.bold_blue('c'), term.bold_blue('s'), term.bold_blue('n'),)
    nonstop = False
    echo(redraw(None))
    for row in range(len(news_txt)):
        echo(news_txt[row].rstrip() + '\r\n')
        if not nonstop and row > 0 and 0 == (row % (term.height - 3)):
            echo(prompt_msg)
            inp = getch()
            if inp in (u's', u'S', u'q', u'Q', term.KEY_EXIT):
                return
            if inp in ('n', u'N'):
                nonstop = True
            echo(u'\r\n')
    echo('\r\npress any key .. ')
    getch()
    return


def get_pager(news_txt, position=None):
    """
    Return Pager instance with content ``news_txt``.
    """
    from x84.bbs import getterminal, Pager
    term = getterminal()
    width = min(130, (term.width - 2))
    height = term.height - len(redraw(None).splitlines())
    yloc = term.height - height
    xloc = (term.width / 2) - (width / 2)
    pager = Pager(height, width, yloc, xloc)
    pager.colors['border'] = term.blue
    pager.glyphs['left-vert'] = u''
    pager.glyphs['right-vert'] = u''
    pager.update('\n'.join(news_txt))
    if position is not None:
        pager.position = position
    return pager


def redraw(pager):
    """ Returns string suitable for refreshing screen. """
    from x84.bbs import getsession, getterminal
    import os
    # pylint: disable=W0603
    #         Using the global statement
    global NEWS_ART  # in-memory cache
    session, term = getsession(), getterminal()
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'news.asc')
    if NEWS_ART is None:
        NEWS_ART = [line for line in open(artfile)]
    # left-align, center, strip, and trim each line of ascii art
    ladjust = lambda line: (
        line.rstrip().center(term.width)[:term.width].rstrip())
    title = u''.join((u']- ', term.bold_blue('PARtY NEWS'), ' [-',))
    footer = u''.join((u'-[ ',
                       term.blue_underline(u'Escape'), '/',
                       term.blue_underline(u'q'), term.bold_blue(u'uit '),
                       ((u'- ' + term.blue_underline(u'e')
                           + term.bold_blue(u'dit ')) if (
                               'sysop' in session.user.groups) else u''),
                           u']-',
    ))
    return u''.join((u'\r\n\r\n',
                     '\r\n'.join(
                         (ladjust(line) for line in NEWS_ART)), u'\r\n',
                     u''.join((
                              u'\r\n' * pager.height,
                              pager.refresh(),
                              pager.border(),
                              pager.title(title),
                              pager.footer(footer),)
                              ) if pager is not None else u'',))


def main():
    """ Main procedure. """
    from x84.bbs import getsession, echo, getch, gosub
    import codecs
    import time
    import os
    # pylint: disable=W0603
    #         Using the global statement
    global NEWS, NEWSAGE  # in-memory cache
    session = getsession()
    session.activity = 'Reading news'
    newsfile = os.path.join(os.path.dirname(__file__), 'art', 'news.txt')
    if not os.path.exists(newsfile):
        echo(u'\r\n\r\nNo news.')
        return

    pager = None
    dirty = True
    while True:
        if session.poll_event('refresh'):
            dirty = True
        if dirty:
            if NEWS is None or os.stat(newsfile).st_mtime > NEWSAGE:
                # open a utf-8 file for international encodings/art/language
                NEWSAGE = time.time()
                NEWS = [line.rstrip() for line in
                        codecs.open(newsfile, 'rb', 'utf8')]
            if (session.user.get('expert', False)):
                return dummy_pager(NEWS)
            pos = pager.position if pager is not None else None
            pager = get_pager(NEWS, pos)
            echo(redraw(pager))
            dirty = False
        inp = getch(1)
        if inp is not None:
            if inp in (u'e', u'E',) and 'sysop' in session.user.groups:
                session.user['news'] = u'\r\n'.join(NEWS)
                if gosub('editor', 'news'):
                    NEWS = session.user['news'].splitlines()
                    codecs.open(newsfile, 'wb', 'utf8').write(
                        u'\r\n'.join(NEWS))
                dirty = True
            else:
                echo(pager.process_keystroke(inp))
                if pager.quit:
                    return
