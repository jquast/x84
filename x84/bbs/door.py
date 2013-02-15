"""
ansiwin package for x/84 BBS http://github.com/jquast/x84
"""
import termios
import logging
import select
import struct
import fcntl
import pty
import sys
import os


class Door(object):
    """
    Spawns a subprocess and pipes input and output over bbs session.
    """
    # pylint: disable=R0902,R0903
    #        Too many instance attributes (8/7)
    #        Too few public methods (1/2)
    time_ipoll = 0.05
    time_opoll = 0.05
    blocksize = 7680
    timeout = 1984
    master_fd = None
    decode_cp437 = False
    _TAP = False  # for debugging

    def __init__(self, cmd='/bin/uname', args=(), env_lang='en_US.UTF-8',
                 env_term=None, env_path=None, env_home=None):
        """
        cmd, args = argv[0], argv[1:]
        lang, term, and env_path become LANG, TERM, and PATH environment
        variables. when term is None, the session terminal type is used.  When
        env_path is None, the .ini 'env_path' value of section [door] is used.
        When env_home is None, $HOME of the main process is used.
        """
        from x84.bbs import getsession, ini
        # pylint: disable=R0913
        #        Too many arguments (7/5)
        self.cmd = cmd
        self.args = (self.cmd,) + args
        self.env_lang = env_lang
        if env_term is None:
            self.env_term = getsession().env.get('TERM')
        else:
            self.env_term = env_term
        if env_path is None:
            self.env_path = ini.CFG.get('door', 'path')
        else:
            self.env_path = env_path
        if env_home is None:
            self.env_home = os.getenv('HOME')
        else:
            self.env_home = env_home

    def run(self):
        """
        Begin door execution. pty.fork() is called, child process
        calls execvpe() while the parent process pipes telnet session
        IPC data to and from the slave pty until child process exits.
        """
        from x84.bbs import getsession, getterminal
        session, term = getsession(), getterminal()
        logger = logging.getLogger()
        try:
            pid, self.master_fd = pty.fork()
        except OSError, err:
            logger.error('OSError in pty.fork(): %s', err)
            return

        # subprocess
        if pid == pty.CHILD:
            sys.stdout.flush()
            env = {'LANG': self.env_lang,
                   'TERM': self.env_term,
                   'PATH': self.env_path,
                   'HOME': self.env_home,
                   'LINES': '%s' % (term.height,),
                   'COLUMNS': '%s' % (term.width,),
                   }
            try:
                os.execvpe(self.cmd, self.args, env)
            except OSError, err:
                logger.error('OSError, %s: %s', err, self.args,)
                sys.exit(1)

        # execute self._loop() and catch all i/o and o/s errors
        #
        # typically, return values from 'input' events are translated keycodes,
        # such as terminal.KEY_ENTER. However, when executing a sub-door, we
        # disable this by setting session.enable_keycodes = False
        swp = session.enable_keycodes
        session.enable_keycodes = False
        # input must be flushed of keycodes!
        readahead = u''.join([inp
                              for inp in session.flush_event('input')
                              if type(inp) is not int])
        if 0 != len(readahead):
            # place non-keycodes back in buffer %-&
            logger.debug('readahead, %r', readahead)
            session.buffer_event('input', readahead)
        try:
            logger.info('exec/%s: %s', pid, ' '.join(self.args))
            self._loop()
        except IOError, err:
            logger.error('IOError: %s', err)
        except OSError, err:
            # match occurs on read() after child closed sys.stdout. (ok)
            if 'Errno 5' not in str(err):
                # otherwise log as an error,
                logger.error('OSError: %s', err)
        session.enable_keycodes = swp
        (pid, status) = os.waitpid(pid, 0)
        res = status >> 8
        if res != 0:
            logger.error('%s child %s exit %d', self.cmd, pid, res)
        else:
            logger.debug('%s exit', self.cmd)
        os.close(self.master_fd)
        return res

    def _loop(self):
        """
        Poll input and outpout of ptys,
        """
        import codecs
        from x84.bbs import getsession, getterminal, echo
        from x84.bbs.cp437 import CP437
        session, term = getsession(), getterminal()
        utf8_decoder = codecs.getincrementaldecoder('utf8')()
        logger = logging.getLogger()
        while True:
            # block up to self.time_opoll for screen output
            rlist = (self.master_fd,)
            ret_tuple = select.select(rlist, (), (), self.time_opoll)
            if self.master_fd in ret_tuple[0]:
                data = os.read(self.master_fd, self.blocksize)
                if 0 == len(data):
                    break
                if self._TAP:
                    logger.debug('<-- %r', data)
                # output to terminal as utf8, unless we specify decode_cp437
                # for special dos-emulated doors such as lord.
                if self.decode_cp437:
                    echo(u''.join(
                        (CP437[ord(ch)] for ch in data)))
                else:
                    decoded = list()
                    def ready_master_fd():
                        """
                        returns True if bytes waiting on master fd, meaning
                        this utf8 byte must really be the last for a while.
                        """
                        return (self.master_fd in
                                select.select([self.master_fd,], (), (), 0)[0])
                    for num, byte in enumerate(data):
                        final = (num + 1) == len(data) and not ready_master_fd()
                        ucs = utf8_decoder.decode(byte, final)
                        if ucs is not None:
                            decoded.append(ucs)
                    echo(u''.join(decoded))



            # block up to self.time_ipoll for keyboard input
            event, data = session.read_events(
                ('refresh', 'input',), self.time_ipoll)
            if event == 'refresh':
                if data[0] == 'resize':
                    logger.debug('send TIOCSWINSZ: %dx%d',
                                 term.width, term.height)
                    fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
                                struct.pack('HHHH', term.height, term.width,
                                            0, 0))
            elif event == 'input':
                # hmm.. what to send, depending on TERM? interesting ..
                n_written = os.write(self.master_fd, data)
                if n_written == 0:
                    logger.warn('fight 0-byte write; exit, right?')
                elif self._TAP:
                    logger.debug('--> %r' % (data[:n_written],))
                if n_written != len(data):
                    # we wrote none or some of our keyboard input, but not all.
                    # re-buffer remaining bytes back into session for next poll
                    session.buffer_input(data[n_written:])
                    # haven't seen this yet, prove to me it works ..
                    logger.warn('buffer_input(%r)', data[n_written:])
