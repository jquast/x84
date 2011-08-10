"""
Local terminal handler for linux virtual consoles.
Copyright (C) 2005 Johannes Lundberg
$Id: local.py,v 1.9 2010/01/01 09:29:48 dingo Exp $
"""

import fcntl
import termios
import signal
import struct
import os
import tty
from select import select
import ansi
import log

from terminal import Terminal

class LocalTerminal (Terminal):
  active = False
  def __init__ (self, ttyname=None, init_script=None):
    self.type = 'local'
    self.init_script = init_script
    if not ttyname:
      log.write ('terminal','warning: no terminal name defined for LocalTerminal')
      ttyname = '/dev/tty'
    self.info = '%s:%s' % (ttyname.split('/')[-1], init_script)
    # open terminal device
    self.file = open(ttyname,'r+b', 0)
    # set raw mode (input is immediate read)
    tty.setraw (self.file)
    # Canonical and no echo (?XXX)
    l = tty.tcgetattr (self.file.fileno())
    l[3] = l[3] & ~tty.TCSAFLUSH
    tty.tcsetattr (self.file.fileno(), tty.TCSANOW, l)

    # Initialize the Terminal generic
    Terminal.__init__(self)

    # on initialize, call the functional equivalent
    # of RemoteTerminal::connectionMade
    self.banner ()

  def banner(self):
    self.file.write (ansi.charset() + ' ' \
                   + ansi.linewrap() + ' ' \
                   + ansi.color() + ' ' \
                   + ansi.cursor_show() + ' ' \
                   + ansi.cls())

    # for local terminals, we still require authentication
    # unless an alternate init_script is used, such as it is
    # for the WFC terminal
    Terminal.addsession (self, user=None, scriptname=self.init_script)

  def close (self):
    # yes, our session has ended, so re-start from zero with self.banner
    # (XXX causes crashloop if addsession fails, needs a PAK prompt)
    self.banner()

  def fileno(self):
    " we must provide our file id to the twisted layer "
    return self.file.fileno()

  def logPrefix (self):
    " we must also provide a logPrefix method to the twisted layer "
    return 'LocalTerminal (%s)' % (self.info,)

  def doRead (self):
    input, data, timeout = self.file, '', .01
    while input:
      data += self.file.read(1)
      input, b, c = select([self.file], [], [], timeout)
    Terminal.handleinput(self, data)
#
#    if not self.active:
#      # BEGIN client session!
#      self.active = True
#    else:
#      data = self.file.read()

  def write (self, data):
    self.file.write (data)
