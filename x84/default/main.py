"""
 Main menu script for x/84, http://github.com/jquast/x84
"""


def refresh():
    """ Refresh main menu. """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import getsession, getterminal, echo, Ansi, showcp437, ini
    import os
    session, term = getsession(), getterminal()
    session.activity = u'Main menu'
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
    entries = [
        ('b', 'bS NEXUS'),
        ('l', 'ASt CAllS'),
        ('o', 'NE liNERS'),
        ('w', "hO'S ONliNE"),
        ('n', 'EWS'),
        ('c', 'hAt'),
        ('!', 'ENCOdiNG'),
        ('t', 'EtRiS'),
        ('s', 'YS. iNfO'),
        ('f', 'ORECASt'),
        ('e', 'dit PROfilE'),
        ('p', 'OSt A MSG'),
        ('r', 'EAd All MSGS'),
        ('g', 'OOdbYE /lOGOff'),]

    # add LORD to menu only if enabled,
    if ini.CFG.getboolean('dosemu', 'enabled') and (
            ini.CFG.get('dosemu', 'lord_path') != 'no'):
        entries.insert(0, ('#', 'PlAY lORd!'))

    if 'sysop' in session.user.groups:
        entries += (('v', 'idEO CASSEttE'),)
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
    """ Main procedure. """
    # pylint: disable=R0912
    #         Too many branches
    from x84.bbs import getsession, getch, goto, gosub
    session = getsession()

    inp = -1
    dirty = True
    while True:
        if dirty or session.poll_event('refresh'):
            refresh()
        inp = getch(1)
        dirty = True
        if inp == u'*':
            goto('main')  # reload main menu using hidden option '*'
        elif inp == u'b':
            gosub('bbslist')
        elif inp == u'l':
            gosub('lc')
        elif inp == u'o':
            gosub('ol')
        elif inp == u's':
            gosub('si')
        elif inp == u'w':
            gosub('online')
        elif inp == u'n':
            gosub('news')
        elif inp == u'f':
            gosub('weather')
        elif inp == u'e':
            gosub('profile')
        elif inp == u'#':
            gosub('lord')
        elif inp == u't':
            gosub('tetris')
        elif inp == u'c':
            gosub('chat')
        elif inp == u'p':
            gosub('writemsg')
        elif inp == u'r':
            gosub('readmsgs')
        elif inp == u'g':
            goto('logoff')
        elif inp == u'!':
            gosub('charset')
        elif inp == '\x1f' and 'sysop' in session.user.groups:
            # ctrl+_, run a debug script
            gosub('debug')
        elif inp == u'v' and 'sysop' in session.user.groups:
            # video cassette player
            gosub('ttyplay')
        else:
            dirty = False
