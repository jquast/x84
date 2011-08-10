"""
Current Session and User instances for 'The Progressive' BBS.
Copyright (C) 2005 Johannes Lundberg
$Id: session.py,v 1.3 2008/06/08 22:17:15 dingo Exp $
"""

import engine
import thread

class CurrentSession:
  " Return caller's session"
  def __call__ (self):
    return engine.getsession()
  def __setattr__ (self, key, value):
    setattr (engine.getsession(), key, value)
  def __getattr__ (self, key):
    return getattr (engine.getsession(), key)

session = CurrentSession()

class CurrentUser:
  " Return caller's session.user"
  def __call__ ():
    return session.user
  def __setattr__ (self, key, value):
    setattr(session.user,key,value)
  def __getattr__ (self, key):
    return getattr (session.user, key)

user = CurrentUser()

