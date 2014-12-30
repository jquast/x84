"""
 Main menu script for x/84, http://github.com/jquast/x84
"""


def refresh():
    """ Refresh main menu. """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import getsession, getterminal, echo, showart, ini, syncterm_setfont
    import os
    import logging
    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    session.activity = u'Main menu'
    artfile = 'main*.asc'

    # tells syncterm to change to topaz, then delete the output to avoid the
    # code to be shown in other clients
    echo(syncterm_setfont('topaz') + term.move_x(0) + term.clear_eol)

    # displays a centered main menu header in topaz encoding for utf8
    for line in showart(os.path.join(os.path.dirname(__file__), 'art', artfile), 'topaz'):
        echo(term.cyan + term.move_x((term.width / 2) - 40) + line)
    echo(u'\r\n\r\n')
    entries = [
        ('$', 'rEAD bUllETiNS'),
        ('bbS', ' NEXUS'),
        ('l', 'ASt CAllS'),
        ('o', 'NE liNERS'),
        ('whO', "'S ONliNE"),
        ('n', 'EWS'),
        ('c', 'hAt'),
        ('iRC', ' chAt'),
        ('!', 'ENCOdiNG'),
        ('t', 'EtRiS'),
        ('s', 'YS. iNfO'),
        ('u', 'SER LiST'),
        ('f', 'ORECASt'),
        ('e', 'dit PROfilE'),
        ('p', 'OSt A MSG'),
        ('r', 'EAd All MSGS'),
        ('v', 'OTiNG bOOTH'),
        ('g', 'OOdbYE /lOGOff'), ]

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

    maxwidth = term.width * .8
    buf_str = u''
    for key, name in entries:
        out_str = u''.join((
            term.cyan(u'('),
            term.magenta_underline(key),
            term.cyan(u')'),
            term.white(name + '  ')))
        ansilen = term.length(buf_str + out_str)
        if ansilen >= maxwidth:
            echo(term.center(buf_str) + u'\r\n\r\n')
            buf_str = out_str
        else:
            buf_str += out_str
    echo(term.center(buf_str) + u'\r\n\r\n')


def main():
    """ Main procedure. """
    # pylint: disable=R0912
    #         Too many branches
    from x84.bbs import getsession, getterminal, getch, goto, gosub, ini
    from x84.bbs import LineEditor, echo, syncterm_setfont
    from common import waitprompt
    from ConfigParser import Error as ConfigError
    session = getsession()
    term = getterminal()

    dirty = True
    while True:
        if dirty or session.poll_event('refresh'):
            refresh()

        echo('\r' + term.underline_green + session.user.handle + term.normal +
             term.magenta + '@' + term.cyan + 'x/84 ' + term.normal + 'Command: ')
        le = LineEditor(30)
        le.colors['highlight'] = term.normal
        inp = le.read()
        # makes the input indifferent to wheter you used lower case when typing
        # in a command or not..
        inp = inp.lower()

        dirty = True
        if inp == u'*':
            goto('main')  # reload main menu using hidden option '*'
        elif inp == u'$':
            gosub('bulletins')
        elif inp == u'bbs':
            gosub('bbslist')
        elif inp == u'l':
            gosub('lc')
        elif inp == u'o':
            gosub('ol')
        elif inp == u's':
            gosub('si')
        elif inp == u'u':
            gosub('userlist')
        elif inp == u'who':
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
            # switch into cp437 for syncterm
            echo(syncterm_setfont('cp437') + term.move_x(0) + term.clear_eol)
            gosub('tetris')
        elif inp == u'c':
            gosub('chat')
        elif inp == u'irc':
            gosub('ircchat')
        elif inp == u'p':
            gosub('writemsg')
        elif inp == u'r':
            gosub('readmsgs')
        elif inp == u'v':
            gosub('vote')
        elif inp == u'g':
            goto('logoff')
        elif inp == u'!':
            gosub('charset')
        elif inp == '\x1f' and 'sysop' in session.user.groups:
            # ctrl+_, run a debug script
            gosub('debug')
        elif inp == '':
            echo('\n')
            waitprompt()
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
                echo('\r\n' + term.red + 'No such command. Try again.\r\n')
                waitprompt()

                dirty = True
