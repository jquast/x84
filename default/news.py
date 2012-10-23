"""
'sysop news' script for x/84, https://github.com/jquast/x84
"""


def dummy_pager(news_txt):
    term = getterminal()
    prompt_msg = u'\r\n[c]ontinue, [s]top, [n]on-stop  ?\b\b'
    nonstop = False
    echo (redraw(None))
    for row in range(len(news_txt)):
        echo (last_callers[row].rstrip() + '\r\n')
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
    width = 60
    height = term.height - 15
    yloc = 10
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
            for line in fopen('default/art/news.asc', 'r')))
    rstr += term.normal + '\r\n\r\n'
    if pager is not None:
        rstr += pager.refresh()
    return rstr

def main():
    session, term = getsession(), getterminal()
    session.activity = 'Reading news'
    news_path = 'data/news.txt'
    try:
        news_txt = '\n'.join(open(news_path).readlines())
    except IOError:
        news_txt = '`news` has not yet been comprimised.'

    if (session.env.get('TERM') == 'unknown'
            or session.user.get('expert', False) or term.width < 64):
        dummy_pager (news_txt)
        return

    echo (term.home + term.normal + term.clear)
    pager = get_pager(news_txt)
    echo (redraw(pager))
    while True:
        inp = getch(1)
        if inp is not None:
            pager.process_keystroke (inp)
            if pager.quit:
                return
        if pollevent('refresh'):
            echo (term.home + term.normal + term.clear)
            pager = get_pager(news_txt)
            echo (redraw(pager))
