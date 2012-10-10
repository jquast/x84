import termios
import select
import struct
import fcntl
import pty
import sys
import re
import os

PATTERN_EIO = re.compile('Errno 5')

class Door(object):
    POLL = 0.02
    BLOCKSIZE = 1920
    master_fd = None
    decode_cp437 = False
    pid = None
    _TAP = False # for debugging

    def __init__(self, cmd='/bin/uname', args=(),
        lang=u'en_US.UTF-8', term=None, path=None,
        decode_cp437=False):
        """
        cmd, args = argv[0], argv[1:]
        lang, term, and path become LANG, TERM, and PATH environment
        variables. when term is None, the session terminal type is used.
        When path is None, the .ini 'path' value of [door] is used.

        When decode_cp437 is True, the door is presumed to be in CP437
        encoding and high-bit characters are mapped to their utf8-equivalent
        glyph.
        """
        from session import getsession
        import ini
        self.cmd = cmd
        self.args = (self.cmd,) + args
        self.lang = lang
        self.term = term if term is not None else \
            getsession().terminal.terminal_type
        self.path = path if path is not None else \
            ini.cfg.get('door', 'path')
        self.decode_cp437 = True

    def run(self):
        from session import getsession, logger
        try:
            self.pid, self.master_fd = pty.fork()
        except OSError, err:
            logger.error ('OSError in pty.fork(): %s', err)
            return

        # subprocess
        if self.pid == pty.CHILD:
            sys.stdout.flush ()
            env = { u'LANG': self.lang,
                    u'TERM': self.term,
                    u'PATH': self.path,
                    u'HOME': os.getenv('HOME') }
            try:
                os.execvpe(self.cmd, self.args, env)
            except OSError, err:
                logger.error ('OSError, %s: %s', err, self.args,)
                sys.exit (1)

        # typically, return values from 'input' events are translated keycodes,
        # such as terminal.KEY_ENTER. However, when executing a sub-door, we
        # disable this by setting session.enable_keycodes = False
        chk_keycodes = getsession().enable_keycodes
        getsession().enable_keycodes = False

        # execute self._loop() and catch all i/o and o/s errors
        try:
            logger.info ('exec/%s: %s', self.pid, ' '.join(self.args))
            self._loop()
        except IOError, err:
            logger.error ('IOError: %s', err)
        except OSError, err:
            # match occurs on read() after child closed sys.stdout. (ok)
            if PATTERN_EIO.search (str(err)) is None:
                # otherwise log as an error,
                logger.error ('OSError: %s', e)

        getsession().enable_keycodes = chk_keycodes

        # retrieve return code
        (self.pid, status) = os.waitpid (self.pid, 0)
        res = status >> 8

        if res != 0:
            logger.warn ('child %s has non-zero exit code: %s',
                    self.pid, res)
        else:
            logger.info ('%s child %s exit %s.', self.cmd, self.pid, res)

        os.close (self.master_fd)
        return res

    def _loop(self):
        from session import getsession, logger
        from output import echo
        from cp437 import CP437

        # signal window size to child pty, untested XXX
        term = getsession().terminal
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
            struct.pack('HHHH', term.height, term.width, 0, 0))

        while True:
            #pylint: disable=W0612
            #        Unused variable 'wfds'
            #        Unused variable 'xfds'
            rlist = (self.master_fd,)
            # block up to self.POLL for screen output
            (rfds, wfds, xfds) = select.select (rlist, (), (), self.POLL)
            if self.master_fd in rfds:
                data = os.read(self.master_fd, self.BLOCKSIZE)
                if 0 == len(data):
                    logger.debug ('read 0 bytes from masterfd')
                    return
                if self._TAP:
                    logger.debug ('<-- %r', data)
                if self.decode_cp437:
                    echo (u''.join((CP437[ord(ch)] for ch in data)))
                else: # utf8 only supported here ...
                    echo (data.decode('utf8'))

            # self.POLL for keyboard input,
            event, data = getsession().read_event (('refresh','input'), self.POLL)
            if (None, None) == (event, data):
                continue # no input

            # handle resize event by propigating to ioctl to child pty
            if event == 'refresh':
                if data[0] == 'resize':
                    # XXX i haven't seen this work yet,
                    logger.debug ('send TIOCSWINSZ: %dx%d',
                            term.width, term.height)
                    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
                        struct.pack('HHHH',
                            int(term.height), int(term.width), 0, 0))
                continue

            if event == 'input':
                if self._TAP:
                    logger.debug ('--> %r' % (data,))

                while 0 != len(data):
                    n = os.write(self.master_fd, data)
                    data = data[n:]
                continue

            assert False, 'unhandled event, data: %s, %r' % (event, data,)
