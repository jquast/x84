"""
Custom exception classes for 'The Progressive' BBS.
Copyright (C) 2005 Johannes Lundberg.
$Id: exception.py,v 1.4 2008/06/08 22:17:15 dingo Exp $
"""

class Disconnect(Exception):
  "Raised when the bbs closes a connection"
  pass

class ConnectionClosed (Exception):
  "Raised when the client closes connection"
  pass

class SilentTermination (Exception):
  "Raised to silently terminate a session"
  pass

class ScriptChange (Exception):
  "Raised whenever a script wants to travel&exchange itself to another"
  pass

class ScriptError (Exception):
  "Raised by runscript when there is an error running the script"
  pass
