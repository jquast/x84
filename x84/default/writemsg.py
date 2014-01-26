"""
Write public or private posts for x/84, https://github.com/jquast/x84/
"""


def banner():
    """ Display banner/art ... nothing for now """
    from x84.bbs import echo, getterminal
    term = getterminal()
    echo(u'\r\n\r\n')
    echo(term.bold_black(u'art needed ../'.center(term.width).rstrip()))
    echo(u'\r\n\r\n')


def display_msg(msg):
    """ Display full message """
    from x84.bbs import getterminal, getsession, echo, Ansi
    session, term = getsession(), getterminal()
    body = msg.body.splitlines()
    echo(u'    AUthOR: ' + term.bold_yellow(msg.author) + u'\r\n\r\n')
    echo(u'   RECiPiENt: ')
    echo(term.yellow(msg.recipient
                     if msg.recipient is not None
                     else u'<(None)=All users>'))
    echo(u'\r\n\r\n')
    echo(u'     SUBjECt: ')
    echo(term.yellow(msg.subject))
    echo(u'\r\n\r\n')
    echo(u'        tAGS: ')
    echo(term.yellow(u', '.join(msg.tags)))
    echo(u'\r\n\r\n')
    echo(term.underline(u'        bOdY: '.ljust(term.width - 1)) + u'\r\n')
    echo(Ansi(u'\r\n'.join(body)).decode_pipe() + term.normal)
    echo(u'\r\n' + term.underline(u''.ljust(term.width - 1)))
    echo(u'\r\n\r\n')
    session.activity = 'Constructing a %s message' % (
        u'public' if u'public' in msg.tags else u'private',)
    return


def prompt_recipient(msg):
    """ Prompt for recipient of message. """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import getterminal, LineEditor, echo, ini, list_users
    from x84.bbs import Selector
    import difflib
    term = getterminal()
    echo(u"ENtER %s, OR '%s' tO AddRESS All. %s to exit" % (
        term.bold_yellow(u'hANdlE'),
        term.bold_yellow(u'None'),
        term.bold_yellow_underline('Escape'),))
    echo(u'\r\n\r\n')
    max_user = ini.CFG.getint('nua', 'max_user')
    lne = LineEditor(max_user, msg.recipient or u'None')
    lne.highlight = term.yellow_reverse
    echo(term.clear_eol + u'   RECiPiENt: ')
    recipient = lne.read()
    if recipient is None or lne.quit:
        return False
    userlist = list_users()
    if recipient in userlist:
        msg.recipient = recipient
        return True
    elif len(recipient) != 0 and recipient != 'None':
        for match in difflib.get_close_matches(recipient, userlist):
            blurb = u'did YOU MEAN: %s ?' % (match,)
            inp = Selector(yloc=term.height - 1,
                           xloc=term.width - 22,
                           width=20, left=u'YES', right=u'NO')
            echo(u''.join((
                u'\r\n',
                term.move(inp.yloc, inp.xloc - len(blurb)),
                term.clear_eol,
                term.bold_yellow(blurb))))
            selection = inp.read()
            echo(term.move(inp.yloc, 0) + term.clear_eol)
            if selection == u'YES':
                msg.recipient = match
                return True
            if selection is None or inp.quit:
                return False
    else:
        blurb = u' NO RECiPiENT; POSt tO PUbliC? '
        inp = Selector(yloc=term.height - 1,
                       xloc=term.width - 22,
                       width=20, left=u'YES', right=u'NO')
        echo(u''.join((
            u'\r\n',
            term.move(inp.yloc, inp.xloc - len(blurb)),
            term.clear_eol,
            term.bold_yellow(blurb))))
        selection = inp.read()
        echo(term.move(inp.yloc, 0) + term.clear_eol)
        if selection == u'YES':
            msg.recipient = None
            return True


def prompt_subject(msg):
    """ Prompt for subject of message. """
    from x84.bbs import getterminal, LineEditor, echo, ini
    term = getterminal()
    max_subject = int(ini.CFG.getint('msg', 'max_subject'))
    lne = LineEditor(max_subject, msg.subject)
    lne.highlight = term.yellow_reverse
    echo(u'\r\n\r\n     SUBjECt: ')
    subject = lne.read()
    if subject is None or 0 == len(subject):
        return False
    msg.subject = subject
    return True


def prompt_tags(msg):
    """ Prompt for and return tags wished for message. """
    # pylint: disable=R0914,W0603
    #         Too many local variables
    #         Using the global statement
    from x84.bbs import DBProxy, echo, getterminal, getsession
    from x84.bbs import Ansi, LineEditor, ini
    session, term = getsession(), getterminal()
    tagdb = DBProxy('tags')
    # version 1.0.9 introduced new ini option; set defaults for
    # those missing it from 1.0.8 upgrades.
    import ConfigParser
    try:
        moderated_tags = ini.CFG.getboolean('msg', 'moderated_tags')
    except ConfigParser.NoOptionError:
        moderated_tags = False
    try:
        moderated_groups = set(ini.CFG.get('msg', 'tag_moderator_groups'
                                           ).split())
    except ConfigParser.NoOptionError:
        moderated_groups = ('sysop', 'moderator',)
    msg_onlymods = (u"\r\nONlY MEMbERS Of GROUPS %s MAY CREAtE NEW tAGS." % (
        ", ".join(["'%s'".format(term.bold_yellow(grp)
                                 for grp in moderated_groups)])))
    msg_invalidtag = u"\r\n'%s' is not a valid tag."
    prompt_tags1 = u"ENtER %s, COMMA-dEliMitEd. " % (term.bold_red('TAG(s)'),)
    prompt_tags2 = u"OR '/list', %s:quit\r\n : " % (
        term.bold_yellow_underline('Escape'),)
    while True:
        # Accept user input for multiple 'tag's, or /list command
        echo(u'\r\n\r\n')
        echo(prompt_tags1)
        echo(prompt_tags2)
        width = term.width - 6
        sel_tags = u', '.join(msg.tags)
        inp_tags = LineEditor(width, sel_tags).read()
        if inp_tags is not None and 0 == len(inp_tags.strip()):
            # no tags must be (private ..)
            msg.tags = set()
            return True
        if inp_tags is None or inp_tags.strip().lower() == '/quit':
            return False
        elif inp_tags.strip().lower() == '/list':
            # list all available tags, and number of messages
            echo(u'\r\n\r\nTags: \r\n')
            all_tags = sorted(tagdb.items())
            if 0 == len(all_tags):
                echo(u'None !'.center(term.width / 2))
            else:
                echo(Ansi(u', '.join(([u'%s(%d)' % (_key, len(_value),)
                                       for (_key, _value) in all_tags]))
                          ).wrap(term.width - 2))
            continue
        echo(u'\r\n')

        # search input as valid tag(s)
        tags = set([inp.strip().lower() for inp in inp_tags.split(',')])

        # if the tag is new, and the user's group is not in
        # tag_moderator_groups, then dissallow such tag if
        # 'moderated_tags = yes' in ini cfg
        if moderated_tags:
            err = False
            for tag in tags.copy():
                if not tag in tagdb and not (
                        session.users.groups & moderated_groups):
                    tags.remove(tag)
                    echo(msg_invalidtag % (term.bold_red(tag),))
                    err = True
            if err:
                echo(msg_onlymods)
                continue
        msg.tags = tags
        return True


def prompt_public(msg):
    """ Prompt for/enforce 'public' tag of message for unaddressed messages.
    """
    from x84.bbs import getterminal, echo, Selector
    term = getterminal()

    if 'public' in msg.tags:
        # msg is addressed to None, and is tagged as 'public',
        return True # quit/escape

    if msg.recipient is None:
        # msg is addressed to nobody, force tag as 'public' or cancel,
        blurb = u"POStS AddRESSEd tO 'None' MUSt bE PUbliC!"
        inp = Selector(yloc=term.height - 1,
                       xloc=term.width - 22,
                       width=20,
                       left=u'Ok', right=u'CANCEl')
        echo(term.move(inp.yloc, inp.xloc - len(blurb)) + term.clear_eol)
        echo(term.bold_red(blurb))
        selection = inp.read()
        echo(term.move(inp.yloc, 0) + term.clear_eol)
        if selection == u'Ok':
            msg.tags.add(u'public')
            return True
        return False # quit/escape

    # not specified; you don't want this msg public? confirm,
    inp = Selector(yloc=term.height - 1,
                   xloc=term.width - 24,
                   width=20,
                   left=u'YES!', right=u'NO')
    blurb = u'SENd PRiVAtE POSt?'
    echo(term.move(inp.yloc, inp.xloc - len(blurb)))
    echo(term.bold_yellow(blurb))
    selection = inp.read()
    echo(term.move(inp.yloc, 0) + term.clear_eol)
    if selection == u'NO':
        msg.tags.add(u'public')
        return True
    elif selection == u'YES!':
        if u'public' in msg.tags:
            msg.tags.remove(u'public')
        return True
    return False # quit/escape


def prompt_body(msg):
    """ Prompt for 'body' of message, executing 'editor' script. """
    from x84.bbs import echo, Selector, getterminal, getsession, gosub
    term = getterminal()
    session = getsession()
    inp = Selector(yloc=term.height - 1,
                   xloc=term.width - 22,
                   width=20,
                   left=u'CONtiNUE', right=u'CANCEl')
    blurb = u'CONtiNUE tO Edit MESSAGE bOdY'
    echo(u'\r\n\r\n')
    echo(term.move(inp.yloc, inp.xloc - len(blurb)))
    echo(term.bold_yellow(blurb))
    selection = inp.read()
    echo(term.move(inp.yloc, 0) + term.clear_eol)
    if selection != u'CONtiNUE':
        return False
    if 0 != len(session.user.get('draft', u'')):
        inp = Selector(yloc=term.height - 1,
                       xloc=term.width - 22,
                       width=20,
                       left=u'REStORE', right=u'ERASE')
        blurb = u'CONtiNUE PREViOUSlY SAVEd dRAft ?'
        echo(u'\r\n\r\n')
        echo(term.move(inp.yloc, inp.xloc - len(blurb)))
        echo(term.bold_yellow(blurb))
        selection = inp.read()
        echo(term.move(inp.yloc, 0) + term.clear_eol)
        if selection == u'REStORE':
            msg.body = session.user['draft']
    echo(u'\r\n\r\n')
    session.user['draft'] = msg.body
    if gosub('editor', 'draft'):
        echo(u'\r\n\r\n' + term.normal)
        msg.body = session.user.get('draft', u'')
        del session.user['draft']
        return 0 != len(msg.body.strip())
    return False


def prompt_send():
    """ Prompt for continue/cancel """
    from x84.bbs import echo, Selector, getterminal
    term = getterminal()
    inp = Selector(yloc=term.height - 1,
                   xloc=term.width - 22,
                   width=20,
                   left=u'CONtiNUE', right=u'CANCEl')
    blurb = u'CONtiNUE tO SENd MESSAGE'
    echo(term.move(inp.yloc, inp.xloc - len(blurb)))
    echo(term.bold_yellow(blurb))
    selection = inp.read()
    echo(term.move(inp.yloc, 0) + term.clear_eol)
    if selection != u'CONtiNUE':
        return False
    return True


def prompt_abort():
    """ Prompt for continue/abort """
    from x84.bbs import echo, Selector, getterminal
    term = getterminal()
    inp = Selector(yloc=term.height - 1,
                   xloc=term.width - 22,
                   width=20,
                   left=u'CONtiNUE', right=u'AbORt')
    blurb = u'CONtiNUE MESSAGE?'
    echo(u'\r\n\r\n')
    echo(term.move(inp.yloc, inp.xloc - len(blurb)))
    echo(term.bold_yellow(blurb))
    selection = inp.read()
    echo(term.move(inp.yloc, 0) + term.clear_eol)
    if selection == u'AbORt':
        return True
    return False


def main(msg=None):
    """ Main procedure. """
    from x84.bbs import Msg, getsession
    session = getsession()
    if msg is None:
        msg = Msg()
        msg.tags = ('public',)
    banner()
    while True:
        session.activity = 'Constructing a %s message' % (
            u'public' if u'public' in msg.tags else u'private',)
        if not prompt_recipient(msg):
            break
        if not prompt_subject(msg):
            break
        if not prompt_tags(msg):
            break
        if not prompt_public(msg):
            break
        if not prompt_body(msg):
            break
        display_msg(msg)
        if not prompt_send():
            break
        msg.save()
        return True
    return False
