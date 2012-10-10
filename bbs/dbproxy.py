"""
Database proxy helper for X/84.
"""

def _sendfunc(event, data):
    from session import getsession
    return getsession().send_event(event, data)

def _recvfunc(events):
    from session import getsession
    event, data = getsession().read_event(events)
    assert event in events
    return data



class DBProxy(object):
    """
      Provide dictionary-like object interface with sendfunc() and recvfunc()
      wrappers, intended for IPC pipe data transfers. Sub-processes to the main
      process (FTP server) use DBProxy directly with their own send and recv
      wrappers. Session runtimes use the derived class DBSessionProxy.
    """
    def __init__(self, schema, send_f, recv_f):
        """ @schema: database key
            @send_f: callable receiving arguments (u'event', (u'data',))
            @recv_f: callable receiving arguments ((u'event',))
        """
        self.schema = schema
        self.send_f = send_f
        self.recv_f = recv_f

    def __proxy__(self, method, *args):
        """
        Proxy a method name and its arguments via
          send.sendfunc(dbkey, (method, args,)).
        """
        #from session import logger
        event = 'db-%s' % (self.schema,)
        # if tap ...
        #logger.debug ('%s (%s (%s, %s))', self.send_f, event, method, args)
        self.send_f (event, (method, args,))
        return self.recv_f((event,))

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

    def keys(self):
        return self.__proxy__ ('keys')
    keys.__doc__ = dict.keys.__doc__

    def pop(self):
        return self.__proxy__ ('pop')
    pop.__doc__ = dict.pop.__doc__

    def popitem(self):
        return self.__proxy__ ('popitem')
    popitem.__doc__ = dict.popitem.__doc__


class DBSessionProxy(DBProxy):
    """
    Provide database proxy suitable for use with BBS Sessions.
    """
    def __init__(self, schema):
        DBProxy.__init__(self, schema, send_f=_sendfunc, recv_f=_recvfunc)
