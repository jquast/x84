"""
Write public or private posts for x/84, https://github.com/jquast/x84/
"""


def refresh(msg, level=0):
    """ Refresh screen, level indicates up to which step """
    from x84.bbs import getterminal, echo
    term = getterminal()
    echo(u'\r\n\r\n')
    echo(term.bold_black(u'art needed ../'.center(term.width).rstrip()))
    echo(u'\r\n\r\n')
    echo(u'    AUthOR: ' + term.bold_blue(msg.author) + u'\r\n\r\n')
    if level > 0:
        echo(u'   RECiPiENt: ')
        echo(term.bold_blue(msg.recipient if msg.recipient is not None
                            else u'<(None)=All users>' + u'\r\n\r\n'))
    if level > 1:
        echo(u'     SUBjECt: ')
        echo(term.bold_blue(msg.subject) + u'\r\n\r\n')
    if level > 2:
        echo(u'        tAGS: ')
        echo(term.clear_eol + term.bold_blue(u', '.join(msg.tags))
             + u'\r\n\r\n')
    if level > 3:
        echo(u'     bOdY: ' + u'\r\n\r\n')
        echo(u'\r\n'.join(msg.body.splitlines()) + u'\r\n\r\n')
    return


def get_recipient(msg):
    """ Prompt for recipient of message. """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import getterminal, LineEditor, echo, ini, list_users
    from x84.bbs import Selector
    import difflib
    term = getterminal()
    echo(term.clear_eol + term.bold_black(
        u"ENtER hANdlE, OR 'None'. Escape to exit")
        + u'\r\n\r\n')
    max_user = ini.CFG.getint('nua', 'max_user')
    lne = LineEditor(max_user, msg.recipient or u'None')
    lne.highlight = term.blue_reverse
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


def get_subject(msg):
    """ Prompt for subject of message. """
    from x84.bbs import getterminal, LineEditor, echo, ini
    term = getterminal()
    max_subject = int(ini.CFG.getint('msg', 'max_subject'))
    lne = LineEditor(max_subject, msg.subject)
    lne.highlight = term.blue_reverse
    echo(term.clear_eol + u'     SUBjECt: ')
    subject = lne.read()
    if subject is None or 0 == len(subject):
        return False
    msg.subject = subject
    return True


def get_public(msg):
    """ Prompt for 'public' tag of message. """
    from x84.bbs import getterminal, echo, Selector
    term = getterminal()
    if msg.recipient is None:
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
        return False
    else:
        inp = Selector(yloc=term.height - 1,
                      xloc=term.width - 22,
                      width=20,
                      left=u'PUbliC', right=u'PRiVAtE')
        blurb = u'PUbliC OR PRiVAtE POSt?'
        echo(term.move(inp.yloc, inp.xloc - len(blurb)))
        echo(term.bold_yellow(blurb))
        selection = inp.read()
        echo(term.move(inp.yloc, 0) + term.clear_eol)
        if selection == u'PUbliC':
            msg.tags.add(u'public')
            return True
        elif selection == u'PRiVAtE':
            if u'public' in msg.tags:
                msg.tags.remove(u'public')
            return True
        return False


def get_body(msg):
    """ Prompt for 'body' of message, executing 'editor' script. """
    from x84.bbs import echo, Selector, getterminal, getsession, gosub
    term = getterminal()
    session = getsession()
    inp = Selector(yloc=term.height - 1,
                  xloc=term.width - 22,
                  width=20,
                  left=u'CONtiNUE', right=u'CANCEl')
    blurb = u'CONtiNUE tO Edit MESSAGE bOdY'
    echo(term.move(inp.yloc, inp.xloc - len(blurb)))
    echo(term.bold_yellow(blurb))
    selection = inp.read()
    echo(term.move(inp.yloc, 0) + term.clear_eol)
    if selection != u'CONtiNUE':
        return False
    if gosub('editor', 'draft'):
        msg.body = session.user.get('draft', u'')
        del session.user['draft']
        return True
    return False


def get_send():
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


def get_abort():
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
    from x84.bbs import getsession, Msg
    session = getsession()
    msg = Msg() if msg is None else msg

    while True:
        session.activity = 'Writing a msg'
        refresh(msg)
        if not get_recipient(msg):
            if get_abort():
                return False
            continue
        refresh(msg, 1)
        if not get_subject(msg):
            if get_abort():
                return False
            continue
        refresh(msg, 2)
        if not get_public(msg):
            if get_abort():
                return False
            continue
        refresh(msg, 3)
        if not get_body(msg):
            continue
        refresh(msg, 4)
        if not get_send():
            continue
        msg.save()
        return True
