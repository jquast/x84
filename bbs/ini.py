"""
 Configuration for x/84 BBS, https://github.com/jquast/x84/
"""

import logging.config
import os.path


#import logging.config
#import os.path
#import ConfigParser
#import sys

#cfg = None # singleton ..

def init(cfg_bbs='data/default.ini', cfg_log='data/logging.ini'):
    """
    Set system-wide defaults, then open and overlay .ini files.
    """
    logging.config.fileConfig (cfg_log)


    #pylint: disable=R0915
    #        Too many statements (57/50)
    #if
    #global cfg
    #LOGGING_CONF=os.path.join(os.path.dirname(__filename__), 'logging.ini')
    #sys.stdout.write (',load %s...' % (cfg_filepath,))
    #sys.stdout.flush ()
    # start with default values,

    cfg = ConfigParser.SafeConfigParser()
    cfg.add_section('system')
    cfg.set('system', 'bbsname', 'x/84')
    cfg.add_section('telnet')
    cfg.set('telnet', 'addr', '127.0.0.1')
    cfg.set('telnet', 'port', '6023')
    #cfg.add_section('ftp')
    #cfg.set('ftp', 'enabled', 'no')
    #cfg.set('ftp', 'addr', '127.0.0.1')
    #cfg.set('ftp', 'port', '6021')
    #cfg.set('ftp', 'basedir', 'ftpdata/')
    #cfg.set('ftp', 'enable_anonymous', 'no')
    #cfg.set('ftp', 'enable_masquerade', 'no')
    #cfg.set('ftp', 'enable_fxp', 'no')
    #cfg.set('ftp', 'timeout', '1984')
    #cfg.set('ftp', 'masq_addr', '64.150.165.47')
    #cfg.set('ftp', 'pasv_ports', '61984-65000')
    #cfg.set('ftp', 'read_limit', '0')
    #cfg.set('ftp', 'write_limit', '0')
    #cfg.set('ftp', 'conns_max', '30')
    #cfg.set('ftp', 'conns_per_ip', '3')
    cfg.add_section ('matrix')
    cfg.set('matrix', 'newcmds', 'new apply')
    cfg.set('matrix', 'byecmds', 'exit logoff bye quit')
    cfg.set('matrix', 'script', 'matrix')
    cfg.set('matrix', 'topscript', 'top')
    cfg.set('matrix', 'enable_anonymous', 'yes')
    cfg.add_section('database')
    cfg.set('database', 'sqlite_folder', 'data/')
    cfg.add_section('session')
    cfg.set('session', 'log_level', 'debug')
    cfg.set('session', 'default_encoding', 'utf8')
    cfg.set('session', 'default_ttype', 'linux')
    cfg.set('session', 'scriptpath', 'default/')
    cfg.set('session', 'tap_input', 'no')
    cfg.set('session', 'tap_output', 'no')
    cfg.set('session', 'record_tty', 'yes')
    cfg.set('session', 'ttylog_folder', 'ttyrecordings/')
    cfg.set('session', 'timeout', '1984')
    cfg.add_section('door')
    cfg.set('door', 'path', '/usr/local/bin:/usr/games')
    cfg.add_section('irc')
    cfg.set('irc', 'server', 'efnet.xs4all.nl')
    cfg.set('irc', 'port', '6667')
    cfg.set('irc', 'channel', '#prsv')
    cfg.add_section('nua')
    cfg.set('nua', 'script', 'nua')
    cfg.set('nua', 'min_user', '3')
    cfg.set('nua', 'max_user', '11')
    cfg.set('nua', 'max_pass', '16')
    cfg.set('nua', 'max_email', '30')
    cfg.set('nua', 'max_origin', '24')
    cfg.set('nua', 'allow_apply', 'yes')
    cfg.set('nua', 'invalid_handles', ' '.join \
        ((cfg.get('matrix','byecmds'),
          cfg.get('matrix','newcmds'),
          'new sysop wfc anonymous',)))
    cfg.add_section('dopewars')
    cfg.set('dopewars', 'scorefile', 'data/dopewars.scores')
    cfg.set('dopewars', 'pidfile', 'data/dopewars.pid')
    cfg.set('dopewars', 'logfile', 'data/dopewars.log')
    sys.stdout.write ('ok')
    sys.stdout.flush ()
    if not os.path.exists(cfg_filepath):
        # write only if not exists;
        # otherwise just go with it.
        sys.stdout.write ('- %s does not exist; writing. -' % (cfg_filepath,))
        fptr = open(cfg_filepath, 'wb')
        cfg.write (fptr)
        fptr.close ()
    else:
        # that is, read in all the real .ini values and replace
        cfg.read (cfg_filepath)
    sys.stdout.write ('ok (%i items).\n' % (len(cfg.sections()),))
