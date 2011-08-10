"""
Custom exception classes for 'The Progressive' BBS.
Copyright (C) 2005 Johannes Lundberg.
$Id: exception.py,v 1.4 2008/06/08 22:17:15 dingo Exp $
"""

class MyException (Exception):
  def __init__ (self, value):
   self.value = value
  def __str__ (self):
   return str(self.value)

class Disconnect (MyException):
  "Raised when the bbs closes a connection"

class ConnectionClosed (MyException):
  "Raised when the client closes connection"

class SilentTermination (MyException):
  "Raised to silently terminate a session"

class ScriptChange (MyException):
  "Raised whenever a script wants to travel&exchange itself to another"

class ScriptError (MyException):
  "Raised by runscript when there is an error running the script"
