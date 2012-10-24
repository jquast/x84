"""
Database proxy helper for X/84.
"""
import logging
import time

import bbs.session

#pylint: disable=C0103
#        Invalid name "logger" for type constant (should match
logger = logging.getLogger()

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
        event = 'db=%s' % (self.schema,)
        # oH! if we did a statement such as:
        # for key in DBProxy('userbase').iterkeys():
        #    if handle == 'oh,Hai!':
        #       break
        # the next call would still have values on the pipe, and this
        # assertion of StartIteration would fail. To prevent, we flush
        # the input pipe first .. but what if we were ninja fast?
        bbs.session.getsession().flush_event (event)
        bbs.session.getsession().send_event (event, (self.table, method, args))
        data = bbs.session.getsession().read_event (event)
        assert data == (None, 'StartIteration'), (
                'iterable proxy used on non-iterable, %r', data)
        data = bbs.session.getsession().read_event (event)
        while data != (None, StopIteration):
            yield data
            data = bbs.session.getsession().read_event (event)

    def proxy_method(self, method, *args):
        """
        Proxy for dictionary methods called over IPC pipe.
        """
        event = 'db-%s' % (self.schema,)
        bbs.session.getsession().send_event (event, (self.table, method, args))
        return bbs.session.getsession().read_event (event)

    def acquire(self, timeout=None):
        """
        Acquire bbs-global lock on database, possibly blocking until it can be
        obtained. When timeout is not None, return False if lock cannot be
        acquired after timeout has elapsed in seconds.
        """
        if timeout is None:
            timeout = float('inf')
        event = 'lock-%s' % (self.schema,)
        stime = time.time ()
        while time.time() - stime < timeout:
            bbs.session.getsession().send_event (event, ('acquire', timeout))
            # engine answers 'True' if lock is acquired, 'False' if not,
            if bbs.session.getsession().read_event (event):
                return True
            time.sleep (1)
            logger.warn ('%s cannot acquire, re-trying ', event)
        logger.warn ('failed to acquire lock.')
        return False

    def release(self):
        """
        Release bbs-global lock on database.
        """
        event = 'lock-%s' % (self.schema,)
        bbs.session.getsession().send_event (event, ('release', None))

    def locked(self):
        """
        Tests wether the lock is currently locked
        """
        event = 'lock-%s' % (self.schema,)
        bbs.session.getsession().send_event (event, ('locked', None))
        return bbs.session.getsession().read_event (event)

    def __cmp__(self, *args):
        return self.proxy_method ('__cmp__', *args)
    __cmp__.__doc__ = dict.__cmp__.__doc__

    def __contains__(self, *args):
        return self.proxy_method ('__contains__', *args)
    __contains__.__doc__ = dict.__contains__.__doc__

    def __getitem__(self, *args):
        return self.proxy_method ('__getitem__', *args)
    __getitem__.__doc__ = dict.__getitem__.__doc__

    def __setitem__(self, *args):
        return self.proxy_method ('__setitem__', *args)
    __setitem__.__doc__ = dict.__setitem__.__doc__

    def __delitem__(self, *args):
        return self.proxy_method ('__delitem__', *args)
    __delitem__.__doc__ = dict.__delitem__.__doc__

    #pylint: disable=C0111
    #        Missing docstring
    def get(self, *args):
        return self.proxy_method ('get', *args)
    get.__doc__ = dict.get.__doc__

    def has_key(self, *args):
        return self.proxy_method ('has_key', *args)
    has_key.__doc__ = dict.has_key.__doc__

    def setdefault(self, *args):
        return self.proxy_method ('setdefault', *args)
    setdefault.__doc__ = dict.setdefault.__doc__

    def update(self, *args):
        return self.proxy_method ('update', *args)
    update.__doc__ = dict.update.__doc__

    def __len__(self):
        return self.proxy_method ('__len__')
    __len__.__doc__ = dict.__len__.__doc__

    def values(self):
        return self.proxy_method ('values')
    values.__doc__ = dict.values.__doc__

    def items(self):
        return self.proxy_method ('items')
    items.__doc__ = dict.items.__doc__

    def iteritems(self):
        return self.proxy_iter ('iteritems')
    iteritems.__doc__ = dict.iteritems.__doc__

    def iterkeys(self):
        return self.proxy_iter ('iterkeys')
    iterkeys.__doc__ = dict.iterkeys.__doc__

    def itervalues(self):
        return self.proxy_iter ('itervalues')
    itervalues.__doc__ = dict.itervalues.__doc__

    def keys(self):
        return self.proxy_method ('keys')
    keys.__doc__ = dict.keys.__doc__

    def pop(self):
        return self.proxy_method ('pop')
    pop.__doc__ = dict.pop.__doc__

    def popitem(self):
        return self.proxy_method ('popitem')
    popitem.__doc__ = dict.popitem.__doc__
