"""
Door package for x/84 BBS http://github.com/jquast/x84
"""
import resource
import termios
import logging
import select
import codecs
import struct
import time
import fcntl
import pty
import sys
import os
import re

class Dropfile(object):
    (DOORSYS, DOOR32, CALLINFOBBS, DORINFO) = range(4)
    DOORSYS_GM = 'GR' # graphics mode

    def __init__(self, filetype=None):
        assert filetype in (self.DOORSYS, self.DOOR32,
                self.CALLINFOBBS, self.DORINFO)
        self.filetype = filetype

    def save(self, folder):
        """ Save dropfile to folder """
        fp = codecs.open(os.path.join(folder, self.filename), 'w', 'ascii', 'replace')
        fp.write(self.__str__())
        fp.close()

    @property
    def node(self):
        from x84.bbs import getsession
        return getsession().node

    @property
    def location(self):
        from x84.bbs import getsession
        return getsession().user.location

    @property
    def fullname(self):
        from x84.bbs import getsession
        return '%s %s' % (
                getsession().user.handle,
                getsession().user.handle,)

    @property
    def securitylevel(self):
        from x84.bbs import getsession
        return 100 if getsession().user.is_sysop else 30

    @property
    def numcalls(self):
        from x84.bbs import getsession
        return getsession().user.calls

    @property
    def lastcall_date(self):
        from x84.bbs import getsession
        return time.strftime('%m/%d/%y',
                time.localtime(getsession().user.lastcall))

    @property
    def lastcall_time(self):
        from x84.bbs import getsession
        return time.strftime('%H:%M',
                time.localtime(getsession().user.lastcall))

    @property
    def time_used(self):
        from x84.bbs import getsession
        return int(time.time() - getsession().connect_time)

    @property
    def remaining_secs(self):
        return 256 * 60

    @property
    def remaining_mins(self):
        return 256

    @property
    def comport(self):
        return 'COM1'

    @property
    def comspeed(self):
        return 57600

    @property
    def comtype(self):
        return 0 ## Line 1 : Comm type (0=local, 1=serial, 2=telnet)

    @property
    def comhandle(self):
        return 0 ## Line 2 : Comm or socket handle

    @property
    def parity(self):
        return 8

    @property
    def password(self):
        return '<encrypted>'

    @property
    def pageheight(self):
        from x84.bbs import getterminal
        return getterminal().height

    @property
    def systemname(self):
        from x84.bbs import ini
        return ini.CFG.get('system', 'software')

    @property
    def xferprotocol(self):
        return 'X' # x-modem for now, we don't have any xfer code/prefs

    @property
    def usernum(self):
        from x84.bbs import getsession
        from x84.bbs.userbase import list_users
        try:
            return list_users().index(getsession().user.handle)
        except ValueError:
            return 999

    @property
    def sysopname(self):
        from x84.bbs import ini
        return ini.CFG.get('system', 'sysop')

    @property
    def alias(self):
        from x84.bbs import getsession
        return getsession().user.handle

    @property
    def filename(self):
        if self.filetype == self.DOORSYS:
            return 'DOOR.SYS'
        elif self.filetype == self.DOOR32:
            return 'DOOR32.SYS'
        elif self.filetype == self.CALLINFOBBS:
            return 'CALLINFO.BBS'
        elif self.filetype == self.DORINFO:
            # n in DORINFOn.DEF is 1-9,0,a-z
            if self.node == 10:
                nodeid = '0'
            elif self.node < 10:
                nodeid = str(self.node)
            else:
                nodeid = chr(ord('a') + (self.node - 11))
                assert ord(nodeid) <= ord('z')
            return 'DORINFO%s.DEF' % (nodeid,)
        else:
            raise ValueError('filetype is unknown')

    def __str__(self):
        if self.filetype == self.DOORSYS:
            return self.get_doorsys()
        elif self.filetype == self.DOOR32:
            return self.get_door32()
        elif self.filetype == self.CALLINFOBBS:
            return self.get_callinfo()
        elif self.filetype == self.DORINFO:
            return self.get_dorinfo()
        else:
            raise ValueError('filetype is unknown')

    def get_doorsys(self):
        return (u'%s:\r\n%d\r\n'  # comport, comspeed
                '%d\r\n%d\r\n'  # parity, node
                '%d\r\nY\r\n'  # comspeed, screen?
                'Y\r\nY\r\nY\r\n'  # printer? pager alarm? caller alarm?
                '%s\r\n%s\r\n'  # fullname, location
                '123-456-7890\r\n123-456-7890\r\n'  # phone numbers
                '%s\r\n%d\r\n%d\r\n'  # password, security level, numcalls
                '%s\r\n%d\r\n%d\r\n'  # lastcall, remaining (secs, mins)
                'GR\r\n%d\r\nN\r\n'  # graphics mode, page length, expert mode
                '1,2,3,4,5,6,7\r\n1\r\n'  # conferences, conf. sel, exp. date
                '01/01/99\r\n'  # exp. date
                '%s\r\n%s\r\n'  # user number, def. xfer protocol,
                '0\r\n0\r\n'  # total #u/l, total #d/l
                '0\r\n9999999\r\n'  # daily d/l limit return val/write val
                '01/01/2001\r\n'  # birthdate
                'C:\\XXX\r\nC:\\XXX\r\n'  # filepaths to bbs files ...
                '%s\r\n%s\r\n'  # sysop's name, user's alias
                '00:05\r\nY\r\n'  # "event time"?, error-correcting connection
                'Y\r\nY\r\n'  # is ANSI in NG mode? Use record locking?
                '7\r\n%d\r\n'  # default color .. time credits in minutes
                '09/09/99\r\n%s\r\n'  # last new file scan, time of call,
                '%s\r\n9999\r\n'  # time of last call, max daily files
                '0\r\n0\r\n0\r\n' # files, u/l Kb, d/l Kb today
                'None\r\n0\r\n0\n' # user comment, doors opened, msgs left
                % (
                    self.comport, self.comspeed, self.parity, self.node,
                    self.comspeed, self.fullname, self.location,
                    self.password, self.securitylevel, self.numcalls,
                    self.lastcall_date, self.remaining_secs,
                    self.remaining_mins, self.pageheight, self.usernum,
                    self.xferprotocol, self.sysopname, self.alias,
                    self.remaining_mins, self.lastcall_time,
                    self.lastcall_time))

    def get_door32(self):
        return (u'%d\r\n%d\r\n%d\r\n'  # comm type, handle, speed
                '%s\r\n%d\r\n%s\r\n'  # system name, user num, real name
                '%s\r\n%d\r\n%d\r\n'  # alias, security level, mins remain,
                '1\r\n%d\n'  # emulation ('ansi'), current node num,
                % (
                    self.comtype, self.comhandle, self.comspeed,
                    self.systemname, self.usernum, self.fullname,
                    self.alias, self.securitylevel, self.remaining_mins,
                    self.node))
    def get_callinfo(self):
        return (u'%s\r\n%d\r\n%s\r\n'  # user name, comspeed, location
                '%d\r\n%d\r\nCOLOR\r\n' # security level, mins remain, ansi?
                '%s\r\n%d\r\n%d\r\n'  # password, usernum, time_used,
                '01:23\r\n01:23 01/02/90\r\n'
                'ABCDEFGH\r\n0\r\n'
                '99\r\n0\r\n'
                '9999\r\n'  # 7 unknown fields,
                '123-456-7890\r\n01/01/90 02:34\r\n' # phone, unknown
                'NOVICE\r\n%s\r\n'  # expert mode, xfer protocol
                '01/01/90\r\n%d\r\n' # unknown, number of calls,
                '%d\r\n0\r\n' # lines per screen, ptr to new msgs?
                '0\r\n0\r\n' # total u/l, d/l
                '8  { Databits }\r\n' #  who knows
                'REMOTE\r\n%s\r\n' # LOCAL|REMOTE, comport,
                '%d\r\nFALSE\r\n' # comspeed, unknown,
                'Normal Connection\r\n' # unknown,
                '01/02/94 01:20\r\n0\r\n1\n' # unknown, "task #", "door #"
                % (self.alias, self.comspeed, self.location,
                    self.securitylevel, self.remaining_mins, self.password,
                    self.usernum, self.time_used, self.xferprotocol,
                    self.numcalls, self.pageheight, self.comport, self.comspeed, ))

    def get_dorinfo(self):
        return (u'%s\r\n%s\r\n%s\r\n' # software, sysop fname, sysop lname,
                '%s\r\n%d\r\n0\r\n'  # com port, bps, "networked"?
                '%s\r\n%s\r\n%s\r\n' # user fname, user lname, user location
                '1\r\n%d\r\n%d\r\n' # term (ansi), security level, mins remain
                '-1\n'  # fossil (-1 = "using external serial driver"..)
                % (
                    self.systemname, self.sysopname, self.sysopname,
                    self.comport, self.comspeed,
                    self.alias, self.alias, self.location,
                    self.securitylevel, self.remaining_mins,))


class Door(object):
    """
    Spawns a subprocess and pipes input and output over bbs session.
    """
    # pylint: disable=R0903
    #        Too few public methods (1/2)
    time_ipoll = 0.05
    time_opoll = 0.05
    blocksize = 7680
    timeout = 1984
    master_fd = None

    def __init__(self, cmd='/bin/uname', args=(), env_lang='en_US.UTF-8',
                 env_term=None, env_path=None, env_home=None, cp437=False):
        # pylint: disable=R0913
        #        Too many arguments (7/5)
        """
        cmd, args = argv[0], argv[1:]
        lang, term, and env_path become LANG, TERM, and PATH environment
        variables. When env_term is None, the session terminal type is used.
        When env_path is None, the .ini 'env_path' value of section [door] is
        used.  When env_home is None, $HOME of the main process is used.
        """
        from x84.bbs import getsession, getterminal, ini
        self._session, self._term = getsession(), getterminal()
        # pylint: disable=R0913
        #        Too many arguments (7/5)
        self.cmd = cmd
        if type(args) is tuple:
            self.args = (self.cmd,) + args
        elif type(args) is list:
            self.args = [self.cmd,] + args
        else:
            raise ValueError, 'args must be tuple or list'
        self.env_lang = env_lang
        if env_term is None:
            self.env_term = self._session.env.get('TERM')
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
        self.env = None # add additional env variables ...
        self.cp437 = cp437
        self._utf8_decoder = codecs.getincrementaldecoder('utf8')()

    def run(self):
        """
        Begin door execution. pty.fork() is called, child process
        calls execvpe() while the parent process pipes telnet session
        IPC data to and from the slave pty until child process exits.
        """
        logger = logging.getLogger()
        env = dict() if self.env is None else self.env
        env.update({'LANG': self.env_lang,
               'TERM': self.env_term,
               'PATH': self.env_path,
               'HOME': self.env_home,
               'LINES': '%s' % (self._term.height,),
               'COLUMNS': '%s' % (self._term.width,)})
        logger.debug('os.execvpe(cmd=%r, args=%r, env=%r',
                self.cmd, self.args, env)
        try:
            pid, self.master_fd = pty.fork()
        except OSError, err:
            # too many open files, out of memory, no such file/directory
            logger.error('OSError in pty.fork(): %s', err)
            return

        # child process
        if pid == pty.CHILD:
            sys.stdout.flush()
            # send initial screen size
            fcntl.ioctl(sys.stdout.fileno(), termios.TIOCSWINSZ,
                        struct.pack('HHHH',
                            self._term.height, self._term.width, 0, 0))
            # we cannot log an exception, only print to stderr and have
            # it captured by the parent process; this is because our 'logger'
            # instance is dangerously forked, and any attempt to communicate
            # with multiprocessing pipes, loggers, etc. will cause the value
            # and state of many various file descriptors to become corrupted
            try:
                os.execvpe(self.cmd, self.args, env)
            except Exception as err:
                sys.stderr.write('%s\n' % (err,))
            os._exit(1)

        # parent process
        #
        # execute self._loop() and catch all i/o and o/s errors
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
        (pid, status) = os.waitpid(pid, 0)
        res = status >> 8
        if res != 0:
            logger.error('%s child %s exit %d', self.cmd, pid, res)
        else:
            logger.debug('%s exit', self.cmd)
        os.close(self.master_fd)
        return res

    def input_filter(self, data):
        """ When keyboard input is detected, this method may filter such input.
        """
        return data

    def output_filter(self, data):
        """ Given door output in bytes, if 'cp437' is specified in class
        constructor, convert to utf8 glyphs using cp437 encoding; otherwise
        decode output as utf8. """
        from x84.bbs.cp437 import CP437
        
        if self.cp437:
            return u''.join((CP437[ord(ch)] for ch in data))

        decoded = list()
        for num, byte in enumerate(data):
            final = ((num + 1) == len(data)
                     and not self._masterfd_isready())
            ucs = self._utf8_decoder.decode(byte, final)
            if ucs is not None:
                decoded.append(ucs)
        return u''.join(decoded)

    def _masterfd_isready(self):
        """
        returns True if bytes waiting on master fd, meaning
        this utf8 byte must really be the last for a while.
        """
        return self.master_fd != -1 and (self.master_fd in
                select.select([self.master_fd, ], (), (), 0)[0])

    def resize(self):
        logger = logging.getLogger()
        logger.debug('send TIOCSWINSZ: %dx%d',
                     self._term.width, self._term.height)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ,
                    struct.pack('HHHH',
                        self._term.height, self._term.width, 0, 0))

    def _loop(self):
        # pylint: disable=R0914
        #         Too many local variables (21/15)
        """
        Poll input and outpout of ptys,
        """
        from x84.bbs import echo
        from x84.bbs.cp437 import CP437
        logger = logging.getLogger()
        while True:
            # block up to self.time_opoll for screen output
            if self.master_fd == -1:
                # pty file descriptor closed by child, early termination!
                break
            rlist = (self.master_fd,)
            ret_tuple = select.select(rlist, (), (), self.time_opoll)
            if self.master_fd in ret_tuple[0]:
                data = os.read(self.master_fd, self.blocksize)
                if 0 == len(data):
                    break
                echo(self.output_filter(data))

            # block up to self.time_ipoll for keyboard input
            event, data = self._session.read_events(
                ('refresh', 'input',), self.time_ipoll)

            if event == 'refresh' and data[0] == 'resize':
                self.resize()

            elif event == 'input':
                data = self.input_filter(data)
                if 0 != len(data):
                    n_written = os.write(self.master_fd, data)
                    if n_written == 0:
                        logger.warn('fight 0-byte write; exit, right?')
                    if n_written != len(data):
                        # we wrote none or some of our keyboard input, but
                        # not all. re-buffer remaining bytes back into
                        # session for next poll
                        self._session.buffer_input(data[n_written:])
                        # XXX I've never actually seen this, though. It might
                        # require writing a sub-program that artificially
                        # hangs, such as time.sleep(99999) to assert correct
                        # behavior. Please report, should be ok ..
                        logger.warn('buffer_input(%r)!', data[n_written:])

class DOSDoor(Door):
    """ This Door-derived class removes the "report cursor position" query
    sequence, which is sent by DOSEMU on startup. It also removes the "switch
    to alternate screen mode" set and reset (blessings terminals provide this
    with the context manager, ala "with term.fullscreen():".

    It would appear that any early keyboard input received (esp. in response
    to "report cursor position") prior to DOOR execution in DOSEMU causes all
    input to be bitshifted and invalid and/or broken.

    This class should resolve such issues by ovveriding output_filter to
    remove such sequence, and input_filter which only allows input after a
    few seconds have passed.
    """
    RE_REPWITH_CLEAR = (
            r'\033\[('
                r'1;80H.*\033\[1;1H'
                r'|H\033\[2J'
                r'|\d+;1H.*\033\[1;1H'
                r')')
    RE_REPWITH_NONE = (
            r'\033\[('
            r'6n'
            r'|\?1049[lh]'
            r'|\d+;\d+r'
            r'|1;1H\033\[\dM)')
    START_BLOCK = 4.0

    def __init__(self, cmd='/bin/uname', args=(), env_lang='en_US.UTF-8',
                 env_term=None, env_path=None, env_home=None, cp437=False):
        Door.__init__(self, cmd, args,
                env_lang, env_term, env_path, env_home, cp437)
        self.check_winsize()
        self._stime = time.time()
        self._re_trim_clear = re.compile(self.RE_REPWITH_CLEAR, flags=re.DOTALL)
        self._re_trim_none = re.compile(self.RE_REPWITH_NONE, flags=re.DOTALL)
        self._replace_clear = (
                self._term.move(25, 0)
                + (u'\r\n' * 25)
                + self._term.home)

    def output_filter(self, data):
        data = Door.output_filter(self, data)
        if self._stime is not None and (
                time.time() - self._stime < self.START_BLOCK):
            data = re.sub(pattern=self._re_trim_clear,
                    repl=(self._replace_clear), string=data)
            data = re.sub(pattern=self._re_trim_none,
                    repl=u'\r\n', string=data)
        return data

    def input_filter(self, data):
        return data if time.time() - self._stime > self.START_BLOCK else ''

    def check_winsize(self):
        assert self._term.width >= 80, (
                'Terminal width must be greater than '
                '80 columns (IBM-PC dimensions). '
                'Please resize your window.')
        assert self._term.height >= 25, (
                'Terminal height must be greater than '
                '25 rows (IBM-PC dimensions). '
                'Please resize your window.')

    def resize(self):
        pass

    def run(self):
        """
        Begin door execution. pty.fork() is called, child process
        calls execvpe() while the parent process pipes telnet session
        IPC data to and from the slave pty until child process exits.

        On exit, DOSDoor flushes any keyboard input; DOSEMU appears to
        send various terminal reset sequences that may cause a reply to
        be received on input, and later as an invalid menu command.
        """
        from x84.bbs import echo
        echo(u'\r\n' * self._term.height)
        Door.run(self)

        # flush any previously decoded but unreceived keystrokes,
        # and any unprocessed input from telnet session not yet processed.
        self._term.kbflush()
        self._session.flush_event('input')

        # perform lossless "cls" after dosemu exit; display is garbage
        echo(self._term.normal + u'\r\n' * self._term.height)
        # also, fight against 'set scrolling region' by resetting, LORD
        # contains, for example: \x1b[3;22r after 'E'nter the realm :-(
        echo(u"\x1b[r")
