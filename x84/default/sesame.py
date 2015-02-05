""" DOS/Door wrapper for x/84. """
# std imports
import contextlib
import shlex
import os

# local
from x84.bbs import getsession, getterminal, echo, ini, Pager, Dropfile
from x84.bbs import Door, DOSDoor, get_ini, syncterm_setfont


def prompt_resize_term(session, term, name):
    want_cols = get_ini('sesame', '{0}_cols'.format(name), getter='getint')
    want_rows = get_ini('sesame', '{0}_rows'.format(name), getter='getint')

    if want_cols and want_rows and not term.kind.startswith('ansi'):
        while not (term.width == want_cols and
                   term.height == want_rows):
            resize_msg = (u'Please resize your window to {0} x {1} '
                          u'current size is {term.width} x {term.height} '
                          u'or press return.  Press escape to cancel.'
                          .format(want_cols, want_rows, term=term))
            echo(term.normal + term.home + term.clear_eos + term.home)
            pager = Pager(yloc=0, xloc=0, width=want_cols, height=want_rows,
                          colors={'border': term.bold_red})
            echo(term.move(term.height - 1, term.width))

            echo(pager.refresh() + pager.border())

            width = min(70, term.width - 5)
            for yoff, line in enumerate(term.wrap(resize_msg, width)):
                echo(u''.join((term.move(yoff + 1, 5), line.rstrip())))

            event, data = session.read_events(('input', 'refresh'))
            if event == 'refresh':
                continue

            if event == 'input':
                session.buffer_input(data, pushback=True)
                inp = term.inkey(0)
                while inp:
                    if inp.code == term.KEY_ENTER:
                        echo(term.normal + term.home + term.clear_eos)
                        return True
                    if inp.code == term.KEY_ESCAPE:
                        return False
                    inp = term.inkey(0)
        return True


def restore_screen(term, cols, rows):
    term._columns, term._rows = cols, rows


def parse_command_args(session, name, node):
    # Parse command path and arguments
    command = get_ini('sesame', name)
    if ' ' in command:
        command, args = command.split(' ', 1)
        args = args.format(
            session=session.to_dict(),
            system=dict(ini.CFG.items('system')),
            node=node,
        )
        args = shlex.split(args)
    else:
        args = []

    if not os.path.exists(command):
        raise RuntimeError("The door {0} specified a command path of "
                           "{1!r}, but no such file exists."
                           .format(name, command))

    return command, args


@contextlib.contextmanager
def acquire_node(session, name):
    nodes = get_ini('sesame', '{0}_nodes'.format(name), getter='getint')
    if not nodes:
        yield None
        return

    for node in range(1, nodes + 1):
        event = 'lock-{name}/{node}'.format(name=name, node=node)
        session.send_event(event, ('acquire', None))
        if session.read_event(event):
            yield node
            session.send_event(event, ('release', None))
            return

    # node could not be acquired
    yield -1


def get_env(session, name):
    # Setup the OS Environment values (if any)
    env = dict()
    env_prefix = '{0}_env_'.format(name)
    for option in ini.CFG.options('sesame'):
        if option.startswith(env_prefix):
            key = option.replace(env_prefix, '').upper()
            env[key] = ini.CFG.get('sesame', option).format(
                session=session.to_dict(),
                system=dict(ini.CFG.items('system')),
            )
    return env


def do_dropfile(name, node):
    dropfile_path = get_ini('sesame', '{0}_droppath'.format(name))
    dropfile_type = get_ini('sesame', '{0}_droptype'.format(name)
                            ) or 'doorsys'
    if not dropfile_path:
        return

    dropfile_type = dropfile_type.upper()

    if not hasattr(Dropfile, dropfile_type):
        raise ValueError('sesame configuration declares dropfile '
                         'format of {0!r} but value is not supported '
                         'by class Dropfile.'.format(dropfile_type))

    _dropfile_type = getattr(Dropfile, dropfile_type)
    Dropfile(_dropfile_type, node).save(dropfile_path)


def main(name):
    """ Sesame runs a named door. """
    session, term = getsession(), getterminal()

    # clear screen,
    echo(term.normal + u'\r\n' * term.height + term.move(0, 0))

    # set font,
    if term.kind.startswith('ansi'):
        syncterm_font = get_ini(
            'sesame', '{0}_syncterm_font'.format(name)) or 'cp437'
        echo(syncterm_setfont(syncterm_font))
        echo(term.move_x(0) + term.clear_eol)

    # pylint: disable=W0212
    #         Access to a protected member {_columns, _rows} of a client class
    store_columns, store_rows = term._columns, term._rows
    if not prompt_resize_term(session, term, name):
        return

    with acquire_node(session, name) as node:

        if node == -1:
            echo(term.bold_red('This door has reached the maximum number '
                               'of nodes and may not be played.\r\n\r\n'
                               'press any key.'))
            term.inkey()
            restore_screen(term, store_columns, store_rows)
            return

        do_dropfile(name, node)

        session.activity = u'Playing {}'.format(name)

        cmd, args = parse_command_args(session, name, node)
        env = get_env(session, name)
        cp437 = get_ini('sesame', '{0}_cp437'.format(name),
                        getter='getboolean')

        _Door = DOSDoor if cmd.endswith('dosemu') else Door
        _Door(cmd=cmd, args=args, env=env, cp437=cp437).run()

    restore_screen(term, store_columns, store_rows)
