"""
'sysop news' script for x/84, https://github.com/jquast/x84
"""

import os
#pylint: disable=W0614
#        Unused import from wildcard import
from x84.bbs import *

def dummy_pager(news_txt):
    term = getterminal()
    prompt_msg = u'\r\n[c]ontinue, [s]top, [n]on-stop  ?\b\b'
    nonstop = False
    echo (redraw(None))
    for row in range(len(news_txt)):
        echo (news_txt[row].rstrip() + '\r\n')
        if not nonstop and row > 0 and 0 == (row % (term.height-1)):
            echo (prompt_msg)
            inp = getch()
            if inp in (u's', u'S', u'q', u'Q', term.KEY_EXIT):
                return
            if inp in ('n', u'N'):
                nonstop = True
    echo ('\r\npress any key .. ')
    getch ()
    return

def get_pager(news_txt):
    term = getterminal()
    width = term.width-6
    yloc = min(10, max(0,term.height - 10))
    height = term.height - yloc - 1
    xloc = max(5, int((float(term.width) / 2) - (float(width) / 2)))
    pager = Pager(height, width, yloc, xloc)
    pager.xpadding = 1
    pager.ypadding = 1
    pager.colors['border'] = term.red
    pager.update (news_txt)
    return pager

def redraw(pager):
    term = getterminal ()
    rstr = term.normal + '\r\n\r\n'
    if term.width >= 64:
        rstr += '\r\n'.join((line.rstrip().center(term.width).rstrip()
            for line in open(os.path.join(
                os.path.dirname(__file__), 'art', 'news.asc'))))
    rstr += term.normal + '\r\n\r\n'
    if pager is not None:
        rstr += pager.refresh()
        rstr += pager.border()
    return rstr

def main():
    import codecs
    session, term = getsession(), getterminal()
    session.activity = 'Reading news'
    news_path = os.path.join(os.path.dirname(__file__), 'art', 'news.txt')
    try:
        news_txt = codecs.open(news_path, encoding='utf8').readlines()
    except IOError:
        news_txt = ('`news` has not yet been comprimised.',)

    if (session.env.get('TERM') == 'unknown'
            or session.user.get('expert', False) or term.width < 64):
        dummy_pager (news_txt.split('\n'))
        return

    echo (term.home + term.normal + term.clear)
    pager = get_pager(u'\n'.join(news_txt))
    echo (redraw(pager))
    while True:
        inp = getch(1)
        if inp is not None:
            echo (pager.process_keystroke (inp))
            if pager.quit:
                return
        if session.poll_event('refresh'):
            echo (term.home + term.normal + term.clear)
            pager = get_pager(u'\n'.join(news_txt))
            echo (redraw(pager))
