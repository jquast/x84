"""
 Example code for a simple, lightbar based main menu for x/84, 
 http://github.com/jquast/x84

 simply copy lb_main.py over to main.py (remember to make a backup
 of the original main.py first !!)
"""

__author__ = 'megagumbo'
__version__ = 1.0

def lb_init(position=None,menu_index=None):
    """ Initialize Lightbar Main Menu """
    from x84.bbs import getsession, getterminal, echo, showart, ini, Lightbar
    import os
    import logging

    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    session.activity = u'Lightbar Main menu'

    # set up lightbar pager, determine terminal dimensions
    term = getterminal()
    height = term.height - 11
    lb_width = int(term.width * .4)
    lb_xloc = int(term.width * .3)
    lightbar = Lightbar(height, lb_width, (term.height - height - 1), lb_xloc)

    # Lightbar main menu entries
    entries = [
        #('',  '-----[COmMs]-----'),
        ('$', 'rEAD bUllETiNS'),
        ('n', 'latest nEWS'),
        ('p', 'pOSt A MSG'),
        ('r', 'rEAd All MSGS'),
        ('c', 'chAt'),
        ('i', 'iRC chAt'),
        #('',  '                  '),
        #('',  '----[SeRVIcES]----'),
        ('l', 'lASt CAllS'),
        ('o', 'oNE liNERS'),
        ('b', 'bbS NEXUS'),
        ('f', 'WeAThER fORECASt'),
        ('t', 'tEtRiS'),
        ('w', "whO'S ONliNE"),
        #('',  '                  '),
        #('',  '-----[SySTeM]-----'),
        ('!', 'ENCOdiNG'),
        ('s', 'sYS. iNfO'),
        ('u', 'uSER LiST'),
        ('e', 'edit PROfilE'),]
    
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

    entries += (('g', 'gOOdbYE /lOGOff'),)

    lightbar.update( entries )

    if menu_index is not None:
        lightbar.goto(menu_index)    

    # set up some nice colors
    lightbar.colors['highlight'] = term.bold_cyan_reverse
    lightbar.colors['border'] = term.bold_blue
    lightbar.xpadding, lightbar.ypadding = 2, 1
    lightbar.alignment = 'center'
 
    # set lightbar theme
    #lightbar.init_theme()

    ## re-select previous selection
    if position is not None:
        lightbar.position = position
    return (lightbar)


def lb_refresh(lb_pager=None):
    """ Refresh lightbar main menu. """
    from x84.bbs import echo

    if lb_pager is None:
       lb_pager = lb_init()
  
    lb_pager.goto(lb_pager.index) 
    echo(lb_pager.refresh())
    echo(lb_pager.border())
    return (lb_pager)


def show_banner():
    """ Display main menu banner """
    from x84.bbs import showart, echo, getterminal, getsession
    import os

    session, term = getsession(), getterminal()
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'main.ans')

    # displays a centered main menu header in topaz encoding for utf8
    for line in showart(artfile,'topaz',center=True):
        echo(line)


def main():
    """ Main procedure. """
    from x84.bbs import getterminal, getsession, getch, goto, gosub
    from x84.bbs import ini, echo
    from ConfigParser import Error as ConfigError
    import os
    import logging

    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    session.activity = u'Lightbar Main menu'

    echo(term.clear)
    show_banner()
    lb = lb_init()

    term_width = term.width
    term_height = term.height

    inp = -1
    dirty = True
    while True:
        if dirty or session.poll_event('refresh'):
            lb_refresh(lb)

        inp = getch(1)
        dirty = True

        # terminal dimensions may change, so we adapt to that
        if (term_width != term.width or term_height != term.height):
            echo(term.clear)
            show_banner()
            lb = lb_init()
            lb_refresh(lb)
            term_width = term.width
            term_height = term.height

        if inp is not None:
            echo(lb.process_keystroke(inp))

            if lb.selected and lb.selection[0] is not None: 
                if lb.selection[0] == u'x':
                    goto('main') 
                elif lb.selection[0] == u'$':
                    gosub('bulletins')
                elif lb.selection[0] == u'b':
                    gosub('bbslist')
                elif lb.selection[0] == u'l':
                    gosub('lc')
                elif lb.selection[0] == u'o':
                    gosub('ol')
                elif lb.selection[0] == u's':
                    gosub('si')
                elif lb.selection[0] == u'w':
                    echo(term.clear)
                    gosub('online')
                elif lb.selection[0] == u'n':
                    gosub('news')
                elif lb.selection[0] == u'f':
                    gosub('weather')
                elif lb.selection[0] == u'u':
                    gosub('userlist')
                elif lb.selection[0] == u'e':
                    echo(term.clear)
                    gosub('profile')
                elif lb.selection[0] == u'#':
                    gosub('lord')
                elif lb.selection[0] == u't':
                    echo(term.clear)
                    gosub('tetris')
                elif lb.selection[0] == u'c':
                    gosub('chat')
                elif lb.selection[0] == u'i':
                    gosub('ircchat')
                elif lb.selection[0] == u'p':
                    gosub('writemsg')
                elif lb.selection[0] == u'r':
                    gosub('readmsgs')
                elif lb.selection[0] == u'g':
                    gosub('logoff')
                elif lb.selection[0] == u'!':
                    gosub('charset')
                elif lb.selection[0] == u'v' and 'sysop' in session.user.groups:
                    gosub('ttyplay')
            
                echo(term.clear)
                show_banner()

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
