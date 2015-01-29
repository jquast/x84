""" Command-line parser for x/84. """
import getopt
import sys
import os


def parse_args():
    """ Parse system arguments and return lookup path for bbs and log ini. """
    if sys.platform.lower().startswith('win32'):
        system_path = os.path.join('C:', 'x84')
    else:
        system_path = os.path.join(os.path.sep, 'etc', 'x84')

    lookup_bbs = (os.path.join(system_path, 'default.ini'),
                  os.path.expanduser(os.path.join('~', '.x84', 'default.ini')))

    lookup_log = (os.path.join(system_path, 'logging.ini'),
                  os.path.expanduser(os.path.join('~', '.x84', 'logging.ini')))

    try:
        opts, tail = getopt.getopt(sys.argv[1:], u'', (
            'config=', 'logger=', 'help'))
    except getopt.GetoptError as err:
        sys.stderr.write('{0}\n'.format(err))
        return 1
    for opt, arg in opts:
        if opt in ('--config',):
            lookup_bbs = (arg,)
        elif opt in ('--logger',):
            lookup_log = (arg,)
        elif opt in ('--help',):
            sys.stderr.write(
                'Usage: \n'
                '{0} [--config <filepath>] [--logger <filepath>]\n'
                .format(os.path.basename(sys.argv[0])))
            sys.exit(1)
    if len(tail):
        sys.stderr.write('Unrecognized program arguments: {0}\n'
                         .format(tail))
        sys.exit(1)
    return (lookup_bbs, lookup_log)



