from session import getsession

class DBProxy(object):
  def __init__(self, schema):
    self.schema = schema

  def __proxy__(self, method, *args):
    event = 'db-%s' % (self.schema,)
    getsession().send_event(event, (method, args,))
    event, data = getsession().read_event((event,'exception',))
    if event != 'exception':
      return data
    t,v,tb = data
    print 'exception:', t,v
    raise t, v

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

