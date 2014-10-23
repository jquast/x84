"""
Database proxy helper for X/84.
"""
# std
import logging

# for session-based ipc

# for drect-db access
from x84.db import (
    get_db_filepath,
    should_tapdb,
    get_database,
    get_db_func,
    get_db_lock,
    log_db_cmd,
)


class DBProxy(object):
    """
    Provide dictionary-like object interface to a database. a database call,
    such as __len__() or keys() is issued as a command to the main engine,
    which spawns a thread to acquire a lock on the database and return the
    results via IPC pipe transfer.
    """

    def __init__(self, schema, table='unnamed', use_session=True):
        """
        Arguments:
            schema: database key, to become basename of .sqlite3 files.
        """
        from x84.bbs.session import getsession
        self.log = logging.getLogger(__name__)
        self.schema = schema
        self.table = table
        self._tap_db = should_tapdb()
        self.session = use_session and getsession()

    def proxy_iter_session(self, method, *args):
        """
        Proxy for iterable dictionary method calls over session IPC pipe.
        """
        if self.session:
            event = 'db=%s' % (self.schema,)
            self.session.flush_event(event)
            self.session.send_event(event, (self.table, method, args))
            data = self.session.read_event(event)
            assert data == (None, 'StartIteration'), (
                'iterable proxy used on non-iterable, %r' % (data,))
            data = self.session.read_event(event)
            while data != (None, StopIteration):
                yield data
                data = self.session.read_event(event)
            self.session.flush_event(event)

    def proxy_method_direct(self, method, *args):
        """
        Proxy for direct dictionary method calls.
        """
        dictdb = get_database(filepath=get_db_filepath(self.schema),
                              table=self.table)
        try:
            func = get_db_func(dictdb, method)
            if self._tap_db:
                log_db_cmd(self.log, self.schema, method, args)
            return func(*args)
        finally:
            dictdb.close()

    def proxy_iter(self, method, *args):
        """
        Proxy for iterable dictionary method calls.
        """
        if self.session:
            return self.proxy_iter_session(method, *args)

        return self.proxy_method_direct(method, *args)

    def proxy_method(self, method, *args):
        """
        Proxy for dictionary method calls.
        """
        if self.session:
            return self.proxy_method_session(method, *args)

        return self.proxy_method_direct(method, *args)

    def proxy_method_session(self, method, *args):
        """
        Proxy for dictionary method calls over IPC pipe.
        """
        event = 'db-%s' % (self.schema,)
        self.session.send_event(event, (self.table, method, args))
        return self.session.read_event(event)

    def acquire(self):
        lock = get_db_lock(schema=self.schema, table=self.table)
        if self._tap_db:
            self.log.debug('lock acquire schema={0}, table={1}'
                           .format(self.schema, self.table))
        lock.acquire()

    def release(self):
        lock = get_db_lock(schema=self.schema, table=self.table)
        if self._tap_db:
            self.log.debug('lock release schema={0}, table={1}'
                           .format(self.schema, self.table))
        lock.release()

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.release()

    # pylint: disable=C0111
    #        Missing docstring
    def __contains__(self, key):
        return self.proxy_method('__contains__', key)
    __contains__.__doc__ = dict.__contains__.__doc__

    def __getitem__(self, key):
        return self.proxy_method('__getitem__', key)
    __getitem__.__doc__ = dict.__getitem__.__doc__

    def __setitem__(self, key, value):
        return self.proxy_method('__setitem__', key, value)
    __setitem__.__doc__ = dict.__setitem__.__doc__

    def __delitem__(self, key):
        return self.proxy_method('__delitem__', key)
    __delitem__.__doc__ = dict.__delitem__.__doc__

    def get(self, key, default=None):
        return self.proxy_method('get', key, default)
    get.__doc__ = dict.get.__doc__

    def has_key(self, key):
        return self.proxy_method('has_key', key)
    has_key.__doc__ = dict.has_key.__doc__

    def setdefault(self, key, value):
        return self.proxy_method('setdefault', key, value)
    setdefault.__doc__ = dict.setdefault.__doc__

    def update(self, *args):
        return self.proxy_method('update', *args)
    update.__doc__ = dict.update.__doc__

    def __len__(self):
        return self.proxy_method('__len__')
    __len__.__doc__ = dict.__len__.__doc__

    def values(self):
        return self.proxy_method('values')
    values.__doc__ = dict.values.__doc__

    def items(self):
        return self.proxy_method('items')
    items.__doc__ = dict.items.__doc__

    def iteritems(self):
        return self.proxy_iter('iteritems')
    iteritems.__doc__ = dict.iteritems.__doc__

    def iterkeys(self):
        return self.proxy_iter('iterkeys')
    iterkeys.__doc__ = dict.iterkeys.__doc__

    def itervalues(self):
        return self.proxy_iter('itervalues')
    itervalues.__doc__ = dict.itervalues.__doc__

    def keys(self):
        return self.proxy_method('keys')
    keys.__doc__ = dict.keys.__doc__

    def pop(self):
        return self.proxy_method('pop')
    pop.__doc__ = dict.pop.__doc__

    def popitem(self):
        return self.proxy_method('popitem')
    popitem.__doc__ = dict.popitem.__doc__
