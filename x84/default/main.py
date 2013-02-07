"""
 Main menu script for x/84, http://github.com/jquast/x84
"""


def refresh():
    from x84.bbs import getterminal, echo, Ansi, from_cp437
    import os
    " refresh main menu screen "
    term = getterminal()
    echo(u''.join((term.normal, term.clear, term.normal_cursor)))
    art = ([Ansi(from_cp437(line)) for line in open(os.path.join(
        os.path.dirname(__file__), 'art', 'main.asc'))])

    def disp_art():
        for line in art:
            echo((line.rstrip().center(term.width).rstrip())[:term.width - 1]
                 + u'\r\n')

    def disp_entry(char, blurb):
        return Ansi(term.bold_blue('(') + term.blue_reverse(char)
                    + term.bold_blue + ')' + term.bright_white(blurb) + u' ')

    def pos_row(n):
        art_row = 12
        art_middl = 8
        art_width = 30
        return term.move(min(term.height - (art_row - n),
                             max(len(art) - art_row,
                                 art_middl + n)),
                         max(1, (term.width / 2) - art_width)
                         ) or '\r\n'

    disp_art()
    # group 1,
    echo(pos_row(0))
    echo(disp_entry('b', 'bS liStER'))
    echo(disp_entry('l', 'ASt CAllS'))
    echo(disp_entry('o', 'NE liNERS'))
    echo(disp_entry('$', "WhO'S ONliNE"))
    # group 2,
    echo(pos_row(2))
    echo(disp_entry('n', 'NEWS'))
    echo(disp_entry('w', 'EAthER fORECASt'))
    echo(disp_entry('p', 'ROfilE EditOR'))
    # group 3,
    echo(pos_row(4))
    echo(disp_entry('!', 'POSt A MSG'))
    echo(disp_entry('r', 'EAd All MSGS'))
    echo(disp_entry('g', 'OOdbYE/lOGOff'))
    echo(u'\r\n\r\n')
    echo(term.move(term.height - 1))


def main():
    from x84.bbs import getsession, getterminal, getch, goto, gosub
    session, term = getsession(), getterminal()

    dirty = True
    while True:
        if dirty or session.poll_event('refresh'):
            refresh()
            dirty = False
        choice = getch(1)
        if choice == u'*':
            # reload main menu using hidden option '*'
            # for making changes to main.py
            goto('main')
        # group 1,
        elif choice == u'b':
            gosub('bbslist')
            dirty = True
        elif choice == u'l':
            gosub('lc')
            dirty = True
        elif choice == u'o':
            gosub('ol')
            dirty = True
        elif choice == u'$':
            gosub('online')
            dirty = True
        # group 2,
        elif choice == u'n':
            gosub('news')
            dirty = True
        elif choice == u'w':
            gosub('weather')
            dirty = True
        elif choice == u'p':
            gosub('profile')
            dirty = True
        # group 3,
        elif choice == u'!':
            gosub('writemsg')
            dirty = True
        elif choice == u'r':
            gosub('readmsgs')
            dirty = True
        elif choice == u'g':
            goto('logoff')
