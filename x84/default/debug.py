""" Debug example script for x/84, https://github.com/jquast/x84 """


def main():
    """ Main procedure. """
    # by default, nothing is done.
    from x84.bbs import getsession
    assert 'sysop' in getsession().user.groups

    #return migrate_105lc()
    return nothing()

    # but this is a great way to make data manipulations,
    # exampled here is importing of a .csv import of
    # a mystic recordbase.
    #return merge_mystic()

    #return tygerofdantye_fix()


def migrate_105lc():
    from x84.bbs import echo, DBProxy, list_users, get_user
    # migrating lastcallers database for 1.0.5 upgrade
    lc = DBProxy('lastcalls')
    for handle in list_users():
        user = get_user(handle)
        lc[(handle)] = (user.lastcall, user.calls, user.location)
        echo('\r\n' + user.handle + '.')
    echo ('\r\n\r\nlast callers db rebuilt!')


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
    echo('\r\n\r\n%d lines processed.' % (lno,))
    getch()
