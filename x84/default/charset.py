"""
Session script for x/84, https://github.com/jquast/x84

This script displays a CP437 artwork (block ansi), and prompts the user to
chose 'utf8' or 'cp437' encoding. Other than the default, 'utf8', the
Session.write() method takes special handling of a session.encoding value
of 'cp437' for encoding translation.
"""

#pylint: disable=W0614
#        Unused import from wildcard import
from bbs import *

def main():
    session, term = getsession(), getterminal()
    if term.number_of_colors == 256:
        artfile = 'default/art/plant-256.ans'
    else:
        artfile = 'default/art/plant.ans'

    enc_prompt = (u'Press left/right until artwork looks best. Clients should'
            ' select utf8 encoding and Andale Mono font. Older clients or'
            ' clients with appropriate 8-bit fontsets can select cp437, though'
            ' some characters may appear as "?".')

    save_msg = u"\r\n\r\n'%s' is now your preferred encoding.\r\n"

    def get_selector(selection):
        """
        Instantiate a new selector, dynamicly for the window size.
        """
        width = max(30, (term.width/2) - 10)
        xloc = max(0, (term.width/2)-(width/2))
        selector = Selector (yloc=term.height-1, xloc=xloc, width=width,
                left='utf8', right='cp437')
        selector.selection = selection
        return selector

    def refresh(sel):
        flushevent ('refresh')
        session.encoding = selector.selection
        if sel.selection == 'utf8':
            # ESC %G activates UTF-8 with an unspecified implementation
            # level from ISO 2022 in a way that allows to go back to
            # ISO 2022 again.
            echo (unichr(27) + u'%G')
        elif sel.selection == 'cp437':
            # ESC %@ returns to ISO 2022 in case UTF-8 had been entered.
            # ESC ) U Sets character set G1 to codepage 437 .. usually.
            echo (unichr(27) + u'%@')
            echo (unichr(27) + u')U')
        else:
            assert False, "Only encodings 'utf8' and 'cp437' supported."
        # clear & display art
        echo (term.move (0, 0) + term.normal + term.clear)
        echo (showcp437 (artfile))
        echo (term.normal + u'\r\n\r\n')
        echo (Ansi(enc_prompt).wrap((term.width / 2) + (term.width / 3))) # 1/2+1/3
        echo (u'\r\n\r\n') # leave at least 2 empty lines at bottom
        echo (sel.refresh ())

    selector = get_selector ('utf8')
    refresh (selector)
    while True:
        inp = getch (1)
        if inp == term.KEY_ENTER:
            session.user['charset'] = session.encoding
            echo (save_msg % (session.encoding,))
            getch (0.5)
            return
        elif inp is not None:
            selector.process_keystroke (inp)
            if selector.quit:
                # 'escape' quits without save, though the encoding
                # has been temporarily set for this session.
                return
            if selector.moved:
                # set and refresh art in new encoding
                refresh (selector)
        if pollevent('refresh') is not None:
            logger.info ('refreshed;')
            # instantiate a new selector in case the window size has changed.
            selector = get_selector (session.encoding)
            refresh (selector)
