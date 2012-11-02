"""
 Configuration for x/84 BBS, https://github.com/jquast/x84/
"""

import logging.config
import os.path

CFG = None

def init(lookup_bbs, lookup_log):
    """
    Initialize global 'CFG' variable, a singleton to contain bbs properties and
    settings across all modules, as well as the logger. Each variable is tuple
    lookup path of in-order preferences for .ini files.

    If none our found, defaults are initialized, and the last item of each
    tuple is created.
    """
    #pylint: disable=R0912
    #        Too many branches (14/12)
    import ConfigParser
    root = logging.getLogger()
    def write_cfg(cfg, filepath):
        """
        Write Config to filepath.
        """
        if not os.path.exists(os.path.dirname(filepath)):
            print ('Creating folder %s\n' % (os.path.dirname(filepath),))
            os.mkdir (os.path.dirname(filepath))
        print ('Saving %s\n' % (filepath,))
        cfg.write (open(filepath, 'wb'))

    # we exploit our last argument as, what we presume to be within a folder
    # writable by our process -- engine.py specifys as ~/.x84/somefile.ini
    loaded = False
    cfg_logfile = lookup_log[-1]
    for cfg_logfile in lookup_log:
        # load-only defaults,
        if os.path.exists(cfg_logfile):
            print ('loading %s' % (cfg_logfile,))
            logging.config.fileConfig (cfg_logfile)
            loaded = True
            break
    if not loaded:
        cfg_log = init_log_ini()
        if not os.path.isdir(os.path.dirname(cfg_logfile)):
            try:
                os.mkdir (os.path.dirname(cfg_logfile))
            except OSError, err:
                root.warn ('%s', err)
        try:
            write_cfg (cfg_log, cfg_logfile)
            root.info ('Saved %s' % (cfg_logfile,))
        except IOError, err:
            root.error ('%s', err)
        logging.config.fileConfig (cfg_logfile)

    loaded = False
    cfg_bbs = ConfigParser.SafeConfigParser()
    cfg_bbsfile = lookup_bbs[-1]
    for cfg_bbsfile in lookup_bbs:
        # load defaults,
        if os.path.exists(cfg_bbsfile):
            cfg_bbs.read (cfg_bbsfile)
            root.info ('loaded %s', cfg_bbsfile)
            loaded = True
            break
    if not loaded:
        cfg_bbs = init_bbs_ini()
        if not os.path.isdir(os.path.dirname(cfg_bbsfile)):
            try:
                os.mkdir (os.path.dirname(cfg_bbsfile))
            except OSError, err:
                root.warn ('%s', err)
        try:
            write_cfg (cfg_bbs, cfg_bbsfile)
            root.info ('Saved %s' % (cfg_bbsfile,))
        except IOError, err:
            root.error ('%s', err)

    #pylint: disable=W0603
    #        Using the global statement
    global CFG
    CFG = cfg_bbs


def init_bbs_ini ():
    """
    Returns ConfigParser instance of bbs system defaults
    """
    import ConfigParser
    cfg_bbs = ConfigParser.SafeConfigParser()

    cfg_bbs.add_section('system')
    cfg_bbs.set('system', 'bbsname', 'x/84')
    cfg_bbs.set('system', 'sysop', '')
    cfg_bbs.set('system', 'software', 'x/84')
    # use module-level 'default' folder
    cfg_bbs.set('system', 'scriptpath',
            os.path.abspath(os.path.join( os.path.dirname(__file__),
                os.path.pardir, 'default')))
    cfg_bbs.set('system', 'datapath',
            os.path.join(os.path.expanduser('~/.x84'), 'data'))
    cfg_bbs.set('system', 'ttyrecpath',
        os.path.join(os.path.expanduser('~/.x84'), 'ttyrecordings'))
    cfg_bbs.set('system', 'timeout', '1984')
    cfg_bbs.set('system', 'password_digest', 'internal')

    cfg_bbs.add_section('telnet')
    cfg_bbs.set('telnet', 'addr', '127.0.0.1')
    cfg_bbs.set('telnet', 'port', '6023')

    cfg_bbs.add_section('door')
    cfg_bbs.set('door', 'path', '/usr/local/bin:/usr/games')

    cfg_bbs.add_section ('matrix')
    cfg_bbs.set('matrix', 'newcmds', 'new apply')
    cfg_bbs.set('matrix', 'byecmds', 'exit logoff bye quit')
    cfg_bbs.set('matrix', 'script', 'matrix')
    cfg_bbs.set('matrix', 'topscript', 'top')
    cfg_bbs.set('matrix', 'enable_anonymous', 'no')

    cfg_bbs.add_section('session')
    cfg_bbs.set('session', 'record_tty', 'yes')
    cfg_bbs.set('session', 'tap_input', 'no')
    cfg_bbs.set('session', 'tap_output', 'no')
    cfg_bbs.set('session', 'default_encoding', 'utf8')

    cfg_bbs.add_section('irc')
    cfg_bbs.set('irc', 'server', 'efnet.xs4all.nl')
    cfg_bbs.set('irc', 'port', '6667')
    cfg_bbs.set('irc', 'channel', '#prsv')

    cfg_bbs.add_section('nua')
    cfg_bbs.set('nua', 'script', 'nua')
    cfg_bbs.set('nua', 'min_user', '3')
    cfg_bbs.set('nua', 'min_pass', '4')
    cfg_bbs.set('nua', 'max_user', '11')
    cfg_bbs.set('nua', 'max_pass', '16')
    cfg_bbs.set('nua', 'max_email', '50')
    cfg_bbs.set('nua', 'max_location', '24')
    cfg_bbs.set('nua', 'allow_apply', 'yes')
    cfg_bbs.set('nua', 'invalid_handles', ' '.join \
        ((cfg_bbs.get('matrix','byecmds'),
          cfg_bbs.get('matrix','newcmds'),
          'sysop anonymous',)))
    return cfg_bbs

def init_log_ini ():
    """
    Returns ConfigParser instance of logger defaults
    """
    import ConfigParser
    cfg_log = ConfigParser.SafeConfigParser()
    cfg_log.add_section('formatters')
    cfg_log.set('formatters', 'keys', 'default')

    cfg_log.add_section('formatter_default')
    cfg_log.set('formatter_default', 'format',
            '%(levelname)s %(filename)s:%(lineno)s '
            '%(processName)s - %(message)s')
    cfg_log.set('formatter_default', 'class', 'logging.Formatter')

    cfg_log.add_section('handlers')
    cfg_log.set('handlers', 'keys', 'console, info_file')

    cfg_log.add_section('handler_console')
    cfg_log.set('handler_console', 'class',
            'x84.bbs.log.ColoredConsoleHandler')
    cfg_log.set('handler_console', 'formatter', 'default')
    cfg_log.set('handler_console', 'args', 'tuple()')

    cfg_log.add_section('handler_info_file')
    cfg_log.set('handler_info_file', 'class', 'logging.FileHandler')
    cfg_log.set('handler_info_file', 'level', 'INFO')
    cfg_log.set('handler_info_file', 'formatter', 'default')
    cfg_log.set('handler_info_file', 'args', '("%s", "w")' %
            (os.path.join(os.path.expanduser('~/.x84'), 'info.log'),))

    cfg_log.add_section('handler_debug_file')
    cfg_log.set('handler_debug_file', 'class', 'logging.FileHandler')
    cfg_log.set('handler_debug_file', 'level', 'debug')
    cfg_log.set('handler_debug_file', 'formatter', 'default')
    cfg_log.set('handler_debug_file', 'args', '("%s", "w")' %
            (os.path.join(os.path.expanduser('~/.x84'), 'debug.log'),))

    cfg_log.add_section('loggers')
    cfg_log.set('loggers', 'keys', 'root, sqlitedict')

    cfg_log.add_section('logger_root')
    cfg_log.set('logger_root', 'level', 'INFO')
    cfg_log.set('logger_root', 'formatter', 'default')
    cfg_log.set('logger_root', 'handlers', 'console,info_file')

    # squelche sqlitedict's info on open, its rather long
    cfg_log.add_section('logger_sqlitedict')
    cfg_log.set('logger_sqlitedict', 'level', 'WARN')
    cfg_log.set('logger_sqlitedict', 'formatter', 'default')
    cfg_log.set('logger_sqlitedict', 'handlers', 'console, info_file')
    cfg_log.set('logger_sqlitedict', 'qualname', 'sqlitedict')
    cfg_log.set('logger_sqlitedict', 'propagate', '0')
    return cfg_log
