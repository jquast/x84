"""
ansiwin package for x/84 BBS http://github.com/jquast/x84
"""
import termios
import select
import logging
import struct
import fcntl
import pty
import sys
import os

import x84.bbs.exception
import x84.bbs.session
import x84.bbs.output
import x84.bbs.cp437
import x84.bbs.ini

#pylint: disable=C0103
#        Invalid name "logger" for type constant (should match
logger = logging.getLogger()

class Door(object):
    """
    Spawns a subprocess and pipes input and output over bbs session.
    """
    #pylint: disable=R0902,R0903
    #        Too many instance attributes (8/7)
    #        Too few public methods (1/2)
    time_ipoll = 0.05
    time_opoll = 0.05
    blocksize = 7680
    timeout = 1984
    master_fd = None
    decode_cp437 = False
    _TAP = False # for debugging

    def __init__(self, cmd='/bin/uname', args=(), env_lang=u'en_US.UTF-8',
            env_term=None, env_path=None, env_home=None):
        """
        cmd, args = argv[0], argv[1:]
        lang, term, and env_path become LANG, TERM, and PATH environment
        variables. when term is None, the session terminal type is used.  When
        env_path is None, the .ini 'env_path' value of section [door] is used.
        When env_home is None, $HOME of the main process is used.
        """
        #pylint: disable=R0913
        #        Too many arguments (7/5)
        self.cmd = cmd
        self.args = (self.cmd,) + args
        self.env_lang = env_lang
        if env_term is None:
            self.env_term = x84.bbs.session.getsession().env.get('TERM')
        else:
            self.env_term = env_term
        if env_path is None:
            self.env_path = x84.bbs.ini.CFG.get('door', 'path')
        else:
            self.env_path = env_path
        if env_home is None:
            self.env_home = env_home
        else:
            self.env_home = os.getenv('HOME')

    def run(self):
        """
        Begin door execution. pty.fork() is called, child process
        calls execvpe() while the parent process pipes telnet session
        IPC data to and from the slave pty until child process exits.
        """
        try:
            pid, self.master_fd = pty.fork()
        except OSError, err:
            logger.error ('OSError in pty.fork(): %s', err)
            return

        session = x84.bbs.session.getsession()
        term = x84.bbs.session.getterminal()
        # subprocess
        if pid == pty.CHILD:
            sys.stdout.flush ()
            env = { u'LANG': self.env_lang,
                    u'TERM': self.env_term,
                    u'PATH': self.env_path,
                    u'HOME': self.env_home,
                    u'LINES': '%s' % (term.height,),
                    u'COLUMNS': '%s' % (term.width,),
                  }
            try:
                os.execvpe(self.cmd, self.args, env)
            except OSError, err:
                logger.error ('OSError, %s: %s', err, self.args,)
                sys.exit (1)

        # execute self._loop() and catch all i/o and o/s errors
        #
        # typically, return values from 'input' events are translated keycodes,
        # such as terminal.KEY_ENTER. However, when executing a sub-door, we
        # disable this by setting session.enable_keycodes = False
        swp = session.enable_keycodes
        session.enable_keycodes = False
        try:
            logger.info ('exec/%s: %s', pid, ' '.join(self.args))
            self._loop()
        except IOError, err:
            logger.error ('IOError: %s', err)
        except OSError, err:
            # match occurs on read() after child closed sys.stdout. (ok)
            if 'Errno 5' not in str(err):
                # otherwise log as an error,
                logger.error ('OSError: %s', err)
        session.enable_keycodes = swp
        (pid, status) = os.waitpid (pid, 0)
        res = status >> 8
        if res != 0:
            logger.error ('%s child %s exit %d', self.cmd, pid, res)
        else:
            logger.info ('%s child %s exit 0', self.cmd, pid)
        os.close (self.master_fd)
        return res

    def _loop(self):
        """
        Poll input and outpout of ptys, raising exception.ConnectionTimeout
        when session idle time exceeds self.timeout.
        """
        term = x84.bbs.session.getterminal()
        while True:
            # block up to self.time_opoll for screen output
            rlist = (self.master_fd,)
            ret_tuple = select.select (rlist, (), (), self.time_opoll)
            if self.master_fd in ret_tuple[0]:
                data = os.read(self.master_fd, self.blocksize)
                if 0 == len(data):
                    break
                if self._TAP:
                    logger.debug ('<-- %r', data)
                # output to terminal as utf8, unless we specify decode_cp437
                # for special dos-emulated doors such as lord.
                x84.bbs.output.echo (u''.join(
                        (x84.bbs.cp437.CP437[ord(ch)] for ch in data)
                    ) if self.decode_cp437
                    else data.decode('utf8'))

            # block up to self.time_ipoll for keyboard input
            event, data = x84.bbs.session.getsession().read_events (
                    events=('refresh','input'), timeout=self.time_ipoll)
            if ((None, None) == (event, data)
                    and x84.bbs.session.getsession().idle > self.timeout):
                raise x84.bbs.exception.ConnectionTimeout (
                        'timeout in door %r', self.args,)
            elif event == 'refresh':
                if data[0] == 'resize':
                    logger.debug ('send TIOCSWINSZ: %dx%d',
                            term.width, term.height)
                    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
                            struct.pack('HHHH', term.height, term.width, 0, 0))
            elif event == 'input':
                if self._TAP:
                    logger.debug ('--> %r' % (data,))
                while 0 != len(data):
                    n_written = os.write(self.master_fd, data)
                    data = data[n_written:]
