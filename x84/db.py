"""
Database request handler for x/84 http://github.com/jquast/x84
"""
import threading
import os

FILELOCK = threading.Lock()


class DBHandler(threading.Thread):
    """
    This handler receives a "database command", in the form of a dictionary
    method name and its arguments, and the return value is sent to the session
    queue with the same 'event' name.
    """

    # pylint: disable=R0902
    #        Too many instance attributes (8/7)
    def __init__(self, queue, event, data):
        """ Arguments:
              inp_queue: parent input end of multiprocessing.Queue()
              event: database schema in form of string 'db-schema' or
                  'db=schema'. When '-' is used, the result is returned as a
                  single transfer. When '=', an iterable is yielded and the
                  data is transfered via the IPC Queue as a stream.
        """
        import x84.bbs.ini
        self.queue = queue
        self.event = event
        assert event[2] in ('-', '='), ('event name must match db[-=]event')
        self.iterable = event[2] == '='
        self.schema = event[3:]
        assert self.schema.isalnum() and os.path.sep not in self.schema, (
            'database schema "%s" must be alpha-numeric and not contain %s' % (
                self.schema, os.path.sep,))
        self.table = data[0]
        self.cmd = data[1]
        self.args = data[2]
        folder = x84.bbs.ini.CFG.get('system', 'datapath')
        self._tap_db = x84.bbs.ini.CFG.getboolean('session', 'tap_db')
        self.filepath = os.path.join(folder, '%s.sqlite3' % (self.schema,),)
        threading.Thread.__init__(self)

    def run(self):
        """
        Execute database command and return results to session queue.
        """
        import logging
        import sqlitedict
        logger = logging.getLogger(__name__)
        FILELOCK.acquire()
        # if the bbs is run as root, file ownerships become read-only
        # and db transactions will throw 'read-only database' errors,
        # exit earlier if we know that file permissions are to blame
        if not os.path.exists(os.path.dirname(self.filepath)):
            os.makedirs(os.path.dirname(self.filepath))
        assert os.access(os.path.dirname(self.filepath), os.F_OK|os.R_OK), (
                'Must have read+write+execute access to "%s" for database' % (
                    os.path.dirname(self.filepath),))
        if os.path.exists(self.filepath):
            assert os.access(self.filepath, os.F_OK|os.R_OK), (
                    'Must have read+write access to %s" for database' % (
                        self.filepath,))
        dictdb = sqlitedict.SqliteDict(
            filename=self.filepath, tablename=self.table, autocommit=True)
        FILELOCK.release()
        assert hasattr(dictdb, self.cmd), (
            "'%(cmd)s' not a valid method of <type 'dict'>" % self)
        func = getattr(dictdb, self.cmd)
        assert callable(func), (
            "'%(cmd)s' not a valid method of <type 'dict'>" % self)
        if self._tap_db:
            logger.debug('%s/%s%s', self.schema, self.cmd,
                    '(*%d)' % (len(self.args)) if len(self.args) else '()')

        # single value result,
        if not self.iterable:
            try:
                if 0 == len(self.args):
                    result = func()
                else:
                    result = func(*self.args)
            # pylint: disable=W0703
            #         Catching too general exception
            except Exception as err:
                # Pokemon exception; package & raise from session process,
                self.queue.send(('exception', err,))
                dictdb.close()
                logger.exception(err)
                return
            self.queue.send((self.event, result))
            dictdb.close()
            return

        # iterable value result,
        self.queue.send((self.event, (None, 'StartIteration'),))
        try:
            if 0 == len(self.args):
                for item in func():
                    self.queue.send((self.event, item,))
            else:
                for item in func(*self.args):
                    self.queue.send((self.event, item,))
        # pylint: disable=W0703
        #         Catching too general exception
        except Exception as err:
            # Pokemon exception; package & raise from session process,
            self.queue.send(('exception', err,))
            dictdb.close()
            logger.exception(err)
            return

        self.queue.send((self.event, (None, StopIteration,),))
        dictdb.close()
        return
