"""
Database request handler for x/84 http://github.com/jquast/x84
"""
import threading
import logging
import os
import sqlitedict
logger = logging.getLogger(__name__)

_lock = threading.Lock()
_databases = {}

def get_db(schema):
    """
    Returns a shared SqliteDict instance, creating a new one if not found
    """
    _lock.acquire()
    if not schema in _databases:
        assert schema.isalnum()
        import bbs.ini
        dbpath = os.path.join(bbs.ini.cfg.get('database','sqlite_folder'),
            '%s.sqlite3' % (schema,),)
        _databases[schema] = sqlitedict.SqliteDict(
                dbpath, autocommit=True)
    _lock.release ()
    return _databases[schema]

class DBHandler(threading.Thread):
    """
    This handler receives a "database command", in the form of a dictionary
    method name and its arguments, and the return value is sent to the session
    pipe with the same 'event' name.
    """
    def __init__(self, pipe, event, data, iterable=False):
        """ Arguments:
              pipe: parent end of multiprocessing.Pipe()
              event: database schema in form of string 'db-schema'
              data: tuple of dictionary method and arguments
        """
        self.pipe = pipe
        self.event = event
        self.schema = event[3:]
        self.cmd = data[0]
        self.args = data[1]
        threading.Thread.__init__ (self)

    def run(self):
        """
        Execute database command and return results to session pipe.
        """
        dictdb = get_db(self.schema)
        assert hasattr(dictdb, self.cmd), \
            "'%(cmd)s' not a valid method of <type 'dict'>" % self
        func = getattr(dictdb, self.cmd)
        assert callable(func), \
            "'%(cmd)s' not a valid method of <type 'dict'>" % self
        logger.debug ('%s/%s(%s)', self.schema, self.cmd, self.args)
        if 0 == len(self.args):
            result = func()
        else:
            result = func(*self.args)
        if self.event[2] == '=':
            # wrap iteratable with special marker,
            self.pipe.send ((self.event, (None, 'StartIteration'),))
            for item in iter(result):
                self.pipe.send ((self.event, item,))
            self.pipe.send ((self.event, (None, StopIteration,),))
            return
        elif self.event[2] == '-':
            self.pipe.send ((self.event, result,))
        else:
            assert False

