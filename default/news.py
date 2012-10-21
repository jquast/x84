"""
 Sysop News script for X/84, http://1984.ws
 Simply edit text file of NEWS_PATH.
"""

NEWS_PATH = 'data/news.txt'
TIMEOUT = 1984

def main():
    import time
    session = getsession()
    session.activity = 'Reading news'
    term = session.terminal
    expert = session.user.get('expert', False)

    def refresh_all(text):
        """ Refresh screen, return None if expert mode,
            otherwise a pager object refreshed with text.
        """
        flushevent ('refresh')
        art = fopen('default/art/news.asc').readlines()
        art_width = max([len(Ansi(line)) for line in art])
        echo (term.move (0,0) + term.clear + '\r\n\r\n')
        if expert:
            if term.width > art_width +2:
                echo ('\r\n'.join (art,))
            return # no pager window
        if term.width < art_width +2:
            return # no pager window

        # initialize and display pager border
        align_x = min(1, (term.width/2) -(art_width/2))+4
        p= Pager(height=term.height -len(art) -4, width=art_width +4,
                yloc=len(art)+3, xloc=align_x)
        p.padding = 2
        p.ypadding = 1

        # overlay ascii art
        for y, line_txt in enumerate(art):
            for x in range(len(line_txt)):
                if line_txt[x] != ' ':
                    x +=1
                    break
            x = align_x + 1 \
                if len(line_txt) == 1 \
                else align_x +x
            echo (term.move (y+4, x))
            echo (line_txt.lstrip() + u'\r\n')

        # now fill pager window with content & refresh
        echo (p.update (text))
        echo (term.move (0,0))
        echo ('%dx%d' % (term.width, term.height,))
        return p

    try:
        news_content = '\n'.join(open(NEWS_PATH).readlines())
    except IOError:
        news_content = '%s not found -- no news :)\n' \
            % (abspath(NEWS_PATH,))
    pager = refresh_all(news_content)

    POLL = 0.1
    t = 0
    while 0 != len(news_content):
        t -= time.time()
        event, data = readevents (('refresh', 'input',), 0.1)
        t += time.time()
        if (None, None) == (event, data):
            if t > TIMEOUT:
                logger.info ('news/timeout exceeded')
                gosub ('logoff')
        else:
            t = 0 # last-key

        if expert is False and term.height < 10 or term.width < 40:
            echo (''.join ((term.move(0, 0), term.clear, term.bold_red,
              'screen size smaller than 40x10; ', 'switching to expert mode.',
              term.normal,)))
            expert = True
            getch(1)

        if event == 'refresh':
            print 'refresh got!'
            pager = refresh_all (news_content)

        elif event == 'input':
            if data in (term.KEY_EXIT, 'q', 'Q',):
                return
            if expert:
                if data in (' ', term.KEY_NPAGE):
                    news_content = news_content[term.height -2:]
                if data in (term.KEY_DOWN, term.KEY_ENTER):
                    news_content = news_content[1:]
            else:
                echo (pager.process_keystroke (data))
