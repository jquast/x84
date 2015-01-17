"""Sesame is a wrapper for the :class:`x84.bbs.door.Door` class.

It takes care of resizing the users' terminal to the correct dimensions or
otherwise emulate the correct terminal size.

Configuration in `default.ini` is as follows::

    [sesame]
    NameOfTheGame = /path/to/binary
    NameOfTheGame_key = $
    NameOfTheGame_cols = 80
    NameOfTheGame_rows = 25

The suffixes for the configuration keys are as follows:

 * `_key`, character that gives access to the door from the BBS menu.
 * `_cols`, the minimal number of terminal columns required by the door.
 * `_rows`, the minimal number of terminal rows required by the door.
 * `_env_*`, additional environment settings required by the door.

The value of the `_env_*` configuration settings are passed to a Python
string formatting function. The session is available as `session` and
the configuration items from the `system` configuration section are
exposed.
"""

import ConfigParser
import shlex
import os


def main(name):
    """Sesame runs a named door."""
    from x84.bbs import getsession, getterminal, echo, ini
    from x84.bbs import Door

    session, term = getsession(), getterminal()
    session_info = session.to_dict()
    system_info = dict(ini.CFG.items('system'))

    store_cols, store_rows = None, None
    try:
        want_cols = ini.CFG.getint('sesame', '{}_cols'.format(name))
        want_rows = ini.CFG.getint('sesame', '{}_rows'.format(name))
        if want_cols != term.width or want_rows != term.height:
            echo(u'\x1b[8;%d;%dt' % (want_rows, want_cols,))
        disp = 1
        while not (term.width == want_cols
                   and term.height == want_cols):
            if disp:
                echo(term.bold_blue('\r\n^\r\n'))
                echo(term.bold_blue('\r\n'.join([u'|'] * (want_rows - 3))))
                echo(u'\r\n')
                echo(term.bold_blue(u'|' + (u'=' * 78) + u'|\r\n'))
                echo(u'for best "screen output", please '
                     'resize window to %s x %s (or press return).' % (
                         want_cols, want_rows,))
                disp = 0
            ret = term.inkey(2)
            if ret in (term.KEY_ENTER, u'\r', u'\n'):
                break

        if term.width != want_cols or term.height != want_rows:
            echo(u'Your dimensions: %s by %s; emulating %s by %s !' % (
                term.width, term.height, want_cols, want_rows,))
            # hand-hack, its ok ... really
            store_cols, store_rows = term.width, term.height
            term._columns, term._rows = want_cols, want_rows
            term.inkey(1)

    except ConfigParser.NoOptionError:
        pass  # no size requirements, assume we're good...

    # Parse command path and arguments
    command = ini.CFG.get('sesame', name)
    if ' ' in command:
        command, args = command.split(' ', 1)
        args = args.format(
            session=session_info,
            **system_info
        )
        args = shlex.split(args)
    else:
        args = []

    assert command != 'no'
    assert os.path.exists(command)

    # Now setup the environment (if any exists)
    env = dict()
    env_prefix = '{0}_env_'.format(name)
    for option in ini.CFG.options('sesame'):
        if option.startswith(env_prefix):
            key = option.replace(env_prefix, '').upper()
            env[key] = ini.CFG.get('sesame', option).format(
                session=session_info,
                **system_info
            )

    session.activity = u'Playing {}'.format(name)
    door = Door(
        command,
        args=args,
        env_home=env.get('HOME'),
        env_path=env.get('PATH'),
        env=env
    )
    door.run()
    echo(term.clear)
    if not (store_cols is None and store_rows is None):
        echo(u'Restoring dimensions to %s by %s !' % (store_cols, store_rows))
        term._rows, term._columns = store_rows, store_cols
    echo(u'\r\n')
    term.inkey(0.5)
