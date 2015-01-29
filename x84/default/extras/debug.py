""" Debug example script for x/84 """


def main():
    """ Main procedure. """
    import os

    # by default, nothing is done.
    from x84.bbs import getsession
    assert 'sysop' in getsession().user.groups

    # return migrate_105lc()
    # return nothing()
    # return gosub('test_keyboard_keys')
    # return dump_x84net_debug()
    return test_xmodem(os.path.join(os.path.dirname(__file__), 'debug.py'))

    # but this is a great way to make data manipulations,
    # exampled here is importing of a .csv import of
    # a mystic recordbase.
    # return merge_mystic()

    # return tygerofdantye_fix()


def test_xmodem(filepath, protocol='xmodem1k'):
    import os
    from x84.bbs import echo, send_modem, recv_modem, getterminal
    term = getterminal()

    echo(u"\r\n\r\n")

    # test bbs sending to client
    stream = open(filepath, 'rb')
    echo(u"Sending {0} using protocol {1}. \r\n"
         u"Start your receiving program now. \r\n"
         u"Press ^X twice to cancel: "
         .format(filepath, protocol))
    status = send_modem(stream, protocol)
    if not status:
        echo(u"\r\nThat didn't go so well.. "
             u"status={0}; sorry!\r\n".format(status))
        term.inkey()
        return

    # test client sending to bbs
    echo(u"Now its your turn cowboy -- send me anything\r\n"
         u"using the {0} protocol. really, I don't care.\r\n"
         .format(protocol))
    stream = open(os.devnull, 'wb')
    if not recv_modem(stream, protocol):
        echo(u"That didn't go so well.. sorry!\r\n")
        term.inkey()
        return

    echo(u"fine shooting, soldier!\r\n")
    term.inkey()


def x84net_requeue():
    # a message failed to queue for delivery, but hellbeard
    # really wanted to see em, so re-queue.
    from x84.bbs import DBProxy, echo
    from pprint import pformat
    queuedb = DBProxy('x84netqueues')
    with queuedb:
        queuedb['264'] = 1
    echo('-')
    echo(pformat(queuedb.items()))
    echo('-')


def migrate_105lc():
    # migrating lastcallers database for 1.0.5 upgrade
    from x84.bbs import echo, DBProxy, list_users, get_user
    lc = DBProxy('lastcalls')
    for handle in list_users():
        user = get_user(handle)
        lc[(handle)] = (user.lastcall, user.calls, user.location)
        echo(u'\r\n' + user.handle + '.')
    echo('\r\n\r\nlast callers db rebuilt!')


def nothing():
    """ Do nothing. """
    from x84.bbs import echo, getch
    echo(u'Nothing to do.')
    getch(3)


def tygerofdantye_fix():
    """ This user was too long! """
    from x84.bbs import DBProxy
    user = DBProxy('userbase')['tygerofdanyte']
    user.delete()
    user.handle = u'tygerdanyte'
    user.save()


def merge_mystic():
    """ Example script to merge csv records into userbase. """
    # pylint: disable=R0914
    #         Too many local variables
    from x84.bbs import ini, echo, getch, User, get_user, find_user
    import os
    # you must modify variable ``do_write`` to commit changes,
    # csv format; 'user:pass:origin:email\n', in iso8859-1 encoding.
    do_write = False
    inp_file = os.path.join(
        ini.CFG.get('system', 'datapath'),
        'mystic_dat.csv')
    lno = 0
    for lno, line in enumerate(open(inp_file, 'r')):
        handle = line.split(':', 1)[0].strip().decode('iso8859-1')
        attrs = line.rstrip().split(':')[2:]
        (_password, _location, _email) = attrs
        (_password, _location, _email) = (
            _password.strip().decode('iso8859-1'),
            _location.strip().decode('iso8859-1'),
            _email.strip().decode('iso8859-1'))
        echo(u''.join((u'\r\n',
                       handle, u': ',
                       '%d ' % (len(_password)),
                       '%s ' % (_location),
                       '%s ' % (_email),)))
        match = find_user(handle)
        if match is None:
            user = User(handle)
            user.location = _location
            user.email = _email
            user.password = _password
        else:
            user = get_user(match)
        user.groups.add('old-school')
        if do_write:
            user.save()
    echo(u'\r\n\r\n%d lines processed.' % (lno,))
    getch()
