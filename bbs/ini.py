"""
 Configuration for x/84 BBS
"""

import ConfigParser
import threading
import sys
import os
cfg = None

def init(cfgFilepath='default.ini'):
  global cfg
  sys.stdout.write (',load %s...' % (cfgFilepath,))
  sys.stdout.flush ()
  # start with default values,
  cfg = ConfigParser.SafeConfigParser()
  cfg.add_section('system')
  cfg.set('system', 'bbsname', 'x/84')
  cfg.add_section('telnet')
  cfg.set('telnet', 'addr', '127.0.0.1')
  cfg.set('telnet', 'port', '6023')
  cfg.add_section('ftp')
  cfg.set('ftp', 'addr', '127.0.0.1')
  cfg.set('ftp', 'port', '6021')
  cfg.set('ftp', 'basedir', 'ftpdata/')
  cfg.set('ftp', 'enable_anonymous', 'no')
  cfg.set('ftp', 'enable_masquerade', 'no')
  cfg.set('ftp', 'enable_fxp', 'no')
  cfg.set('ftp', 'timeout', '1984')
  cfg.set('ftp', 'masq_addr', '64.150.165.47')
  cfg.set('ftp', 'pasv_ports', '61984-65000')
  cfg.set('ftp', 'read_limit', '0')
  cfg.set('ftp', 'write_limit', '0')
  cfg.set('ftp', 'conns_max', '30')
  cfg.set('ftp', 'conns_per_ip', '3')
  cfg.add_section ('matrix')
  cfg.set('matrix', 'newcmds', 'new apply')
  cfg.set('matrix', 'byecmds', 'exit logoff bye quit')
  cfg.set('matrix', 'script', 'matrix')
  cfg.set('matrix', 'topscript', 'top')
  cfg.add_section('database')
  cfg.set('database', 'sqlite_folder', 'data/')
  cfg.add_section('session')
  cfg.set('session', 'log_level', 'debug')
  cfg.set('session', 'default_encoding', 'cp437')
  cfg.set('session', 'default_ttype', 'ansi')
  cfg.set('session', 'scriptpath', 'default/')
  cfg.set('session', 'tap_input', 'no')
  cfg.set('session', 'tap_output', 'no')
  cfg.set('session', 'record_tty', 'yes')
  cfg.set('session', 'ttylog_folder', 'ttyrecordings/')
  cfg.set('session', 'timeout', '1984')
  cfg.set('session', 'door_syspath', '/usr/local/bin:/usr/games')
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
  sys.stdout.write ('ok')
  sys.stdout.flush ()
  if not os.path.exists(cfgFilepath):
    # write only if not exists;
    # otherwise just go with it.
    sys.stdout.write ('- %s does not exist; writing. -' % (cfgFilepath,))
    fp = open(cfgFilepath, 'wb')
    cfg.write (fp)
    fp.close ()
  else:
    # that is, read in all the real .ini values (above values are overwrriten)
    cfg.read (cfgFilepath)
  sys.stdout.write ('ok (%i items).\n' % (len(cfg.sections()),))
