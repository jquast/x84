""" Database request handler for x/84. """
# std imports
import multiprocessing
import threading
import logging
import errno
import os

# 3rd-party
import sqlitedict

FILELOCK = multiprocessing.Lock()
DATALOCK = {}


def get_database(filepath, table):
    """ Return :class:`sqlitedict.SqliteDict` instance for given database. """
    # pylint: disable=W0602
    #          Using global for 'FILELOCK' but no assignment is done
    global FILELOCK
    with FILELOCK:
        # if the bbs is run as root, file ownerships become read-only
        # and db transactions will throw 'read-only database' errors,
        # exit earlier if we know that file permissions are to blame
        check_db(filepath)

        dictdb = sqlitedict.SqliteDict(filename=filepath,
                                       tablename=table,
                                       autocommit=True)
    return dictdb


def check_db(filepath):
    """
    Verify permission access of given database file.

    :raises AssertionError: file or folder is not writable.
    :raises OSError: could not write containing folder.
    """
    db_folder = os.path.dirname(filepath)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
    assert os.access(db_folder, os.F_OK | os.R_OK), (
        'Must have rw access to db_folder:', db_folder)
    if os.path.exists(filepath):
        assert os.access(filepath, os.F_OK | os.R_OK | os.W_OK), (
            'Must have r+w access to db file:', filepath)


def get_db_filepath(schema):
    """ Return filesystem path of given database ``schema``. """
    from x84.bbs.ini import get_ini
    folder = get_ini('system', 'datapath')
    return os.path.join(folder, '{0}.sqlite3'.format(schema))


def get_db_lock(schema, table):
    """ Return database lock for given ``(schema, table)``. """
    key = (schema, table)
    # pylint: disable=W0602
    #          Using global for 'FILELOCK' but no assignment is done
    global DATALOCK, FILELOCK
    with FILELOCK:
        if key not in DATALOCK:
            DATALOCK[key] = multiprocessing.Lock()
    return DATALOCK[key]


def get_db_func(dictdb, cmd):
    """
    Return callable function of method on ``dictdb``.

    :raises AssertionError: not a valid method or not callable.
    """
    assert hasattr(dictdb, cmd), (
        "{cmd!r} not a valid method of {db_type!r}"
        .format(cmd=cmd, db_type=type(dictdb)))
    func = getattr(dictdb, cmd)
    assert callable(func), (
        "{cmd!r} not a callable method of {db_type!r}"
        .format(cmd=cmd, db_type=type(dictdb)))
    return func


def parse_dbevent(event):
    """
    Parse a database event into ``(iterable, schema)``.

    Called by class initializer, to determine if the event should return
    an iterable, and for what database name (``schema``).

    :rtype: tuple
    """
    assert event[2] in ('-', '='), ('event name must match db[-=]event')
    iterable = event[2] == '='
    schema = event[3:]
    assert schema.isalnum() and os.path.sep not in schema, (
        'database schema {!r} must be alpha-numeric and not contain {!r}'
        .format(schema, os.path.sep))

    return iterable, schema


def log_db_cmd(log, schema, cmd, args):
    """ Log database command (when tap_db ini option is used). """
    s_args = '()'
    if len(args):
        s_args = '(*{0})'.format(len(args))
    log.debug('{schema}/{cmd}{args}'.format(schema=schema,
                                            cmd=cmd,
                                            args=s_args))


class DBHandler(threading.Thread):

    """
    This handler receives and handles a dictionary-based "database command".

    See complimenting :class:`x84.bbs.dbproxy.DBProxy`, which behaves as a
    dictionary and "packs" command iterables through an IPC event queue which
    is then dispatched by the engine.

    The return values are sent to the session queue with equal 'event' name.
    """

    def __init__(self, queue, event, data):
        """
        Class initializer.

        :param multiprocessing.Pipe queue: parent input end of a tty session
                                           ipc queue (``tty.master_write``).
        :param str event: database schema in form of string ``'db-schema'``
                          or ``'db=schema'``.  When ``'-'`` is used, the result
                          is returned as a single transfer. When ``'='``, an
                          iterable is yielded and the data is transfered via
                          the IPC Queue as a stream.
        :param tuple data: a dict method proxy command sequence in form of
                           ``(table, command, arguments)``.  For example,
                           ``('unnamed', 'pop', 0).
        """
        self.log = logging.getLogger(__name__)
        self.queue, self.event = queue, event
        self.table, self.cmd, self.args = data

        self.iterable, self.schema = parse_dbevent(event)
        self.filepath = get_db_filepath(self.schema)

        from x84.bbs.ini import get_ini
        self._tap_db = self.log.isEnabledFor(logging.DEBUG) and (
            get_ini('session', 'tab_db', getter='getboolean'))

        threading.Thread.__init__(self)

    def run(self):
        """ Execute database command and return results to session queue. """
        dictdb = get_database(self.filepath, self.table)
        func = get_db_func(dictdb, self.cmd)
        if self._tap_db:
            log_db_cmd(self.log, self.schema, self.cmd, self.args)

        try:
            # single value result,
            if not self.iterable:
                result = func(*self.args)
                self.queue.send((self.event, result))

            # iterable value result,
            else:
                self.queue.send((self.event, (None, 'StartIteration'),))
                for item in func(*self.args):
                    self.queue.send((self.event, item,))
                self.queue.send((self.event, (None, StopIteration,),))

        # pylint: disable=W0703
        #         Catching too general exception
        except Exception as err:
            # Pokemon exception, send to session
            try:
                self.queue.send(('exception', err,))
            except IOError as err:
                if err.errno == errno.EBADF:
                    # our pipe/queue has been disconnected (the session
                    # has disconnected), heck this might be the cause of
                    # our first exception
                    return
                raise

        finally:
            dictdb.close()
