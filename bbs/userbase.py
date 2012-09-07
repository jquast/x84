from session import getsession, logger
from dbproxy import DBProxy

db = DBProxy('userbase')

# XXX Begin Compatibility
# XXX Rename / Cut
def finduser(handle):
  " Given handle, discover and return database key, matched case-insensitive "
  for k in db.keys():
    if k.lower() == handle.lower():
      return k

def userexist(handle):
  " return True if user exists "
  return db.has_key(handle)

def authuser(handle, try_pass):
  """
    Return True if user by key of handle exists, has a password, the
    password matches the try_pass argument, and password is not None.
  """
  h= finduser(handle)
  if h is None:
    return None
  u= getuser(h)
  if u is None:
    return None
  return u.password is not None and try_pass == u.password

def getuser(handle):
  " Return User object instance, retrieved by handle. "
  return db[handle]

def listusers():
  """
  Return list of user record instances by iterating over all handle keys,
  users without a password are discluded unless allUsers is set to True.
  """
  return db.values ()

def listgroups():
  " Return list of all groups on active accounts. "
  groups = set()
  for user in listusers():
    map(groups.add, user.groups)
  return groups

def groupmembers():
  " return dict of groups containing list of members. "
  return dict([(grp, [u for u in db.values() if grp in u.groups])
    for grp in listgroups()])

def membersofgroup(group):
  " return list of users found in group by name. "
  return groupmembers()[group]
# XXX Rename
# XXX Begin Compatibility

class User(object):
  _handle = None
  _calls = 0
  _lastcall = 0
  _groups = []
  _location = ''
  _hint = ''
  _saved = False
  _postrefs = []
  _password = None
  _plan = ''
  def __init__(self, handle='anonymous', password=u'', location=u'', hint=u''):
    self.handle = handle
    self.password = password
    self.location = location
    self.hint = hint

  @property
  def calls(self):
    return self._calls
  @calls.setter
  def calls(self, value):
    assert type(value) is int
    self._calls = value

  @property
  def handle(self):
    return self._handle
  @handle.setter
  def handle(self, value):
    assert type(value) is unicode and len(value) > 0
    self._handle = value

  @property
  def lastcall(self):
    return self._lastcall
  @lastcall.setter
  def lastcall(self, value):
    assert type(value) is float
    self._lastcall = value

  @property
  def groups(self):
    return self._groups
  @groups.setter
  def groups(self, value):
    assert type(value) is list
    self._groups = value

  @property
  def location(self):
    return self._location
  @location.setter
  def location(self, value):
    assert type(value) is unicode
    self._location = value

  @property
  def hint(self):
    return self._hint
  @hint.setter
  def hint(self, value):
    assert type(value) is unicode
    self._hint = value

  @property
  def postrefs(self):
    return self._postrefs
  @postrefs.setter
  def postrefs(self, value):
    assert type(value) is list
    self._postrefs = value

  @property
  def password(self):
    return self._password
  @password.setter
  def password(self, value):
    assert type(value) is unicode
    self._password = value

  @property
  def plan(self):
    return self._plan
  @plan.setter
  def plan(self, value):
    assert type(value) is unicode
    self._plan = value

# XXX Compatibility
# XXX Rename / Cut
  def set (self, key, value):
    db[self.handle].__setattr__ (key, value)

  def get(self, key):
    return db[self.handle].__getattr__(key)

  def has_key(self, key):
    return hasattr(db[self.handle], key)

  def add(self):
    if 0 == len(listusers()) and not 'sysop' in self.groups:
      logger.warn ('first new user becomes sysop: %s', self.handle)
      self.groups = list(('sysop',))
    db[self.handle] = self

  def delete(self):
    del db[self.handle]

  def addgroup (self, group):
    db[self.handle].groups = [g for g in db[self.handle].groups if g != group] \
        + [group,]
  def delgroup (self, group):
    db[self.handle].groups = [g for g in db[self.handle].groups if g != group]

  def posts(self):
    return self._postrefs

  def numPosts(self):
    return len(self._postrefs)

  def post(self, msg_index):
    assert type(msg_index) is int
    db[self.handle].postrefs = list((msg_index,) + db[self.handle].postrefs)
# XXX End compatibility
# XXX Rename / Cut
