def main():
    # by default, nothing is done.
    from x84.bbs import getsession
    assert 'sysop' in getsession().user.groups

    return nothing()

    # but this is a great way to make data manipulations,
    # exampled here is importing of an old sqlite3 userbase record,
    # as well as a .csv export of a mystic recordbase.
    #return merge_mystic()

def nothing():
    from x84.bbs import echo, getch
    echo(u'Nothing to do.')
    getch(3)

def merge_mystic():
    from x84.bbs import ini, echo, getch, User
    import os
    WRITE = False
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
        user = User(handle)
        user.location = _location
        user.email = _email
        user.password = _password
        user.groups.add('old-school')
        if WRITE:
            user.save()
    echo('\r\n\r\n%d lines processed.' % (lno,))
    getch()
