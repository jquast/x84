"""
 Message base for 'The Progressive' BBS.
 Copyright (c) 2007 Jeffrey Quast
 $Id: userbase.py,v 1.28 2010/01/02 00:39:33 dingo Exp $
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast', \
                 'Copyright (C) 2005 Johannes Lundberg']
__license__ = 'ISC'

import db, persistent
import time

def finduser(find):
  " return proper case for handles matched case insensitively "
  for handle in db.users.keys():
    if handle and handle.lower()==find.lower():
      # return match
      return handle
  # return null (fail)
  return None

def userexist(handle):
  " return True if user exists "
  return db.users.has_key(handle)

def authuser(handle, try_pass):
  """
    Return True if user by key of handle exists, has a password, and
    that password matches the try_pass argument. Setting the password
    to None effectively disables authentication of an account.
  """
  h=finduser(handle)
  return h and db.users[h].password \
    and try_pass == db.users[h].password

def getuser(handle):
  " return user record, retrieved by handle, return None if not found "
  if db.users.has_key(handle):
    return db.users[handle]
  return None

def listusers(allUsers=False):
  """
  return list of user record instances by iterating over all handle keys,
  users without a password are discluded unless allUsers is set to True.
  """
  return [db.users[h] for h in db.users.keys() if allUsers or db.users[h].password]

def listgroups():
  " return list of all groups on active accounts "
  groups = []
  for user in listusers():
    for group in user.groups:
      if group not in groups:
        groups.append (group)
  return groups

def groupmembers():
  " return dict of groups containing list of members "
  groups = {}
  for group in listgroups():
    groups[group] = []
  for user in listusers():
##IF 0 (transitionary)
#    if user.__dict__.has_key('groups'):
##ENDIF
      for group in user.groups:
        groups[group].append (user.handle)
  return groups

def membersofgroup(group):
  " return list of users found in group by name "
  groups = groupmembers()
  if groups.has_key(group):
    return groups[group]
  return None

class User(persistent.Persistent):
  " instance for fresh database record "
  handle = 'undefined'
  calls = 0
  lastcall = 0
  groups = []
  location = ''
  hint = ''
  saved = False
  postrefs = []
  pubkey = None
  password = None
  plan = ''

  def __init__ (self):
    self.creationtime = time.time()

  @db.locker
  def set (self, key, value):
    db.users[self.handle].__setattr__ (key, value)

  def get(self, key):
    return db.users[self.handle].__dict__[key]

  def has_key(self, key):
    return db.users[self.handle].__dict__.has_key(key)

  def keys(self):
    return db.users[self.handle].__dict__.keys()

  @db.locker
  def add(self):
    " commit this User instance as new record in the database."
    # First new user is added to sysop group.
    if not len(listusers(allUsers=True)) and not 'sysop' in self.groups:
      print 'userbase: first new user', self.handle, 'becomes sysop.'
      self.groups.append ('sysop')
    if db.users.has_key(self.handle):
      print "userbase.py: obliterating old user record for '" + self.handle + "'!"
    db.users[self.handle] = self

  @db.locker
  def delete(self):
    " delete a user from the database "
    del db.users[self.handle]

  @db.locker
  def addgroup (self, group):
    " place user in a group (string), return False if user is already in group"
    if not group in db.users[self.handle].groups:
      db.users[self.handle].groups.append (group)
      return True

  @db.locker
  def delgroup (self, group):
    " remove user from group, return False if user was not in group "
    if group in self.groups:
      db.users[self.handle].groups.remove (group)
      return True

  def posts(self):
    " return list of message indicies user has posted "
    return self.postrefs

  def numPosts(self):
    " return number of messages user has posted "
    return len(self.postrefs)

  @db.locker
  def post(self, msg_index):
    " register a post by user "
    if not type(msg_index) == type(int):
      raise ValueError, "msg_index must be an integer msg.number"
    self.postrefs.append (msg_index)


