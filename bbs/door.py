import pty
import re
import os
import select
import tty

from output import echo
from input import getch, sendch
from session import logger

class Door(object):
  POLL = 0.15
  BLOCKSIZE = 1920
  master_fd = None
  pEIO = re.compile('[eE]rrno 5')

  def __init__(self, cmd='/bin/uname', args=()):
    self.cmd = cmd
    self.args = (self.cmd,) + args

  def run(self):
    assert self.master_fd is None
    pid, master_fd = pty.fork()
    self.master_fd = master_fd
    if pid == pty.CHILD:
      os.execlp(self.cmd, *self.args)
    try:
      logger.info ('launched : %s %s' % (self.cmd, self.args,))
      self._loop()
    except IOError, e:
      logger.error ('IOError: %s', e)
    except OSError, e:
      if self.pEIO.search (str(e)) != None:
        logger.info ('stdout closed by child')
        return
      logger.error ('OSError: %s', e)
    os.close(master_fd)
    self.master_fd = None

  def _loop(self):
    while True:
      # block up to self.POLL for screen output
      try:
        rfds, wfds, xfds = select.select([self.master_fd,],[],[], self.POLL)
      except select.error, e:
        if e[0] == 4:
          print 'syscall?'
          continue # log

      if self.master_fd in rfds:
        data = os.read(self.master_fd, self.BLOCKSIZE)
        echo (data)

      # block up to self.POLL for keyboard input
      data = getch(self.POLL)
      if data is None:
        continue
      if type(data) is int:
        data = sendch (data)
      while 0 != len(data):
        n = os.write(self.master_fd, data)
        data = data[n:]
