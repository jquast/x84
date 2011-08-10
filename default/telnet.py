"""
telnet client for X/84, http://1984.ws
$Id: telnet.py,v 1.1 2010/01/02 07:34:43 dingo Exp $

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2010 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']
import telnetlib

def main(host, port=None):
  port = port and port or 23
  session = getsession()
  session.activity = 'telneting to %s' % (host,)
  telnet = telnetlib.Telnet()
  echo (cls())
  echo ('\r\nTrying %s...' % (host,))
  try:
    telnet.open (host, port)
  except:
    type, value, tb = sys.exc_info ()
    echo ('\r\n%s%s' % (color(*LIGHTRED), value))
    echo ('\r\n%s%s' % (color(), 'press any key'))
    readkey()
    return
  echo ('\r\nConnected to %s.' % (host,))
  echo ("\r\nEscape character is '^].'")
  readkey (1)
  while True:
    ch = readkey (timeout=0.01)
    try:
      echo (telnet.read_very_eager())
      if ch == '\035':
        # XXX implement a command set? ..
        telnet.close()
        echo ('\r\n%sConnection closed.' % (cl()+color(),))
      elif ch:
        telnet.write(ch)
    except:
      type, value, tb = sys.exc_info ()
      echo (color() + cl())
      echo ('\r\n%s%s' % (cl()+color(*LIGHTRED), value))
      break
  echo ('\r\n%s%s' % (cl()+color(), 'press any key'))
  readkey ()
