"""
Database proxy helper for X/84.
"""

class DBProxy(object):
    """
    Provide dictionary-like object interface via IPC pipe data transfers.
    """
    #pylint: disable=C0111
    #        Missing docstring

    def __init__(self, schema):
        """ @schema: database key
        """
        self.schema = schema

    def __proxy_iter__(self, method, *args):
        """
        Proxy a method that returns a data type supporting __iter__ by yielding
        its IPC event data values until StopIteration is sent.
        """
        from bbs.session import getsession
        event = 'db=%s' % (self.schema,)
        getsession().send_event (event, (method, args))
        event, data = getsession().read_event (events=(event,))
        assert (None, 'StartIteration') == data
        while True:
            event, data = getsession().read_event (events=(event,))
            if data == (None, StopIteration):
                raise StopIteration()
            yield data

    def __proxy__(self, method, *args):
        """
        Proxy a method name and its arguments, then block
        until a response is received.
        """
        from bbs.session import getsession
        event = 'db-%s' % (self.schema,)
        getsession().send_event (event, (method, args))
        event, data = getsession().read_event (events=(event,))
        return data

    def __cmp__(self, *args):
        return self.__proxy__ ('__cmp__', *args)
    __cmp__.__doc__ = dict.__cmp__.__doc__

    def __contains__(self, *args):
        return self.__proxy__ ('__contains__', *args)
    __contains__.__doc__ = dict.__contains__.__doc__

    def __getitem__(self, *args):
        return self.__proxy__ ('__getitem__', *args)
    __getitem__.__doc__ = dict.__getitem__.__doc__

    def __setitem__(self, *args):
        return self.__proxy__ ('__setitem__', *args)
    __setitem__.__doc__ = dict.__setitem__.__doc__

    def __delitem__(self, *args):
        return self.__proxy__ ('__delitem__', *args)
    __delitem__.__doc__ = dict.__delitem__.__doc__

    def get(self, *args):
        return self.__proxy__ ('get', *args)
    get.__doc__ = dict.get.__doc__

    def has_key(self, *args):
        return self.__proxy__ ('has_key', *args)
    has_key.__doc__ = dict.has_key.__doc__

    def setdefault(self, *args):
        return self.__proxy__ ('setdefault', *args)
    setdefault.__doc__ = dict.setdefault.__doc__

    def update(self, *args):
        return self.__proxy__ ('update', *args)
    update.__doc__ = dict.update.__doc__

    def __len__(self):
        return self.__proxy__ ('__len__')
    __len__.__doc__ = dict.__len__.__doc__

    def values(self):
        return self.__proxy__ ('values')
    values.__doc__ = dict.values.__doc__

    def items(self):
        return self.__proxy__ ('items')
    items.__doc__ = dict.items.__doc__

    def iteritems(self):
        return self.__proxy_iter__ ('iteritems')
    iteritems.__doc__ = dict.iteritems.__doc__

    def iterkeys(self):
        return self.__proxy_iter__ ('iterkeys')
    iterkeys.__doc__ = dict.iterkeys.__doc__

    def itervalues(self):
        return self.__proxy_iter__ ('itervalues')
    itervalues.__doc__ = dict.itervalues.__doc__

    def keys(self):
        return self.__proxy__ ('keys')
    keys.__doc__ = dict.keys.__doc__

    def pop(self):
        return self.__proxy__ ('pop')
    pop.__doc__ = dict.pop.__doc__

    def popitem(self):
        return self.__proxy__ ('popitem')
    popitem.__doc__ = dict.popitem.__doc__
