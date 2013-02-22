"""
Session script for x/84, https://github.com/jquast/x84

This script displays a CP437 artwork (block ansi), and prompts the user to
chose 'utf8' or 'cp437' encoding. Other than the default, 'utf8', the
Session.write() method takes special handling of a session.encoding value
of 'cp437' for encoding translation.

feedback appreciated in the refresh() method; special characters
are used to "switch" terminals from one mode to another -- do any work?
"""

import os


def get_selector(selection):
    """
    Instantiate a new selector, dynamicly for the window size.
    """
    from x84.bbs import getterminal, Selector
    term = getterminal()
    width = max(30, (term.width / 2) - 10)
    xloc = max(0, (term.width / 2) - (width / 2))
    sel = Selector(yloc=term.height - 1,
                   xloc=xloc, width=width,
                   left='utf8', right='cp437')
    sel.selection = selection
    return sel


def main():
    """ Main procedure. """
    # pylint: disable=R0912
    #        Too many branches
    from x84.bbs import getsession, getterminal, echo, getch, Ansi, from_cp437
    session, term = getsession(), getterminal()
    session.activity = u'Selecting chracter set'
    artfile = os.path.join(
        os.path.dirname(__file__), 'art', (
            'plant-256.ans' if term.number_of_colors == 256
            else 'plant.ans'))
    enc_prompt = (
        u'Press left/right until artwork looks best. Clients should'
        ' select utf8 encoding and Andale Mono font. Older clients or'
        ' clients with appropriate 8-bit fontsets can select cp437, though'
        ' some characters may appear as "?".')
    save_msg = u"\r\n\r\n'%s' is now your preferred encoding ..\r\n"
    if session.user.get('expert', False):
        echo(u'\r\n\r\n(U) UTF-8 encoding or (C) CP437 encoding [uc] ?\b\b')
        while True:
            inp = getch()
            if inp in (u'u', u'U'):
                session.encoding = 'utf8'
                break
            elif inp in (u'c', u'C'):
                session.encoding = 'cp437'
                break
        session.user['charset'] = session.encoding
        echo(save_msg % (session.encoding,))
        getch(1.0)
        return

    art = (from_cp437(open(artfile).read()).splitlines()
           if os.path.exists(artfile) else [u''])

    def refresh(sel):
        """ Refresh art and yes/no prompt, ``sel``. """
        session.flush_event('refresh')
        session.encoding = selector.selection
        if sel.selection == 'utf8':
            # ESC %G activates UTF-8 with an unspecified implementation
            # level from ISO 2022 in a way that allows to go back to
            # ISO 2022 again.
            echo(unichr(27) + u'%G')
        elif sel.selection == 'cp437':
            # ESC %@ returns to ISO 2022 in case UTF-8 had been entered.
            # ESC ) U Sets character set G1 to codepage 437 .. usually.
            echo(unichr(27) + u'%@')
            echo(unichr(27) + u')U')
        else:
            assert False, "Only encodings 'utf8' and 'cp437' supported."
        # display art, banner, paragraph, refresh selector refresh
        buf = [line for line in art]
        return u''.join((
            u'\r\n\r\n',
            u'\r\n'.join(buf),
            u'\r\n\r\n',
            Ansi(enc_prompt).wrap(int(term.width * .95)),
            u'\r\n\r\n',
            sel.refresh(),))

    selector = get_selector(session.encoding)
    echo(refresh(selector))
    while True:
        inp = getch(1)
        if inp == term.KEY_ENTER:
            session.user['charset'] = session.encoding
            echo(save_msg % (session.encoding,))
            getch(1.0)
            return
        elif inp is not None:
            selector.process_keystroke(inp)
            if selector.quit:
                # 'escape' quits without save, though the encoding
                # has been temporarily set for this session.
                return
            if selector.moved:
                # set and refresh art in new encoding
                echo(refresh(selector))
        if session.poll_event('refresh') is not None:
            # instantiate a new selector in case the window size has changed.
            selector = get_selector(session.encoding)
            echo(refresh(selector))
