from dbproxy import DBProxy
import bcrypt

db = DBProxy('userbase')

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def listusers():
  """
  Return list of user record instances by iterating over all handle keys,
  users without a password are discluded unless allUsers is set to True.
  """
  return db.values ()

def finduser(handle):
  """Given handle, discover and return matching database key."""
  for key in db.keys():
    if key.lower() == handle.lower():
      return key

def getuser(handle):
  """Return User object instance, retrieved by handle."""
  return db[handle]

def userexist(handle):
  """Return True if user exists."""
  import warnings
  warnings.warn(DeprecationWarning, 'userexist deprecated, use finduser()', 2)
  return db.has_key(handle)

def authuser(handle, try_pass):
  """Return True if try_pass is the correct password for a user."""
  assert type(try_pass) is unicode
  assert len(try_pass) > 0
  (salt, hashed) = getuser(handle).password
  return hashed == bcrypt.hashpw(try_pass, salt) \
      if not None in (salt, hashed) \
      else False

class User(dict):
  _handle = None
  _calls = 0
  _lastcall = 0
  _location = u''
  _hint = u''
  _password = (None, None)
  _plan = ''

  def __init__(self, handle=u'anonymous', password=u'', location=u'', hint=u''):
    self.handle = handle
    self.password = password
    self.location = location
    self.hint = hint
    dict.__init__ (self)
    self.set('groups', set(),)


  @property
  def isSysop(self):
    """Return True if 'sysop' in groups."""
    return 'sysop' in self.get('groups')

  @property
  def handle(self):
    """Nickname of caller and key of user in database."""
    return self._handle

  @handle.setter
  def handle(self, value):
    assert type(value) is unicode and len(value) > 0
    self._handle = value
    db[self.handle] = self #save


  @property
  def password(self):
    return self._password

  @password.setter
  def password(self, value):
    assert type(value) is unicode
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(value, salt)
    self._password = (salt, hashed)

  @property
  def lastcall(self):
    """Time last called in epoch seconds."""
    return self._lastcall

  @lastcall.setter
  def lastcall(self, value):
    assert type(value) in (int,float,)
    self._lastcall = value
    db[self.handle] = self #save


  @property
  def calls(self):
    """Legacy, number of times user has 'called' this board."""
    return self._calls

  @calls.setter
  def calls(self, value):
    assert type(value) is int
    self._calls = value
    db[self.handle] = self #save


  @property
  def location(self):
    """Legacy, used as a geographical location."""
    return self._location

  @location.setter
  def location(self, value):
    assert type(value) is unicode
    self._location = value #save


  @property
  def hint(self):
    """Legacy, used as an e-mail address."""
    return self._hint

  @hint.setter
  def hint(self, value):
    assert type(value) is unicode
    self._hint = value
    db[self.handle] = self #save


  @property
  def plan(self):
    """Legacy, like unix .plan; blogosphere, lol."""
    return self._plan

  @plan.setter
  def plan(self, value):
    assert type(value) is unicode
    self._plan = value

  def set (self, key, value):
    self[key] = value
    db[self.handle] = self # save

  def save(self):
    if 0 == len(listusers()) and not 'sysop' in self.groups:
      logger.warn ('first new user becomes sysop: %s', self.handle)
      self.groups = list(('sysop',))
    db[self.handle] = self

  def delete(self):
    del db[self.handle]
