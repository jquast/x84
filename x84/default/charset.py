"""
Encoding selection script for x/84, https://github.com/jquast/x84

Displays a CP437 artwork (block ansi), and prompts the user
to chose 'utf8' or 'cp437' encoding.
"""
# std imports
import os

# x/84
from x84.bbs import getsession, getterminal, echo, syncterm_setfont, LineEditor

# local
from common import display_banner

#: filepath to folder containing this script
here = os.path.dirname(__file__)

#: filepath to artfile displayed for this script
art_file = os.path.join(here, 'art', 'encoding.ans')

#: encoding used to display artfile
art_encoding = 'cp437_art'

#: fontset for SyncTerm emulator
syncterm_font = 'cp437'

#: text to display in prompt
prompt_text = (u"Chose an encoding and set font until artwork "
               u"looks best.  "

               u"SyncTerm, netrunner, and other DOS-emulating clients "
               u"should chose cp437, though internationalized languages "
               u"will appear as '?'.  "

               u"OSX Clients should chose an Andale Mono font. Linux "
               u"fonts should chose an <...> font. ")

prompt_padding = 10


def _show_opt(term, keys):
    """ Display characters ``key`` highlighted as keystroke """
    return u''.join((term.bold_black(u'['),
                     term.bold_green_underline(keys),
                     term.bold_black(u']')))


def display_prompt(term):
    """ Display prompt of user choices. """
    echo(u'\r\n\r\n')
    width = min(term.width, 80 - prompt_padding)
    for line in term.wrap(prompt_text, width):
        echo(u' ' * ((term.width - width) / 2))
        echo(line + '\r\n')

    echo(u'\r\n')
    echo(term.center(u'{0}tf8, {1}p437, {2}one:'
                     .format(_show_opt(term, u'u'),
                             _show_opt(term, u'c'),
                             _show_opt(term, u'd'))
                     ).rstrip() + u' ')


def do_select_encoding(term, session):
    editor_colors = {'highlight': term.black_on_green}
    dirty = True
    while True:
        if session.poll_event('refresh') or dirty:
            vertical_padding = 2 if term.height >= 24 else 0
            display_banner(filepattern=art_file,
                           encoding=art_encoding,
                           vertical_padding=vertical_padding)
            display_prompt(term)
            echo ({
                # ESC %G activates UTF-8 with an unspecified implementation
                # level from ISO 2022 in a way that allows to go back to
                # ISO 2022 again.
                'utf8': unichr(27) + u'%G',
                # ESC %@ returns to ISO 2022 in case UTF-8 had been entered.
                # ESC ) U Sets character set G1 to codepage 437, such as on
                # Linux vga console.
                'cp437': unichr(27) + u'%@' + unichr(27) + u')U',
            }.get(session.encoding, u''))
            dirty = False

        inp = LineEditor(1, colors=editor_colors).read()

        if inp is None or inp.lower() == 'd':
            break
        elif len(inp) == 1:
            # position cursor for next call to LineEditor()
            echo(u'\b')

        if inp.lower() == u'u' and session.encoding != 'utf8':
            session.encoding = 'utf8'
            dirty = True
        elif inp.lower() == 'c' and session.encoding != 'cp437':
            session.encoding = 'cp437'
            dirty = True


def main():
    """ Script entry point. """
    session, term = getsession(), getterminal()
    session.activity = u'Selecting character set'

    # set syncterm font, if any
    if syncterm_font and term._kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    do_select_encoding(term, session)
