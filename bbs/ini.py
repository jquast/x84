"""
 Configuration for x/84 BBS, https://github.com/jquast/x84/
"""

import logging.config
import os.path
import ConfigParser

cfg = None

def init(cfg_bbsfile='data/default.ini', cfg_logfile='data/logging.ini'):
    """
    Initialize global 'cfg' variable, a singleton to contain bbs properties and
    settings across all modules. After initializing default configurations, if
    the file 'cfg_bbsfile' exists, those settings are merged. Logfile settings
    are also loaded from 'cfg_filepath'.
    """
    global cfg
    root = logging.getLogger()
    def write_cfg(cfg, filepath):
        """
        write ConfigParser to filepath
        """
        root.info ('saving %s', filepath)
        fptr = open(filepath, 'wb')
        cfg.write (fptr)
        fptr.close ()

    # load-only defaults,
    save_err = False
    if not os.path.exists(cfg_logfile):
        cfg_log = init_log_ini()
        try:
            write_cfg (cfg_log, cfg_logfile)
        except IOError, err:
            root.error ('%s', err)
            save_err = True
    if not save_err:
        root.info ('loading %s', cfg_logfile)
        logging.config.fileConfig (cfg_logfile)

    # load defaults, overlay filepath
    cfg_bbs = init_bbs_ini ()
    if not os.path.exists(cfg_bbsfile):
        try:
            write_cfg (cfg_bbs, cfg_bbsfile)
        except IOError, err:
            root.error ('%s', err)
    else:
        root.info ('loading %s', cfg_bbsfile)
        cfg_bbs.read (cfg_bbsfile)
    cfg = cfg_bbs


def init_bbs_ini ():
    """
    Returns ConfigParser instance of bbs system defaults
    """
    cfg_bbs = ConfigParser.SafeConfigParser()

    cfg_bbs.add_section('system')
    cfg_bbs.set('system', 'bbsname', 'x/84')

    cfg_bbs.add_section('telnet')
    cfg_bbs.set('telnet', 'addr', '127.0.0.1')
    cfg_bbs.set('telnet', 'port', '6023')

    cfg_bbs.add_section ('matrix')
    cfg_bbs.set('matrix', 'newcmds', 'new apply')
    cfg_bbs.set('matrix', 'byecmds', 'exit logoff bye quit')
    cfg_bbs.set('matrix', 'script', 'matrix')
    cfg_bbs.set('matrix', 'topscript', 'top')
    cfg_bbs.set('matrix', 'enable_anonymous', 'no')

    cfg_bbs.add_section('database')
    cfg_bbs.set('database', 'sqlite_folder', './data/')

    cfg_bbs.add_section('session')
    cfg_bbs.set('session', 'ttylog_folder', './ttyrecordings/')
    cfg_bbs.set('session', 'record_tty', 'yes')
    cfg_bbs.set('session', 'scriptpath', os.path.join(os.path.dirname(__file__),
        os.path.pardir, 'default/'))
    cfg_bbs.set('session', 'tap_input', 'no')
    cfg_bbs.set('session', 'tap_output', 'no')
    cfg_bbs.set('session', 'default_encoding', 'utf8')
    cfg_bbs.set('session', 'default_ttype', 'linux')
    cfg_bbs.set('session', 'timeout', '1984')

    cfg_bbs.add_section('door')
    cfg_bbs.set('door', 'path', '/usr/local/bin:/usr/games')

    cfg_bbs.add_section('irc')
    cfg_bbs.set('irc', 'server', 'efnet.xs4all.nl')
    cfg_bbs.set('irc', 'port', '6667')
    cfg_bbs.set('irc', 'channel', '#prsv')

    cfg_bbs.add_section('nua')
    cfg_bbs.set('nua', 'script', 'nua')
    cfg_bbs.set('nua', 'min_user', '3')
    cfg_bbs.set('nua', 'max_user', '11')
    cfg_bbs.set('nua', 'max_pass', '16')
    cfg_bbs.set('nua', 'max_email', '30')
    cfg_bbs.set('nua', 'max_origin', '24')
    cfg_bbs.set('nua', 'allow_apply', 'yes')
    cfg_bbs.set('nua', 'invalid_handles', ' '.join \
        ((cfg_bbs.get('matrix','byecmds'),
          cfg_bbs.get('matrix','newcmds'),
          'sysop anonymous',)))
    return cfg_bbs

    #cfg_bbs.add_section('dopewars')
    #cfg_bbs.set('dopewars', 'scorefile', 'data/dopewars.scores')
    #cfg_bbs.set('dopewars', 'pidfile', 'data/dopewars.pid')
    #cfg_bbs.set('dopewars', 'logfile', 'data/dopewars.log')

    #cfg_bbs.add_section('ftp')
    #cfg_bbs.set('ftp', 'enabled', 'no')
    #cfg_bbs.set('ftp', 'addr', '127.0.0.1')
    #cfg_bbs.set('ftp', 'port', '6021')
    #cfg_bbs.set('ftp', 'basedir', 'ftpdata/')
    #cfg_bbs.set('ftp', 'enable_anonymous', 'no')
    #cfg_bbs.set('ftp', 'enable_masquerade', 'no')
    #cfg_bbs.set('ftp', 'enable_fxp', 'no')
    #cfg_bbs.set('ftp', 'timeout', '1984')
    #cfg_bbs.set('ftp', 'masq_addr', '64.150.165.47')
    #cfg_bbs.set('ftp', 'pasv_ports', '61984-65000')
    #cfg_bbs.set('ftp', 'read_limit', '0')
    #cfg_bbs.set('ftp', 'write_limit', '0')
    #cfg_bbs.set('ftp', 'conns_max', '30')
    #cfg_bbs.set('ftp', 'conns_per_ip', '3')

def init_log_ini ():
    """
    Returns ConfigParser instance of logger defaults
    """
    cfg_log = ConfigParser.SafeConfigParser()
    cfg_log.add_section('formatters')
    cfg_log.set('formatters', 'keys', 'default')

    cfg_log.add_section('formatter_default')
    cfg_log.set('formatter_default', 'format',
            '%(levelname)s %(filename)s:%(lineno)s '
            '%(processName)s%(threadName)s - %(message)s')
    cfg_log.set('formatter_default', 'class', 'logging.Formatter')

    cfg_log.add_section('handlers')
    cfg_log.set('handlers', 'keys', 'console, info_file')

    cfg_log.add_section('handler_console')
    cfg_log.set('handler_console', 'class', 'bbs.log.ColoredConsoleHandler')
    cfg_log.set('handler_console', 'formatter', 'default')
    cfg_log.set('handler_console', 'args', 'tuple()')

    cfg_log.add_section('handler_info_file')
    cfg_log.set('handler_info_file', 'class', 'logging.FileHandler')
    cfg_log.set('handler_info_file', 'level', 'INFO')
    cfg_log.set('handler_info_file', 'formatter', 'default')
    cfg_log.set('handler_info_file', 'args', '("data/info.log", "w")')

    cfg_log.add_section('handler_debug_file')
    cfg_log.set('handler_debug_file', 'class', 'logging.FileHandler')
    cfg_log.set('handler_debug_file', 'level', 'debug')
    cfg_log.set('handler_debug_file', 'formatter', 'default')
    cfg_log.set('handler_debug_file', 'args', '("data/debug.log", "w")')

    cfg_log.add_section('loggers')
    cfg_log.set('loggers', 'keys', 'root')

    cfg_log.add_section('logger_root')
    cfg_log.set('logger_root', 'level', 'INFO')
    cfg_log.set('logger_root', 'formatter', 'default')
    cfg_log.set('logger_root', 'handlers', 'console,info_file')

    return cfg_log
