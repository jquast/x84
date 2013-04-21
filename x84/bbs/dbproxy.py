"""
Database proxy helper for X/84.
"""
import time


class DBProxy(object):
    """
    Provide dictionary-like object interface to a database. a database call,
    such as __len__() or keys() is issued as a command to the main engine,
    which spawns a thread to acquire a lock on the database and return the
    results via IPC pipe transfer.
    """

    def __init__(self, schema, table='unnamed'):
        """
        Arguments:
            schema: database key, to become basename of .sqlite3 files.
        """
        self.schema = schema
        self.table = table

    def proxy_iter(self, method, *args):
        """
        Iterable proxy for dictionary methods called over IPC pipe.
        """
        import x84.bbs.session
        event = 'db=%s' % (self.schema,)
        session = x84.bbs.session.getsession()
        session.flush_event(event)
        session.send_event(event, (self.table, method, args))
        data = session.read_event(event)
        assert data == (None, 'StartIteration'), (
            'iterable proxy used on non-iterable, %r' % (data,))
        data = session.read_event(event)
        while data != (None, StopIteration):
            yield data
            data = session.read_event(event)
        session.flush_event(event)

    def proxy_method(self, method, *args):
        """
        Proxy for dictionary methods called over IPC pipe.
        """
        import x84.bbs.session
        event = 'db-%s' % (self.schema,)
        session = x84.bbs.session.getsession()
        session.send_event(event, (self.table, method, args))
        return session.read_event(event)

    def acquire(self, blocking=True, stale=2.0):
        """
        Acquire a fine-grained BBS-global lock, blocking or non-blocking.

        When invoked with the blocking argument set to True (the default),
        block until the lock is acquired, and return True.

        When invoked with the blocking argument set to False, do not block.
        Returns False if lock is not acquired.

        If the engine has held the lock longer than ``stale`` seconds, the
        lock is granted anyway.
        """
        import x84.bbs.session
        event = 'lock-%s/%s' % (self.schema, self.table)
        session = x84.bbs.session.getsession()
        while True:
            session.send_event(event, ('acquire', stale))
            data = session.read_event(event)
            if data is True or not blocking:
                return data
            time.sleep(0.1)

    def release(self):
        """
        Release bbs-global lock on database.
        """
        import x84.bbs.session
        event = 'lock-%s/%s' % (self.schema, self.table)
        session = x84.bbs.session.getsession()
        return session.send_event(event, ('release', None))

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
