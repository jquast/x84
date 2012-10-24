"""
Database request handler for x/84 http://github.com/jquast/x84
"""
import threading
import logging
import os
import sqlitedict
#pylint: disable=C0103
#        Invalid name "logger" for type constant
logger = logging.getLogger(__name__)

FILELOCK = threading.Lock()
DATABASES = {}

def get_db(schema):
    """
    Returns a shared SqliteDict instance, creating a new one if not found
    """
    FILELOCK.acquire()
    if not schema in DATABASES:
        assert schema.isalnum()
        import bbs.ini
        dbpath = os.path.join(bbs.ini.CFG.get('database','sqlite_folder'),
            '%s.sqlite3' % (schema,),)
        DATABASES[schema] = sqlitedict.SqliteDict(filename=dbpath,
                tablename='unnamed', autocommit=True)
    FILELOCK.release ()
    return DATABASES[schema]

class DBHandler(threading.Thread):
    """
    This handler receives a "database command", in the form of a dictionary
    method name and its arguments, and the return value is sent to the session
    pipe with the same 'event' name.
    """
    def __init__(self, pipe, event, data):
        """ Arguments:
              pipe: parent end of multiprocessing.Pipe()
              event: database schema in form of string 'db-schema' or
                  'db=schema'. When '-' is used, the result is returned as a
                  single transfer. When '=', an iterable is yielded and the
                  data is transfered via the IPC pipe as a stream.
        """
        self.pipe = pipe
        self.event = event
        self.schema = event[3:]
        self.table = data[0]
        self.cmd = data[1]
        self.args = data[2]
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
        logger.debug ('%s/%s%s', self.schema, self.cmd,
                '(*%d)' if len(self.args) else '')
        if 0 == len(self.args):
            result = func()
        else:
            result = func(*self.args)
        if self.event[2] == '-':
            self.pipe.send ((self.event, result))
        elif self.event[2] == '=':
            # wrap iteratable with special marker,
            self.pipe.send ((self.event, (None, 'StartIteration'),))
            for item in iter(result):
                self.pipe.send ((self.event, item,))
            self.pipe.send ((self.event, (None, StopIteration,),))
        else:
            assert False

