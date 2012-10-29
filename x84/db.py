"""
Database request handler for x/84 http://github.com/jquast/x84
"""
import x84.bbs.exception
import x84.bbs.ini
import threading
import logging
import sys
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
    datapath = x84.bbs.ini.CFG.get('system', 'datapath')
    if not schema in DATABASES:
        assert schema.isalnum()
        if not os.path.exists(datapath):
            os.makedirs (datapath)
        dbpath = os.path.join(datapath, '%s.sqlite3' % (schema,),)
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
        assert event[2] in ('-', '='), ('event name must match db[-=]event')
        self.iterable = event[2] == '='
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
                '(*%d)' % (len(self.args)) if len(self.args) else '()')

        #pylint: disable=W0703
        #        Catching too general exception Exception
        try:
            if 0 == len(self.args):
                result = func()
            else:
                result = func(*self.args)
        except Exception, err:
            # Pokemon exception; send (err_type, err_value)
            return self.pipe.send ((x84.bbs.exception.DatabaseError,
                (sys.exc_info()[0], err)))

        # single value result,
        if not self.iterable:
            return self.pipe.send ((self.event, result))

        # iterable value result,
        self.pipe.send ((self.event, (None, 'StartIteration'),))
        for item in iter(result):
            self.pipe.send ((self.event, item,))
        return self.pipe.send ((self.event, (None, StopIteration,),))
