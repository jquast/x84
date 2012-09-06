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
  cfg.set('system', 'scriptpath', 'default/')
  cfg.set('system', 'matrixscript', 'matrix')
  cfg.set('system', 'topscript', 'top')
  cfg.set('system', 'local_wfc', '')
  cfg.set('system', 'wfcscript', 'wfc')
  cfg.set('system', 'local_ttys', '')
  cfg.set('system', 'telnet_port', '23')
  cfg.set('system', 'finger_port', '79')
  cfg.set('system', 'max_sessions', '3')
  cfg.set('system', 'default_keymap', 'ansi')
  cfg.set('system', 'detach_keystroke', '\004')
  cfg.set('system', 'log_file', 'debug.log')
  cfg.set('system', 'log_level', '2')
  cfg.set('system', 'log_rotate', '5')
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
  cfg.set('nua', 'invalid_handles', 'bye new logoff quit sysop wfc all none')
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
