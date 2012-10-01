
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

  def __contains__(self, *args):
    return self.__proxy__ ('__contains__', *args)

  def __getitem__(self, *args):
    return self.__proxy__ ('__getitem__', *args)

  def __setitem__(self, *args):
    return self.__proxy__ ('__setitem__', *args)

  def get(self, *args):
    return self.__proxy__ ('get', *args)

  def has_key(self, *args):
    return self.__proxy__ ('has_key', *args)

  def setdefault(self, *args):
    return self.__proxy__ ('setdefault', *args)

  def update(self, *args):
    return self.__proxy__ ('update', *args)

  def __len__(self):
    return self.__proxy__ ('__len__')

  def values(self):
    return self.__proxy__ ('values')

  def items(self):
    return self.__proxy__ ('items')

  def keys(self):
    return self.__proxy__ ('keys')

  def pop(self):
    return self.__proxy__ ('pop')

  def popitem(self):
    return self.__proxy__ ('popitem')


def _sendfunc(event, data):
  from session import getsession
  return getsession().send_event(event, data)


def _recvfunc(events):
  from session import getsession
  ev, data = getsession().read_event(events)
  assert ev in events
  return data


class DBSessionProxy(DBProxy):
  """
  Provide database access via a proxy to terminal sessions
  """
  def __init__(self, schema):
    DBProxy.__init__(self, schema, send_f=_sendfunc, recv_f=_recvfunc)
