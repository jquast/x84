import bbs.ini
import threading
import os
import sqlitedict

DATABASES = {}
LOCK = threading.Lock()

class DBHandler(threading.Thread):
  """
  This thread requires a client pipe, a database 'event' in string form
  'db-schema', where 'schema' is a sqlite database name. 'data' is in the form
  of (command, arguments), where command is a dictionary method and arguments
  are optional arguments to that method. This database query is executed and
  the result is sent back to the client pipe with the same 'event' string name
  as received.
  """
  def __init__(self, pipe, event, data):
    self.pipe = pipe
    self.schema = event.split('-',1)[1]
    self.cmd = data[0]
    self.args = data[1:]
    threading.Thread.__init__ (self)

  def run(self):
    global DATABASES
    LOCK.acquire()
    if not self.schema in DATABASES:
      dbpath = os.path.join(bbs.ini.cfg.get('system','sqlite_folder'),
          '%s.sqlite3' % (self.schema,),)
      DATABASES[self.schema] = sqlitedict.SqliteDict(dbpath, autocommit=True)
    LOCK.release ()
    if len(self.args):
      result = getattr(DATABASES[self.schema], self.cmd) ()
    else:
      result = getattr(DATABASES[self.schema], self.cmd) (self.args)
    self.pipe.send (('db-%s' % (self.schema,), result))
    return
