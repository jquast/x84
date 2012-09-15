import termios
import select
import struct
import fcntl
import pty
import sys
import re
import os

class Door(object):
  POLL = 0.15
  BLOCKSIZE = 1920
  master_fd = None
  pid = None
  pEIO = re.compile('[eE]rrno 5')

  def __init__(self, cmd='/bin/uname', args=(), lang='en_US.UTF-8', term=None):
    from session import getsession
    self.cmd = cmd
    self.args = (self.cmd,) + args
    self.lang = lang
    self.term = term if term is not None else \
        getsession().terminal.terminal_type

  def run(self):
    from session import logger
    try:
      self.pid, self.master_fd = pty.fork()
    except OSError, e:
      logger.error ('OSError in pty.fork(): %s', e,)
      return

    if self.pid == pty.CHILD:
      sys.stdout.flush ()
      os.execle(self.cmd, self.args, \
          (('LANG', self.lang,),
           ('TERM', self.term,),))

    # catch all i/o and o/s errors
    try:
      logger.info ('exec/%s: %s %s' % (self.pid, self.cmd, self.args,))
      self._loop()
    except IOError, e:
      logger.error ('IOError: %s', e)
    except OSError, e:
      if self.pEIO.search (str(e)) != None:
        # this occurs on read() when child closed sys.stdout
        logger.debug ('(eof) OSError: %s', e)
      else:
        logger.error ('OSError: %s', e)

    # retrieve return code
    (self.pid, status) = os.waitpid (self.pid, 0)
    res = status >> 8
    if res != 0:
      logger.warn ('child %s has non-zero exit code: %s' % (self.pid, res,))
    else:
      logger.info ('child %s exit %s.' % (self.pid, res,))
    os.close (self.master_fd)

  def _loop(self):
    from session import getsession, logger
    from input import getch, sendch
    from output import echo

    # signal window size to child pty, untested XXX
    term = getsession().terminal
    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
        struct.pack('HHHH', term.height, term.width, 0, 0))

    while True:
      # block up to self.POLL for screen output
      rfds, wfds, xfds = select.select([self.master_fd,],[],[], self.POLL)
      if self.master_fd in rfds:
        data = os.read(self.master_fd, self.BLOCKSIZE)
        if 0 == len(data):
          return
        echo (data, encoding='utf-8')

      # then, block up to self.POLL for keyboard input,
      event, data = getsession().read_event (('refresh','input'), self.POLL)
      if (None, None) == (event, data):
        continue

      # handle resize event by propigating to ioctl to child pty
      if event == 'refresh':
        if data[0] == 'resize':
          logger.debug ('send TIOCSWINSZ: %dx%d', term.width, term.height)
          fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
              struct.pack('HHHH', int(term.height), int(term.width), 0, 0))
        continue

      if event == 'input':
        if type(data) is int:
          # translate curses keycodes into a byte sequence that
          # is equivalent to our terminal setting
          data = sendch (data)
        assert 0 != len(data)
        while 0 != len(data):
          n = os.write(self.master_fd, data)
          data = data[n:]
        continue

      assert 0, 'unhandled event, data: %s, %r' %(event, data,)
