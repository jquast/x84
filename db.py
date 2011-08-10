"""
 ZODB Database interface for 'The Progressive' BBS.
"""
__author__ = 'Johannes Lundberg'
__copyright__ = 'Copyright (C) 2005 Johannes Lundberg'
__license__ = 'Public Domain'
__version__ = '$Id'

# age of unused deleted data in database
# to purge on init in L{openDB}. theoretically,
# we could rollback, though there are no functions
# implemented to assist in that work
pack_days = 0

# root key of database for userland scripts
UDB='udb'

# list of config files to load after main.cfg
CONFIG_FILES=['userbase.cfg']

# we can't use the log module in the database,
# because its a circular dependency, information
# is kept to a minimum and sys.stdout is used for
# messages

from ZODB import DB
from ZODB.FileStorage import FileStorage
import ZODB.POSException
import transaction
import sys
from persistent import Persistent
from threading import Lock
from BTrees.OOBTree import OOBTree

from persistent.mapping import PersistentMapping
from persistent.list import PersistentList

def load_cfg(config_files=CONFIG_FILES):
  # load
  import imp
  global cfgfile_option
  cfgfile_option = {}

  sys.stdout.write('[db] Loading configuration files:\n')
  if len(sys.argv) > 1:
    sys.stdout.write ('     using alternate config: %s\n' % (sys.argv[1],))
    CONFIG_FILES.insert (0,sys.argv[1])
  else:
    sys.stdout.write ('     using default main.cfg\n')
    CONFIG_FILES.insert (0,'main.cfg')

  for filename in CONFIG_FILES:
    sys.stdout.write ('     ... %s\n' % (filename,))
    file, filename, (suffix, mode, type) = \
      open(filename, 'U'), filename, ('.cfg', 'U', 1)
    # exceptions may be raised here on syntax errors,
    # they could be presented more helpfully XXX
    script = imp.load_module(filename[filename.find('.')],
      file, filename, (suffix, mode, type))
    for opt in [o for o in dir(script) if not o.startswith('__')]:
      v, d = getattr(script, opt)
      cfgfile_option[opt] = \
        { 'default': v, 'help': d}

def openDB():
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
  global users, msgs, logfile

  sys.stdout.write('[db] loading...\n')
  database = DB(FileStorage('data/system'))
  db_tm = transaction.TransactionManager()

  # remove old database revisions over 90 days on open
  sys.stdout.write ('[db] packing database, days=%i' % (pack_days,))
  database.pack (days=pack_days)

  sys.stdout.write ('[db] open database')
  # XXX deprication - zodb now wants a transaction manager
  connection = database.open() #txn_mgr=db_tm)

  root = connection.root()
  for key in ('logfile','user','msgs','cfg'):
    if not root.has_key(key):
      sys.stdout.write ('[db] primary database %s does not exist, creating\n' % (key,))
      root[key] = OOBTree()
  users, msgs, logfile = root['user'], root['msgs'], root['logfile']
  commit ()
  dblock = Lock()
  sys.stdout.write ('[db] database server ready\n')

  # XXX use alt config as first command argument,
  # should getopt somewhere else instead
  if len(sys.argv) > 1:
    return load_cfg(sys.argv[1])
  return load_cfg()

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

  Use C{PersistentList} as data type for repositories, and check for
  existance in the script's init() function::

    def init():
       global udb
       udb = openudb ('new database')
       if not udb.has_key ('my list'):
         lock()
         udb['my list'] = PersistentList()
         commit ()
         unlock ()

  @return: a database repository instance of type PersistentMapping
  """
  # Key of the root database to store database records for the userland
  if not root.has_key(UDB):
    sys.stdout.write('[db] creating new master userland database: %s' % (UDB,))
    root[UDB] = PersistentMapping()
  if not root[UDB].has_key(name):
    sys.stdout.write('[db] creating new userland database on open: %s' % (name,))
    root[UDB][name] = PersistentMapping()
  return root[UDB][name]

def deleteudb(name):
  """
  Remove a custom user database.
  """
  if not root[UDB].has_key(name):
    return
  sys.stdout.write ('[db] deleting user database: %s' % (name,))
  del root[UDB][name]

# XXX insane
class Cfg:
  """
  The Cfg class is a wrapper on the C{root['cfg']} variable, but
  the getattr method is overrided, so that if the configuration option
  is not available, it is retrieved from the L{default} module variable
  of the same name.
  """
  def __delattr__ (self, key):
    try:
      del root['cfg'][key]
    except:
      pass
  def __setattr__ (self, key, value):
    lock()
    root['cfg'][key] = value
    commit()
    unlock()
  def __getattr__ (self, key):
    if cfgfile_option.has_key(key):
      return cfgfile_option[key]['default']
    else:
      return root['cfg'][key]

" @var cfg: an exported instance of the L{Cfg} class. "
cfg = Cfg()
