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
  cfg.set('system', 'telnet_addr', '127.0.0.1')
  cfg.set('system', 'telnet_port', '6023')
  cfg.add_section ('matrix')
  cfg.set('matrix', 'newcmds', 'new apply')
  cfg.set('matrix', 'byecmds', 'exit logoff bye quit')
  cfg.set('matrix', 'script', 'matrix')
  cfg.set('matrix', 'topscript', 'top')
  cfg.add_section('database')
  cfg.set('database', 'sqlite_folder', 'data/')
  cfg.add_section('session')
  cfg.set('session', 'log_level', 'debug')
  cfg.set('session', 'default_encoding', 'iso8859-1')
  cfg.set('session', 'default_ttype', 'vt220')
  cfg.set('session', 'scriptpath', 'default/')
  cfg.add_section('irc')
  cfg.set('irc', 'server', 'efnet.xs4all.nl')
  cfg.set('irc', 'port', '6667')
  cfg.set('irc', 'channel', '#prsv')
  cfg.add_section('nua')
  cfg.set('nua', 'min_user', '3')
  cfg.set('nua', 'max_user', '11')
  cfg.set('nua', 'max_pass', '16')
  cfg.set('nua', 'max_email', '30')
  cfg.set('nua', 'max_origin', '24')
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
