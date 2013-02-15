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
    # pylint: disable=R0912
    #        Too many branches (14/12)
    import ConfigParser
    root = logging.getLogger()

    def write_cfg(cfg, filepath):
        """
        Write Config to filepath.
        """
        if not os.path.exists(os.path.dirname(filepath)):
            print('Creating folder %s\n' % (os.path.dirname(filepath),))
            os.mkdir(os.path.dirname(filepath))
        print('Saving %s\n' % (filepath,))
        cfg.write(open(filepath, 'wb'))

    # exploit last argument, presumed to be within a folder
    # writable by our process, and where the ini is wanted
    # -- engine.py specifys a default of: ~/.x84/somefile.ini
    loaded = False
    cfg_logfile = lookup_log[-1]
    for cfg_logfile in lookup_log:
        # load-only defaults,
        if os.path.exists(cfg_logfile):
            print ('loading %s' % (cfg_logfile,))
            logging.config.fileConfig(cfg_logfile)
            loaded = True
            break
    if not loaded:
        cfg_log = init_log_ini()
        if not os.path.isdir(os.path.dirname(cfg_logfile)):
            try:
                os.mkdir(os.path.dirname(cfg_logfile))
            except OSError, err:
                root.warn('%s', err)
        try:
            write_cfg(cfg_log, cfg_logfile)
            root.info('Saved %s' % (cfg_logfile,))
        except IOError, err:
            root.error('%s', err)
        logging.config.fileConfig(cfg_logfile)

    loaded = False
    cfg_bbs = ConfigParser.SafeConfigParser()
    cfg_bbsfile = lookup_bbs[-1]
    for cfg_bbsfile in lookup_bbs:
        # load defaults,
        if os.path.exists(cfg_bbsfile):
            cfg_bbs.read(cfg_bbsfile)
            root.info('loaded %s', cfg_bbsfile)
            loaded = True
            break
    if not loaded:
        cfg_bbs = init_bbs_ini()
        if not os.path.isdir(os.path.dirname(cfg_bbsfile)):
            try:
                os.mkdir(os.path.dirname(cfg_bbsfile))
            except OSError, err:
                root.warn('%s', err)
        try:
            write_cfg(cfg_bbs, cfg_bbsfile)
            root.info('Saved %s' % (cfg_bbsfile,))
        except IOError, err:
            root.error('%s', err)

    # pylint: disable=W0603
    #        Using the global statement
    global CFG
    CFG = cfg_bbs


def init_bbs_ini():
    """
    Returns ConfigParser instance of bbs system defaults
    """
    import ConfigParser
    # used to construct default e-mail
    # pylint: disable=R0915
    #         Too many statements (51/50)
    import getpass
    import socket
    cfg_bbs = ConfigParser.SafeConfigParser()

    cfg_bbs.add_section('system')
    cfg_bbs.set('system', 'bbsname', 'x/84')
    cfg_bbs.set('system', 'sysop', '')
    cfg_bbs.set('system', 'software', 'x/84')
    # use module-level 'default' folder
    cfg_bbs.set('system', 'scriptpath', os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, 'default')))
    cfg_bbs.set('system', 'datapath',
                os.path.join(os.path.expanduser('~/.x84'), 'data'))
    cfg_bbs.set('system', 'ttyrecpath',
                os.path.join(os.path.expanduser('~/.x84'), 'ttyrecordings'))
    cfg_bbs.set('system', 'timeout', '1984')
    cfg_bbs.set('system', 'password_digest', 'internal')
    cfg_bbs.set('system', 'mail_addr',
                '%s@%s' % (getpass.getuser(), socket.gethostname()))
    cfg_bbs.set('system', 'mail_smtphost', 'localhost')
    # change 'ansi' termcaps to 'ansi-bbs', for SynchoTerm
    cfg_bbs.set('system', 'termcap-ansi', 'ansi-bbs')
    # could be information leak to sensitive sysops
    cfg_bbs.set('system', 'show_traceback', 'no')
    # store passwords in uppercase, facebook and mystic bbs does this ..
    cfg_bbs.set('system', 'pass_ucase', 'no')

    cfg_bbs.add_section('telnet')
    cfg_bbs.set('telnet', 'addr', '127.0.0.1')
    cfg_bbs.set('telnet', 'port', '6023')

    # default path if cmd argument is not absolute,
    cfg_bbs.add_section('door')
    cfg_bbs.set('door', 'path', '/usr/local/bin:/usr/games')

    cfg_bbs.add_section('matrix')
    cfg_bbs.set('matrix', 'newcmds', 'new apply')
    cfg_bbs.set('matrix', 'byecmds', 'exit logoff bye quit')
    cfg_bbs.set('matrix', 'script', 'matrix')
    cfg_bbs.set('matrix', 'topscript', 'top')
    cfg_bbs.set('matrix', 'enable_anonymous', 'no')
    cfg_bbs.set('matrix', 'enable_pwreset', 'yes')

    cfg_bbs.add_section('session')
    cfg_bbs.set('session', 'record_tty', 'yes')
    cfg_bbs.set('session', 'tap_input', 'no')
    cfg_bbs.set('session', 'tap_output', 'no')
    cfg_bbs.set('session', 'default_encoding', 'utf8')

    cfg_bbs.add_section('irc')
    cfg_bbs.set('irc', 'server', 'efnet.xs4all.nl')
    cfg_bbs.set('irc', 'port', '6667')
    cfg_bbs.set('irc', 'channel', '#prsv')

    cfg_bbs.add_section('nethack')
    cfg_bbs.set('nethack', 'enabled', 'yes')
    cfg_bbs.set('nethack', 'path', '/nh343/nethack.343-nao')
    cfg_bbs.set('nethack', 'logfile', '/nh343/var/xlogfile')

    cfg_bbs.add_section('nua')
    cfg_bbs.set('nua', 'script', 'nua')
    cfg_bbs.set('nua', 'min_user', '3')
    cfg_bbs.set('nua', 'min_pass', '4')
    cfg_bbs.set('nua', 'max_user', '11')
    cfg_bbs.set('nua', 'max_pass', '16')
    cfg_bbs.set('nua', 'max_email', '50')
    cfg_bbs.set('nua', 'max_location', '24')
    cfg_bbs.set('nua', 'allow_apply', 'yes')
    cfg_bbs.set('nua', 'invalid_handles', ' '.join(
        (cfg_bbs.get('matrix', 'byecmds'),
         cfg_bbs.get('matrix', 'newcmds'),
         'sysop anonymous',)))
    cfg_bbs.set('nua', 'handle_validation', '^[A-Za-z0-9]{3,11}$')

    cfg_bbs.add_section('msg')
    cfg_bbs.set('msg', 'max_subject', '40')
    return cfg_bbs


def init_log_ini():
    """
    Returns ConfigParser instance of logger defaults
    """
    import ConfigParser
    cfg_log = ConfigParser.RawConfigParser()
    cfg_log.add_section('formatters')
    cfg_log.set('formatters', 'keys', 'default')

    cfg_log.add_section('formatter_default')
    # for multiprocessing/threads, use: %(processName)s %(threadName) !
    cfg_log.set('formatter_default', 'format',
                u'%(asctime)s %(levelname)s '
                u'%(filename)11s:%(lineno)-3s %(message)s')
    cfg_log.set('formatter_default', 'class', 'logging.Formatter')
    cfg_log.set('formatter_default', 'datefmt', '%a-%m-%d %I:%M%p')

    cfg_log.add_section('handlers')
    cfg_log.set('handlers', 'keys', 'console, rotate_daily')

    cfg_log.add_section('handler_console')
    cfg_log.set('handler_console', 'class',
                'x84.bbs.log.ColoredConsoleHandler')
    cfg_log.set('handler_console', 'formatter', 'default')
    cfg_log.set('handler_console', 'args', 'tuple()')

    cfg_log.add_section('handler_rotate_daily')
    cfg_log.set('handler_rotate_daily', 'class',
                'logging.handlers.TimedRotatingFileHandler')
    cfg_log.set('handler_rotate_daily', 'level', 'INFO')
    cfg_log.set('handler_rotate_daily', 'suffix', '%Y%m%d')
    cfg_log.set('handler_rotate_daily', 'encoding', 'utf8')
    cfg_log.set('handler_rotate_daily', 'formatter', 'default')
    daily_log = os.path.join(os.path.expanduser('~/.x84'), 'daily.log')
    cfg_log.set('handler_rotate_daily', 'args',
                '("' + daily_log + '", "midnight", 1, 60)')

    cfg_log.add_section('loggers')
    cfg_log.set('loggers', 'keys', 'root, sqlitedict')

    cfg_log.add_section('logger_root')
    cfg_log.set('logger_root', 'level', 'INFO')
    cfg_log.set('logger_root', 'formatter', 'default')
    cfg_log.set('logger_root', 'handlers', 'console, rotate_daily')

    # squelche sqlitedict's info on open, its rather long
    cfg_log.add_section('logger_sqlitedict')
    cfg_log.set('logger_sqlitedict', 'level', 'WARN')
    cfg_log.set('logger_sqlitedict', 'formatter', 'default')
    cfg_log.set('logger_sqlitedict', 'handlers', 'console, rotate_daily')
    cfg_log.set('logger_sqlitedict', 'qualname', 'sqlitedict')
    cfg_log.set('logger_sqlitedict', 'propagate', '0')

    cfg_log.add_section('ttyplay')
    cfg_log.set('ttyplay', 'exe', '/usr/bin/ttyplay')
    return cfg_log
