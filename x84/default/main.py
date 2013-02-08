"""
 Main menu script for x/84, http://github.com/jquast/x84
"""


def refresh():
    from x84.bbs import getterminal, echo, Ansi, showcp437
    import os
    term = getterminal()
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'main.asc')
    echo(u''.join((
        u'\r\n\r\n',
        term.blue(u'/'.rjust(term.width / 2)), term.bold_black(u'/ '),
        term.bold('x'), term.bold_blue('/'), term.bold('84'), u' ',
        'MAiN MENU',
        u'\r\n')))
    for line in showcp437(artfile):
        echo(line)
    echo(u'\r\n\r\n')
    entries = (
            ('b', 'bS liStER'),
            ('l', 'ASt CAllS'),
            ('o', 'NE liNERS'),
            ('w', "hO'S ONliNE"),
            ('n', 'EWS'),
            ('$', 'EAthER fORECASt'),
            ('e', 'Edit PROfilE'),
            ('!', 'POSt A MSG'),
            ('r', 'EAd All MSGS'),
            ('g', 'OOdbYE /lOGOff'),)
    buf_str = u''
    for key, name in entries:
        out_str = u''.join((
            term.bold(u'('),
            term.bold_blue_underline(key),
            term.bold(u')'),
            term.bold_blue(name.split()[0]),
            u' ', u' '.join(name.split()[1:]),
            u'  '))
        ansilen = len(Ansi(buf_str + out_str))
        if ansilen >= (term.width * .8):
            echo(Ansi(buf_str).center(term.width) + u'\r\n\r\n')
            buf_str = out_str
        else:
            buf_str += out_str
    echo(Ansi(buf_str).center(term.width) + u'\r\n\r\n')
    echo(u' [%s]:' % (
        term.blue_underline(''.join([key for key, name in entries]))))


def main():
    from x84.bbs import getsession, getterminal, getch, goto, gosub
    session, term = getsession(), getterminal()

    choice = -1
    while True:
        if choice is not None:
            refresh()
        choice = getch(1)
        if choice == u'*':
            goto('main')  # reload main menu using hidden option '*'
        elif choice == u'b':
            gosub('bbslist')
        elif choice == u'l':
            gosub('lc')
        elif choice == u'o':
            gosub('ol')
        elif choice == u'w':
            gosub('online')
        elif choice == u'n':
            gosub('news')
        elif choice == u'$':
            gosub('weather')
        elif choice == u'p':
            gosub('profile')
        elif choice == u't':
            gosub('tetris')  # currently hidden (jojo's)
        elif choice == u'!':
            gosub('writemsg')
        elif choice == u'r':
            gosub('readmsgs')
        elif choice == u'g':
            goto('logoff')
