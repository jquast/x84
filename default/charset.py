"""
This script helps the user select between cp437 and utf8 encoding.
"""
def main():
    import textwrap
    session, term = getsession(), getterminal()
    user = session.user
    artfile = 'art/plant.ans'
    choice_1 = 'utf8' # default
    choice_2 = 'cp437'
    choice_1txt = choice_1 + " (YES!)"
    choice_2txt = choice_2 + " (OldSChOOliN' iT)"
    enc_prompt = u"Use %s encoding? Press left/right until artwork " \
        u"looks best. Adjust your terminal encoding or font if " \
        u"necessary. %s is preferred, otherwse only %s is supported. " \
        u"Press return to accept selection." % (choice_1txt, choice_1,
            choice_2txt,)
    bar_width = max(8, (term.width/2) -10)
    selector = Selector (yloc=term.height-1, xloc=5, width=bar_width)
    selector.left = choice_1txt
    selector.right = choice_2txt
    selector.selection = choice_1txt

    def refresh(enc):
        getsession().encoding = enc
        if enc == 'cp437':
            # ESC %@ goes back from UTF-8 to ISO 2022 in case UTF-8 had been entered
            # via ESC %G.
            echo (u'\033%@')
            # ESC ) K or ESC ) U Sets character set G1 to codepage 437, for examble
            # linux vga console
            echo (u'\033)K')
            echo (u'\033)U')
        elif enc == 'utf8':
            # ESC %G activates UTF-8 with an unspecified implementation level from
            # ISO 2022 in a way that allows to go back to ISO 2022 again.
            echo (u'\033%G')

        # clear & display art
        echo (term.move (0,0) + term.clear)
        showfile (artfile)
        echo (term.normal + u'\r\n\r\n')
        echo (u'\r\n'.join(textwrap.wrap(enc_prompt, term.width-3)) + u'\r\n')
        echo (selector.refresh ())

    if user.get('charset', None) is None:
        # user has no preferred charset, use session-detected/bbs-default
        senc = session.encoding
    else:
        senc = user.get('charset')

    refresh (choice_1) # default is 'utf8'

    while True:
        (ev, data) = readevent(('input','refresh',),
            int(ini.cfg.get('session','timeout')))
        if (ev, data) == (None, None):
            raise ConnectionTimeout ('timeout selecting character set')
        if ev == 'input':
            if data in (u'\r', term.KEY_ENTER):
                # return was pressed
                set_enc = choice_1 if selector.selection == selector.left else choice_2
                user.set ('charset', set_enc)
                user.save ()
                echo (u"\r\n\r\n'%s' is now your preferred charset.\r\n" %
                        (user.get('charset'),))
                return
            echo (selector.process_keystroke (data))
            #if selector.quit:
            #    return
        if ev == 'refresh' or selector.moved:
        # re-locate lightbar; re-display art & prompt
            refresh(session.encoding)
            #selector.state = selector.laststate
