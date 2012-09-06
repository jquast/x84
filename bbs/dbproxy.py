from session import getsession

class DBProxy(object):
  def __init__(self, schema):
    self.schema = schema
  def __proxy__(self, method, args):
    getsession().send_event(('db-%s' % (self.schema,)), (method, args,))
    event, data = getsession().read_event((('db-%s' % (self.schema,))))
    return data

  def __cmp__(self, *args):
    return self.__proxy__ ('__cmp__', args)
  def __contains__(self, *args):
    return self.__proxy__ ('__contains__', args)
  def __getitem__(self, *args):
    return self.__proxy__ ('__getitem__', args)
  def __iter__(self, *args):
    return self.__proxy__ ('__iter__', args)
  def __len__(self, *args):
    return self.__proxy__ ('__len__', args)
  def __setitem__(self, *args):
    return self.__proxy__ ('__setitem__', args)
  def get(self, *args):
    return self.__proxy__ ('get', args)
  def has_key(self, *args):
    return self.__proxy__ ('has_key', args)
  def items(self, *args):
    return self.__proxy__ ('items', args)
  def keys(self, *args):
    return self.__proxy__ ('keys', args)
  def pop(self, *args):
    return self.__proxy__ ('pop', args)
  def popitem(self, *args):
    return self.__proxy__ ('popitem', args)
  def setdefault(self, *args):
    return self.__proxy__ ('setdefault', args)
  def update(self, *args):
    return self.__proxy__ ('update', args)
  def values(self, *args):
    return self.__proxy__ ('values', args)
