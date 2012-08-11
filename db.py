"""
 Database & Configuration for x/84 BBS
"""
__author__ = 'Johannes Lundberg, Jeffrey Quast'
__copyright__ = 'Copyright (C) 2011 Johannes Lundberg, Jeffrey Quast'
__license__ = 'ISC'

import ConfigParser
import threading
import BTrees
import sys
import os

# age of unused deleted data in database
# to purge on init in L{openDB}. theoretically,
# we could rollback, though there are no functions
# implemented to assist in that work
pack_days = 0

# root key of database for userland scripts
UDB='udb'

import ZODB
import ZODB.FileStorage
import transaction
import persistent

def load_cfg(cfgFilepath='default.ini'):
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
  return cfg
  sys.stdout.write ('ok (%i items).\n' % (len(cfg.sections()),))

def openDB(cfgFile='default.ini'):
  """
  Initialize the database. The following global variables are exported:
    - B{database}: zodb file storage-based object database
    - B{db_tm}: database transaction manager
    - B{connection}: database connection instance
    - B{root}: root object access to connection instance
    - B{dblock}: database lock, to lock between threads
    - B{users}: users database
    - B{msgs}: msgs database
    - B{logfile}: log database
  """

  global database, db_tm, connection, root, dblock
  global users, msgs, logfile, cfg

  # we can't use the log module, as it records entries
  # to the database, causing a circular dependency,
  # minimal information is sent to sys.stdout,
  # think: doom init() load screen.
  sys.stdout.write ('[db: load')
  sys.stdout.flush ()
  database = ZODB.DB(ZODB.FileStorage.FileStorage('data/system'))
  db_tm = transaction.TransactionManager()

  # remove old database revisions over 90 days on open
  sys.stdout.write (',pack(%i)' % (pack_days,))
  sys.stdout.flush ()
  database.pack (days=pack_days)

  sys.stdout.write (',open')
  sys.stdout.flush ()
  # XXX deprication - zodb now wants a transaction manager
  connection = database.open() #txn_mgr=db_tm)

  root = connection.root()
  for key in ('logfile','user','msgs',):
    if not root.has_key(key):
      sys.stdout.write ('\n- DB %s does not exist, creating -' % (key,))
      root[key] = BTrees.OOBTree.OOBTree()
  users, msgs, logfile = root['user'], root['msgs'], root['logfile']
  commit ()
  dblock = threading.Lock()

  cfg = load_cfg(cfgFile)
  sys.stdout.write (']\n')
  return

def commit():
  " Commit pending transactions. "
  transaction.get().commit()
  #db_tm.get().commit()

def close():
  " Close database connection. "
  sys.stdout.write ('[db] database closing, transfer counts: %s\n' \
            % repr(connection.getTransferCounts()))
  try:
    try:
      connection.close()
    except ZODB.POSException.ConnectionStateError:
      sys.stdout.write ('[db] Failed to close database connection!\n')
      sys.stdout.write ('[db] %s' % (traceback.format_exception_only (type, value),))
      sys.stdout.write ('[db] %s' % (traceback.format_tb (tb),))
      try:
        sys.stdout.write ('[db] Commit dangling transaction:')
        commit()
        sys.stdout.write ('[db] Success')
      except:
        sys.stdout.write ('[db] Attempt to commit dangling transaction failed!')
        sys.stdout.write ('[db] %s' % (traceback.format_exception_only (type, value),))
        sys.stdout.write ('[db] %s' % (traceback.format_tb (tb),))
        sys.stdout.write ("[db] Please ensure @db.locker's are placed appropriately")
  finally:
    # one last shot, bbs crashes out otherwise
    connection.close()
    database.close()

def lock():
  """
  Aquire a lock to database. All other database transactions are delayed
  until it hs been released using unlock()
  """
  dblock.acquire()

def unlock():
  " Release lock to database. "
  dblock.release()

def locker(f,*a):
  """
  Use this function wrapper to manage safe lock(), commit(), and
  unlock() counts. Currently it is not guarenteed for transactions
  within a function wrapped by L{locker} can fail safely. Simply place
  a C{@locker} before a function defintion to wrap that function.
  """
  def l(*a):
    # aquire lock
    lock()
    # call function
    f(*a)
    # commit
    commit()
    # and unlock
    unlock()
  return l

def openudb(name):
  """
  When creating your own database, use this wrapper to make a custom
  unique database repository, that persists and is shared across threads.
  For example::

    udb = openudb('samurais')

  If the database does not exist, it will be created. Make sure to use
  L{locker} as a wrapper above any functions that make transactions
  to a udb database.

  Use C{persistent.PersistentList} as data type for repositories, and check for
  existance in the script's init() function::

    def init():
       global udb
       udb = openudb ('new database')
       if not udb.has_key ('my list'):
         lock()
         udb['my list'] = persistent.PersistentList()
         commit ()
         unlock ()

  @return: a database repository instance of type persistent.PersistentMapping
  """
  # Key of the root database to store database records for the userland
  if not root.has_key(UDB):
    sys.stdout.write('[db] creating new master userland database: %s' % (UDB,))
    root[UDB] = persistent.mapping.PersistentMapping()
  if not root[UDB].has_key(name):
    sys.stdout.write('[db] creating new userland database on open: %s' % (name,))
    root[UDB][name] = persistent.mapping.PersistentMapping()
  return root[UDB][name]

def deleteudb(name):
  """
  Remove a custom user database.
  """
  if not root[UDB].has_key(name):
    return
  sys.stdout.write ('[db] deleting user database: %s' % (name,))
  del root[UDB][name]
