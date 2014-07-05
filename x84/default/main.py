"""
 Main menu script for x/84, http://github.com/jquast/x84
"""


def refresh():
    """ Refresh main menu. """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import getsession, getterminal, echo, showart, ini
    import os
    import logging
    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    session.activity = u'Main menu'
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'main.asc')
    echo(u''.join((
        u'\r\n\r\n',
        term.blue(u'/'.rjust(term.width / 2)), term.bold_black(u'/ '),
        term.bold('x'), term.bold_blue('/'), term.bold('84'), u' ',
        'MAiN MENU',
        u'\r\n')))
    # displays a centered main menu header in topaz encoding for utf8
    for line in showart(artfile,'topaz'):
        echo(term.cyan+term.move_x((term.width/2)-40)+line)
    echo(u'\r\n\r\n')
    entries = [
        ('$', 'rEAD bUllETiNS'),
        ('b', 'bS NEXUS'),
        ('l', 'ASt CAllS'),
        ('o', 'NE liNERS'),
        ('w', "hO'S ONliNE"),
        ('n', 'EWS'),
        ('c', 'hAt'),
        ('i', 'RC chAt'),
        ('!', 'ENCOdiNG'),
        ('t', 'EtRiS'),
        ('s', 'YS. iNfO'),
        ('u', 'SER LiST'),
        ('f', 'ORECASt'),
        ('e', 'dit PROfilE'),
        ('p', 'OSt A MSG'),
        ('r', 'EAd All MSGS'),
        ('g', 'OOdbYE /lOGOff'),]

    # add LORD to menu only if enabled,
    if ini.CFG.getboolean('dosemu', 'enabled') and (
            ini.CFG.get('dosemu', 'lord_path') != 'no'):
        entries.insert(0, ('#', 'PlAY lORd!'))

    # add sesame doors to menu if enabled
    if ini.CFG.has_section('sesame'):
        from ConfigParser import NoOptionError
        for door in ini.CFG.options('sesame'):
            if '_' in door:
                continue

            # .. but only if we have the binary
            if not os.path.exists(ini.CFG.get('sesame', door)):
                continue

            # .. and a key is configured
            try:
                key = ini.CFG.get('sesame', '{}_key'.format(door))
            except NoOptionError:
                logger.error("no key configured for sesame door '{}'".format(
                    door,
                ))
            else:
                logger.debug("added sesame door '{}' with key '{}'".format(
                    door, key
                ))
                entries.insert(0, (key, 'PlAY {}'.format(door)))

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
        ansilen = term.length(buf_str + out_str)
        if ansilen >= (term.width * .8):
            echo(term.center(buf_str) + u'\r\n\r\n')
            buf_str = out_str
        else:
            buf_str += out_str
    echo(term.center(buf_str) + u'\r\n\r\n')
    echo(u' [%s]:' % (
        term.blue_underline(''.join([key for key, name in entries]))))


def main():
    """ Main procedure. """
    # pylint: disable=R0912
    #         Too many branches
    from x84.bbs import getsession, getch, goto, gosub, ini
    from ConfigParser import Error as ConfigError
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
        elif inp == u'$':
            gosub('bulletins')
        elif inp == u'b':
            gosub('bbslist')
        elif inp == u'l':
            gosub('lc')
        elif inp == u'o':
            gosub('ol')
        elif inp == u's':
            gosub('si')
        elif inp == u'u':
            gosub('userlist')
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
        elif inp == u'i':
            gosub('ircchat')
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
            handled = False
            try:
                for option in ini.CFG.options('sesame'):
                    if option.endswith('_key'):
                        door = option.replace('_key', '')
                        key = ini.CFG.get('sesame', option)
                        if inp == key:
                            gosub('sesame', door)
                            handled = True
                            break
            except ConfigError:
                pass

            if not handled:
                dirty = False
