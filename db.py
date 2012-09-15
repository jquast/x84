import threading
import traceback
import logging
import os
import sys
import sqlitedict
import bbs.ini
logger = logging.getLogger(__name__)
DATABASES = {}
LOCK = threading.Lock()

class DBHandler(threading.Thread):
  """
  This thread requires a client pipe, a database 'event' in string form
  'db-schema', where 'schema' is a sqlite database name. 'data' is in the form
  of (command, arguments), 'command' is a string of any method, and arguments
  are optional arguments to that method. This database query is executed and
  the result is sent back to the client pipe with the same 'event' string name
  as received.
  """
  def __init__(self, pipe, event, data):
    self.pipe = pipe
    self.event = event
    self.schema = event.split('-',1)[1]
    self.cmd = data[0]
    self.args = data[1]
    threading.Thread.__init__ (self)

  def run(self):
    global DATABASES
    LOCK.acquire()
    if not self.schema in DATABASES:
      dbpath = os.path.join(bbs.ini.cfg.get('database','sqlite_folder'),
          '%s.sqlite3' % (self.schema,),)
      DATABASES[self.schema] = sqlitedict.SqliteDict(dbpath, autocommit=True)
    db = DATABASES[self.schema]
    LOCK.release ()
    assert hasattr(db, self.cmd), \
        "'%(_cmd)s' not a valid method of <type 'dict'>" % self
    f = getattr(db, self.cmd)
    assert callable(f), \
        "'%(_cmd)s' not a valid method of <type 'dict'>" % self
    logger.debug ('%s/%s(%s)', self.schema, self.cmd, self.args)
    try:
      result = f() if 0==len(self.args) else f(*self.args)
      self.pipe.send ((self.event, result,))
    except:
      t, v, tb= sys.exc_info()
      self.pipe.send (('exception', (t, v, traceback.format_tb(tb),)))
