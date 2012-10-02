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
  _TAP = False # for debugging

  def __init__(self, cmd='/bin/uname', args=(), lang=u'en_US.UTF-8', term=None,
      path=None):
    from session import getsession
    import ini
    self.cmd = cmd
    self.args = (self.cmd,) + args
    self.lang = lang
    self.term = term if term is not None else \
        getsession().terminal.terminal_type
    self.path = path if path is not None else \
        ini.cfg.get('session', 'door_syspath')

  def run(self):
    from session import getsession, logger
    try:
      self.pid, self.master_fd = pty.fork()
    except OSError, e:
      logger.error ('OSError in pty.fork(): %s', e,)
      return

    # subprocess
    if self.pid == pty.CHILD:
      sys.stdout.flush ()
      args = list(self.args)
      env = {
          u'LANG': self.lang,
          u'TERM': self.term,
          u'PATH': self.path,
          u'HOME': os.getenv('HOME') }
      os.execvpe(self.cmd, self.args, env)

    # typically, return values from 'input' events are translated keycodes,
    # such as terminal.KEY_ENTER. However, when executing a sub-door, we
    # disable this by setting session.enable_keycodes = False
    chk_keycodes = getsession().enable_keycodes
    getsession().enable_keycodes = False

    # execute self._loop() and catch all i/o and o/s errors
    try:
      logger.info ('exec/%s: %s' % (self.pid, ' '.join(self.args)))
      self._loop()
    except IOError, e:
      logger.error ('IOError: %s', e)
    except OSError, e:
      if self.pEIO.search (str(e)) != None:
        # this occurs on read() after child closed sys.stdout
        logger.debug ('(eof) OSError: %s', e)
      else:
        logger.error ('OSError: %s', e)

    getsession().enable_keycodes = True

    # retrieve return code
    (self.pid, status) = os.waitpid (self.pid, 0)
    res = status >> 8
    if res != 0:
      logger.warn ('child %s has non-zero exit code: %s' % (self.pid, res,))
    else:
      logger.info ('child %s exit %s.' % (self.pid, res,))
    os.close (self.master_fd)
    return res

  def _loop(self):
    from session import getsession, logger
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
        if self._TAP:
          logger.debug ('<-- %r', data)
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
        #assert 0 != len(data)
        if self._TAP:
          logger.debug ('--> %r' % (data,))

        # XXX blocking write loop for non-blocking i/o..
        # could be rather cpu consuming ..
        while 0 != len(data):
          n = os.write(self.master_fd, data)
          data = data[n:]
        continue

      assert 0, 'unhandled event, data: %s, %r' %(event, data,)
