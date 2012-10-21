"""
Session script for x/84, https://github.com/jquast/x84

This script displays a CP437 artwork (block ansi), and prompts the user to
chose 'utf8' or 'cp437' encoding. Other than the default, 'utf8', the
Session.write() method takes special handling of a session.encoding value
of 'cp437' for encoding translation.
"""
def main():
    import textwrap
    session, term = getsession(), getterminal()
    if term.number_of_colors == 256:
        artfile = 'default/art/plant-256.ans'
    else:
        artfile = 'default/art/plant.ans'

    enc_prompt = u"Press left/right until artwork looks best. Clients " \
            "should select utf8 encoding, older clients or clients with " \
            "appropriate 8-bit fontsets can select cp437."

    def get_selector(selection):
        """
        Instantiate a new selector, dynamicly for the window size.
        """
        width = max(30, (term.width/2) - 10)
        xloc = min(0, (term.width/2)-width)
        selector = Selector (yloc=term.height-1, xloc=xloc, width=width,
                left='utf8', right='cp437')
        selector.selection = selection
        return selector

    def refresh(sel):
        flushevent ('refresh')
        if sel.selection == 'utf8':
            # ESC %G activates UTF-8 with an unspecified implementation
            # level from ISO 2022 in a way that allows to go back to
            # ISO 2022 again.
            echo (u'\033%G')
        elif sel.selection == 'cp437':
            # ESC %@ returns to ISO 2022 in case UTF-8 had been entered.
            # ESC ) K or ESC ) U Sets character set G1 to codepage 437.
            echo (u'\033%@')
            echo (u'\033)K')
            echo (u'\033)U')
        else:
            assert False, "Only encodings 'utf8' and 'cp437' supported."
        # clear & display art
        echo (term.move (0,0) + term.normal + term.clear)
        echo (showcp437 (artfile))
        echo (term.normal + u'\r\n\r\n')
        echo (u'\r\n'.join(textwrap.wrap(enc_prompt, term.width-3)) + u'\r\n')
        echo (sel.refresh ())

    selector = get_selector ('utf8')
    refresh (selector)
    while True:
        ch = getch ()
        if ch == term.KEY_ENTER:
            session.user['charset'] = session.encoding
            echo (u"\r\n\r\n'%s' is now your preferred encoding.\r\n"
                    % (session.encoding,))
            getch (1.0)
            return
        else:
            selector.process_keystroke (ch)
            if selector.quit:
                # 'escape' quits without save, though the encoding
                # has been temporarily set for this session.
                return
            if selector.moved:
                # set and refresh art in new encoding
                session.encoding = selector.selection
                refresh (selector)

        if readevent('refresh', 0) is not None:
            # instantiate a new selector in case the window size has changed.
            selector = get_selector (session.encoding)
            refresh (selector)
