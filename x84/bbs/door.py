"""
Door package for x/84.

This implements the concept of "Doors", popular for DOS BBS software.

It also supports executing external Unix paths. See wikipedia article
for details: http://en.wikipedia.org/wiki/BBS_door
"""

# std imports
import logging
import select
import codecs
import struct
import shlex
import time
import sys
import os
import re

# local imports
from x84.bbs.session import getsession, getterminal
from x84.bbs.output import echo
from x84.bbs.ini import get_ini
from x84.bbs.userbase import list_users


class Dropfile(object):

    """
    Dropfile export class.

    From http://en.wikipedia.org/wiki/BBS_door

    > the 1990s on, most BBS software had the capability to "drop to" doors.
    > Several standards were developed for passing connection and user
    > information to doors; this was usually done with "dropfiles", small binary
    > or text files dropped into known locations in the BBS's file system.
    """

    #: Dropfile type constants
    (DOORSYS, DOOR32, CALLINFOBBS, DORINFO) = range(4)

    def __init__(self, filetype=None):
        """
        Class constructor.

        :param filetype: dropfile type. One of ``Dropfile.DOORSYS``,
                         ``Dropfile.DOOR32``, ``Dropfile.CALLINFOBBS``,
                         or ``Dropfile.DORINFO``.
        :type filetype: int
        """
        assert filetype in (self.DOORSYS, self.DOOR32,
                            self.CALLINFOBBS, self.DORINFO)
        self.filetype = filetype

    def save(self, folder):
        """ Save dropfile to destination ``folder`` """
        f_path = os.path.join(folder, self.filename)
        with codecs.open(f_path, 'w', 'ascii', 'replace') as out_p:
            out_p.write(self.__str__())

    @property
    def node(self):
        """ User's node number. """
        return getsession().node

    @property
    def location(self):
        """ User location. """
        return getsession().user.location

    @property
    def fullname(self):
        """ User fullname. Returns ``<handle> <handle>``. """
        return '%s %s' % (
            getsession().user.handle,
            getsession().user.handle,)

    @property
    def securitylevel(self):
        """ User security level. Always 30, or 100 for sysop. """
        return 100 if getsession().user.is_sysop else 30

    @property
    def numcalls(self):
        """ Number of calls by user. """
        return getsession().user.calls

    @property
    def lastcall_date(self):
        """ Date of last call (format is ``%m/%d/%y``). """
        return time.strftime(
            '%m/%d/%y', time.localtime(getsession().user.lastcall))

    @property
    def lastcall_time(self):
        """ Time of last call (format is ``%H:%M``). """
        return time.strftime(
            '%H:%M', time.localtime(getsession().user.lastcall))

    @property
    def time_used(self):
        """ Time used (session duration) in seconds. """
        return int(time.time() - getsession().connect_time)

    @property
    def remaining_secs(self):
        """ Remaining seconds (always returns ``15360``). """
        return 256 * 60

    @property
    def remaining_mins(self):
        """ Remaining minutes (always returns ``256``). """
        return 256

    @property
    def comport(self):
        """ Com port (always returns ``COM1``). """
        return 'COM1'

    @property
    def comspeed(self):
        """ Com speed (always returns ``57600``). """
        return 57600

    @property
    def comtype(self):
        """ Com type (always returns ``0``). """
        return 0  # Line 1 : Comm type (0=local, 1=serial, 2=telnet)

    @property
    def comhandle(self):
        """ Com handle (always returns ``0``). """
        return 0  # Line 2 : Comm or socket handle

    @property
    def parity(self):
        """ Data parity. """
        return 8

    @property
    def password(self):
        """ Password of user. """
        return '<encrypted>'

    @property
    def pageheight(self):
        """ Terminal height. """
        return getterminal().height

    @property
    def systemname(self):
        """ BBS System name. """
        return get_ini('system', 'software') or 'x/84'

    @property
    def xferprotocol(self):
        """ preferred transfer protocol. """
        return 'X'  # x-modem for now, we don't have any xfer code/prefs

    @property
    def usernum(self):
        """ User record number. """
        try:
            return list_users().index(getsession().user.handle)
        except ValueError:
            return 999

    @property
    def sysopname(self):
        """ name of sysop. """
        return get_ini('system', 'sysop') or u''

    @property
    def alias(self):
        """ current session's handle. """
        return getsession().user.handle

    @property
    def filename(self):
        """ Filename of given dropfile. """
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
            return 'DORINFO{0}.DEF'.format(nodeid)
        else:
            raise ValueError('filetype is unknown')

    def __str__(self):
        """ Returns dropfile content. """
        method = {
            self.DOORSYS: self._get_doorsys,
            self.DOOR32: self._get_door32,
            self.CALLINFOBBS: self._get_callinfo,
            self.DORINFO: self._get_dorinfo,
        }.get(self.filetype, None)
        if method is None:
            raise ValueError('unknown dropfile filetype: {self.filetype}'
                             .format(self=self))
        return method()

    def _get_doorsys(self):
        """ Return door.sys-formatted dropfile content. """
        return (u'{s.comport}:\r\n'
                u'{s.comspeed}\r\n'
                u'{s.parity}\r\n'
                u'{s.node}\r\n'
                u'{s.comspeed}\r\n'
                u'Y\r\n'                  # screen?
                u'Y\r\n'                  # printer?
                u'Y\r\n'                  # pager alarm?
                u'Y\r\n'                  # caller alartm?
                u'{s.fullname}\r\n'
                u'{s.location}\r\n'
                u'123-456-7890\r\n'       # phone number1
                u'123-456-7890\r\n'       # phone number2
                u'{s.password}\r\n'
                u'{s.securitylevel}\r\n'
                u'{s.numcalls}\r\n'
                u'{s.lastcall_date}\r\n'
                u'{s.remaining_secs}\r\n'
                u'{s.remaining_mins}\r\n'
                u'GR\r\n'                 # graphics mode
                u'{s.pageheight}\r\n'
                u'N\r\n'                  # expert mode?
                u'1,2,3,4,5,6,7\r\n'      # conferences
                u'1\r\n'                  # conf. sel, exp. date
                u'01/01/99\r\n'           # exp. date
                u'{s.usernum}\r\n'
                u'{s.xferprotocol}\r\n'
                u'0\r\n'                  # total num. uploads
                u'0\r\n'                  # total num, downloads
                u'0\r\n'                  # daily d/l limit
                u'9999999\r\n'            # return val/write val
                u'01/01/2001\r\n'         # birthdate
                u'C:\\XXX\r\n'            # filepaths to bbs files ...
                u'C:\\XXX\r\n'            # filepaths to bbs files ...
                u'{s.sysopname}\r\n'      # sysop's name
                u'{s.alias}\r\n'          # user's alias
                u'00:05\r\n'              # event time(?)
                u'Y\r\n'                  # error-correcting connection
                u'Y\r\n'                  # is ANSI in NG mode?
                u'Y\r\n'                  # use record locking?
                u'7\r\n'                  # default color ..
                u'{s.remaining_mins}\r\n'
                u'09/09/99\r\n'           # last new file scan,
                u'{s.lastcall_time}\r\n'  # time of this call
                u'{s.lastcall_time}\r\n'  # time of last call
                u'9999\r\n'               # max daily files
                u'0\r\n'                  # num. files today
                u'0\r\n'                  # u/l Kb today
                u'0\r\n'                  # d/l Kb today
                u'None\r\n'               # user comment
                u'0\r\n'                  # doors opened
                u'0\n'                    # msgs left
                .format(s=self))

    def _get_door32(self):
        """ Return door32.sys-formatted dropfile content. """
        return (u'{s.comtype}\r\n'
                u'{s.comhandle}\r\n'
                u'{s.comspeed}\r\n'
                u'{s.systemname}\r\n'
                u'{s.usernum}\r\n'
                u'{s.fullname}\r\n'
                u'{s.alias}\r\n'
                u'{s.securitylevel}\r\n'
                u'{s.remaining_mins}\r\n'
                u'1\r\n'                  # emulation (1=ansi)
                u'{s.node}\n'
                .format(s=self))

    def _get_callinfo(self):
        """ Return callinfo.BBS-formatted dropfile content. """
        return (u'{s.alias}\r\n'
                u'{s.comspeed}\r\n'
                u'{s.location}\r\n'
                u'{s.securitylevel}\r\n'
                u'{s.remaining_mins}\r\n'
                u'COLOR\r\n'              # COLOR=ansi
                u'{s.password}\r\n'
                u'{s.usernum}\r\n'
                u'{s.time_used}\r\n'
                u'01:23\r\n'              # 1
                u'01:23 01/02/90\r\n'     # ..
                u'ABCDEFGH\r\n'           # ..
                u'0\r\n'                  # ..
                u'99\r\n'                 # ..
                u'0\r\n'                  # ..
                u'9999\r\n'               # 7 unknown fields,
                u'123-456-7890\r\n'       # phone number
                u'01/01/90 02:34\r\n'     # unknown date/time
                u'NOVICE\r\n'             # expert mode (off)
                u'{s.xferprotocol}\r\n'
                u'01/01/90\r\n'           # unknown date
                u'{s.numcalls}\r\n'
                u'{s.pageheight}\r\n'
                u'0\r\n'                  # ptr to new msgs?
                u'0\r\n'                  # total u/l
                u'0\r\n'                  # total d/l
                u'{s.parity}\r\n'         # ?? like 8,N,1 ??
                u'REMOTE\r\n'             # local or remote?
                u'{s.comport}\r\n'
                u'{s.comspeed}\r\n'
                u'FALSE\r\n'              # unknown,
                u'Normal Connection\r\n'  # unknown,
                u'01/02/94 01:20\r\n'     # unknown date/time
                u'0\r\n'                  # task #
                u'1\n'                    # door #
                .format(s=self))

    def _get_dorinfo(self):
        """ Return DORINFO.DEF-formatted dropfile content. """
        return (u'{s.systemname}\r\n'
                u'{s.sysopname}\r\n'     # sysop f.name
                u'{s.sysopname}\r\n'     # sysop l.name
                u'{s.comport}\r\n'
                u'{s.comspeed}\r\n'
                u'0\r\n'                 # "networked"?
                u'{s.alias}\r\n'         # user f.name
                u'{s.alias}\r\n'         # user l.name
                u'{s.location}\r\n'
                u'1\r\n'                 # term (1=ansi)
                u'{s.securitylevel}\r\n'
                u'{s.remaining_mins}\r\n'
                u'-1\n'                   # fossil (-1=external)
                .format(s=self))


class Door(object):

    """ Spawns a subprocess and pipes input and output over bbs session. """

    time_ipoll = 0.05
    time_opoll = 0.05
    blocksize = 7680
    master_fd = None
    # pylint: disable=R0903,R0913
    #        Too few public methods
    #        Too many arguments

    def __init__(self, cmd='/bin/uname', args=(), env_lang='en_US.UTF-8',
                 env_term=None, env_path=None, env_home=None, cp437=False,
                 env=None):
        """
        Class constructor.

        :param cmd: full path of command to execute.
        :type cmd: str
        :param args: command arguments as tuple.
        :type args: tuple
        :param env_lang: exported as environment variable LANG.
        :type env_lang: str
        :param env_term: exported as environment variable TERM.  When
                         unspecified, it is determined by the same
                         TERM value the original blessed.Terminal instance
                         used.
        :type env_term: str
        :param env_path: exported as environment variable PATH.
                         When None (default), the .ini 'env_path'
                         value of section [door] is
        :type env_path: str
        :param env_home: exported as environment variable HOME.  When env_home
                         is None, the environment value of the main process is
                         used.
        :type env_home: str
        :param cp437: When true, forces decoding of external program as
                      codepage 437.  This is the most common encoding used
                      by DOS doors.
        :param env: Additional environment variables to extend to the sub-process.
        :type env: dict
        :type cp437: bool

        """
        self._session, self._term = getsession(), getterminal()
        self.cmd = cmd
        if type(args) is tuple:
            self.args = (self.cmd,) + args
        elif type(args) is list:
            self.args = [self.cmd, ] + args
        else:
            raise ValueError('args must be tuple or list')
        self.env_lang = env_lang
        self.env_term = env_term or self._term.kind
        self.env_path = env_path or get_ini('door', 'path')
        self.env_home = env_home or os.getenv('HOME')
        self.env = env or {}
        self.cp437 = cp437
        self._utf8_decoder = codecs.getincrementaldecoder('utf8')()

    def run(self):
        """
        Begin door execution.

        pty.fork() is called, child process calls execvpe() while the parent
        process pipes session IPC data to and from the slave pty, until the
        child process exits.
        """
        try:
            import termios
            import fcntl
            import pty
        except ImportError, err:
            raise OSError('door support not (yet) supported on {0} platform.'
                          .format(sys.platform.lower()))

        logger = logging.getLogger()
        env = self.env.copy()
        env.update({'LANG': self.env_lang,
                    'TERM': self.env_term,
                    'PATH': self.env_path,
                    'HOME': self.env_home,
                    'LINES': str(self._term.height),
                    'COLUMNS': str(self._term.width),
                    })
        # pylint: disable=W1202
        #         Use % formatting in logging functions ...
        logger.debug('os.execvpe(cmd={self.cmd}, args={self.args}, '
                     'env={self.env}'.format(self=self))
        try:
            # on Solaris we would need to use something like I've done
            # in pexpect project, a custom pty fork implementation.
            pid, self.master_fd = pty.fork()
        except OSError as err:
            # too many open files, out of memory, no such file/directory
            logger.error('OSError in pty.fork(): %s', err)
            return

        # child process
        if pid == pty.CHILD:
            sys.stdout.flush()
            # send initial screen size
            _bytes = struct.pack('HHHH',
                                 self._term.height,
                                 self._term.width,
                                 0, 0)
            # pylint: disable=E1101
            #         Instance of 'DummyStream' has no 'fileno' member
            fcntl.ioctl(sys.stdout.fileno(), termios.TIOCSWINSZ, _bytes)
            # we cannot log an exception, only print to stderr and have
            # it captured by the parent process; this is because our 'logger'
            # instance is dangerously forked, and any attempt to communicate
            # with multiprocessing pipes, loggers, etc. will cause the value
            # and state of many various file descriptors to become corrupted
            try:
                os.execvpe(self.cmd, self.args, env)
            except OSError as err:
                sys.stderr.write('%s\n' % (err,))
            # pylint: disable=W0212
            #         Access to a protected member _exit of a client class
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
        """
        Derive and modify to implement a keyboard-input filter.

        When keyboard input is detected, this method may filter such input.
        This base class method simply returns data as-is.
        """
        return data

    def output_filter(self, data):
        """
        Filter output (performs cp437 encoding).

        Given door output in bytes, if 'cp437' is specified in class
        constructor, convert to utf8 glyphs using cp437 encoding;
        otherwise decode output naturally as utf8.
        """
        if self.cp437:
            # cp437 bytes don't need to be incrementally decoded, each
            # byte is always final.
            return data.decode('cp437_art')

        # utf-8, however, may be read mid-stream of a multibyte sequence.
        decoded = list()
        for byte in data:
            ucs = self._utf8_decoder.decode(byte, final=False)
            if ucs is not None:
                decoded.append(ucs)
        return u''.join(decoded)

    def resize(self):
        """ Signal resize of terminal to pty. """
        import termios
        import fcntl
        logger = logging.getLogger()
        logger.debug('send TIOCSWINSZ: %dx%d',
                     self._term.width, self._term.height)
        _bytes = struct.pack('HHHH',
                             self._term.height,
                             self._term.width,
                             0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, _bytes)

    def _loop(self):
        """ Main event loop, polling i/o of pty and session. """
        # pylint: disable=R0914
        #         Too many local variables (21/15)
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
                    if n_written != len(data):
                        # we wrote none or some of our keyboard input, but
                        # not all. re-buffer remaining bytes back into
                        # session for next poll
                        self._session.buffer_input(data[n_written:])

                        # XXX I've never actually seen this, though. It might
                        # require writing a sub-program that artificially
                        # hangs, such as time.sleep(99999) to assert correct
                        # behavior. Please report, should be ok ..
                        logger.error('re-buffer_input(%r)!', data[n_written:])


class DOSDoor(Door):

    """
    Door-derived class with special handlers for executing dosemu.

    This Door-derived class removes the "report cursor position" query
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

    RE_REPWITH_CLEAR = (r'\033\[('
                        r'1;80H.*\033\[1;1H'
                        r'|H\033\[2J'
                        r'|\d+;1H.*\033\[1;1H'
                        r')')
    RE_REPWITH_NONE = (r'\033\[('
                       r'6n'
                       r'|\?1049[lh]'
                       r'|\d+;\d+r'
                       r'|1;1H\033\[\dM)')
    START_BLOCK = 4.0
    # pylint: disable=R0913
    #         Too many arguments

    def __init__(self, cmd='/bin/uname', args=(), env_lang='en_US.UTF-8',
                 env_term=None, env_path=None, env_home=None, cp437=True):
        """
        Class constructor.

        :param cmd: full path of command to execute.
        :type cmd: str
        :param args: command arguments as tuple.
        :type args: tuple
        :param env_lang: exported as environment variable LANG.
        :type env_lang: str
        :param env_term: exported as environment variable TERM.  When
                         unspecified, it is determined by the same
                         TERM value the original blessed.Terminal instance
                         used.
        :type env_term: str
        :param env_path: exported as environment variable PATH.
                         When None (default), the .ini 'env_path'
                         value of section [door] is
        :type env_path: str
        :param env_home: exported as environment variable HOME.  When env_home
                         is None, the environment value of the main process is
                         used.
        :type env_home: str
        :param cp437: When true, forces decoding of external program as
                      codepage 437.  This is the most common encoding used
                      by DOS doors.
        :param env: Additional environment variables to extend to the
                    sub-process.
        :type env: dict
        :type cp437: bool
        """
        Door.__init__(self, cmd, args, env_lang, env_term,
                      env_path, env_home, cp437)
        self.check_winsize()
        self._stime = time.time()
        self._re_trim_clear = re.compile(self.RE_REPWITH_CLEAR,
                                         flags=re.DOTALL)
        self._re_trim_none = re.compile(self.RE_REPWITH_NONE,
                                        flags=re.DOTALL)
        self._replace_clear = u''.join((self._term.move(25, 0),
                                        (u'\r\n' * 25),
                                        self._term.home))

    def output_filter(self, data):
        """ filter screen output (removes dosemu startup sequences). """
        data = Door.output_filter(self, data)
        if self._stime is not None and (
                time.time() - self._stime < self.START_BLOCK):
            data = re.sub(pattern=self._re_trim_clear,
                          repl=(self._replace_clear), string=data)
            data = re.sub(pattern=self._re_trim_none,
                          repl=u'\r\n', string=data)
        return data

    def input_filter(self, data):
        """ filter keyboard input (used for "throway" bug workaround). """
        return data if time.time() - self._stime > self.START_BLOCK else u''

    def check_winsize(self):
        """ Assert window size is large enough for a DOS door. """
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
        Begin door execution.

        pty.fork() is called, child process calls execvpe() while the parent
        process pipes telnet session IPC data to and from the slave pty until
        child process exits.

        On exit, DOSDoor flushes any keyboard input; DOSEMU appears to send
        various terminal reset sequences that may cause a reply to be received
        on input, and later as an invalid menu command.
        """
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


# pylint: disable=R0913,R0914,R0915
#         Too many arguments
#         Too many local variables
#         Too many statements
def launch(dos=None, cp437=True, drop_type=None,
           drop_folder=None, name=None, args='',
           forcesize=None, activity=None, command=None,
           nodes=None, forcesize_func=None, env_term=None):
    """
    Helper function for launching an external program as a "Door".

    the forcesize_func may be overridden if the sysop wants to use
    their own function for presenting the screen resize prompt.

    virtual node pools are per-door, based on the 'name' argument, up
    to a maximum determined by the 'nodes' argument.
    name='Netrunner' nodes=4 would mean that the door, Netrunner, has
    a virtual node pool with 4 possible nodes in it. When 4 people
    are already playing the game, additional users will be notified
    that there are no nodes available for play until one of them is
    released.

    for DOS doors, the [dosemu] section of default.ini is used for
    defaults::

        default.ini
        ---
        [dosemu]
        bin = /usr/bin/dosemu
        home = /home/bbs
        path = /usr/bin:/usr/games:/usr/local/bin
        opts = -u virtual -f /home/bbs/dosemu.conf -o /home/bbs/dosemu%%#.log %%c 2> /home/bbs/dosemu_boot%%#.log
        dropdir = /home/bbs/dos
        nodes = 4

    in 'opts', %%# becomes the virtual node number, %%c becomes the 'command'
    argument.

    'dropdir' is where dropfiles will be created if unspecified. you can
    give each door a dropdir for each node if you like, for ultimate
    compartmentalization -- just set the 'dropdir' argument when calling
    this function.

    -u virtual can be used to add a section to your dosemu.conf for
    virtualizing the com port (which allows you to use the same dosemu.conf
    locally by omitting '-u virtual')::

        dosemu.conf
        ---
        $_cpu = (80386)
        $_hogthreshold = (20)
        $_layout = "us"
        $_external_charset = "utf8"
            $_internal_charset = "cp437"
        $_term_update_freq = (4)
        $_rdtsc = (on)
        $_cpuspeed = (166.666)
        ifdef u_virtual
                $_com1 = "virtual"
        endif
    """
    session, term = getsession(), getterminal()
    logger = logging.getLogger()
    echo(term.clear)

    with term.fullscreen():
        store_rows, store_cols = None, None
        env_term = env_term or term.kind
        strnode = None
        (dosbin, doshome, dospath, dosopts, dosdropdir, dosnodes) = (
            get_ini('dosemu', 'bin'),
            get_ini('dosemu', 'home'),
            get_ini('dosemu', 'path'),
            get_ini('dosemu', 'opts'),
            get_ini('dosemu', 'dropdir'),
            get_ini('dosemu', 'nodes'))

        if drop_folder is not None and drop_type is None:
            drop_type = 'DOORSYS'

        if drop_type is not None and drop_folder is None:
            drop_folder = dosdropdir

        if drop_folder or drop_type:
            assert name is not None, (
                'name required for door using node pools')

            for node in range(nodes if nodes is not None else dosnodes):
                event = 'lock-%s/%d' % (name, node)
                session.send_event(event, ('acquire', None))
                data = session.read_event(event)

                if data is True:
                    strnode = str(node + 1)
                    break

            if strnode is None:
                logger.warn('No virtual nodes left in pool: %s', name)
                echo(term.bold_red(u'This door is currently at maximum '
                                   u'capacity. Please try again later.'))
                term.inkey(3)
                return

            logger.info('Requisitioned virtual node %s-%s', name, strnode)
            dosopts = dosopts.replace('%#', strnode)
            dosdropdir = dosdropdir.replace('%#', strnode)
            drop_folder = drop_folder.replace('%#', strnode)
            args = args.replace('%#', strnode)

        try:
            if dos is not None or forcesize is not None:
                if forcesize is None:
                    forcesize = (80, 25,)
                else:
                    assert len(forcesize) == 2, forcesize

                # pylint: disable=W0633
                #         Attempting to unpack a non-sequence
                want_cols, want_rows = forcesize

                if want_cols != term.width or want_rows != term.height:
                    store_cols, store_rows = term.width, term.height
                    echo(u'\x1b[8;%d;%dt' % (want_rows, want_cols,))
                    term.inkey(timeout=0.25)

                dirty = True

                if not (term.width == want_cols and term.height == want_rows):
                    if forcesize_func is not None:
                        forcesize_func()
                    else:
                        while not (term.width == want_cols and
                                   term.height == want_rows):
                            if session.poll_event('refresh'):
                                dirty = True

                            if dirty:
                                dirty = False
                                echo(term.clear)
                                echo(term.bold_cyan(
                                    u'o' + (u'-' * (forcesize[0] - 2))
                                    + u'>\r\n'
                                    + (u'|\r\n' * (forcesize[1] - 2))))
                                echo(u''.join(
                                    (term.bold_cyan(u'V'),
                                     term.bold(u' Please resize your screen '
                                               u'to %sx%s and/or press ENTER '
                                               u'to continue' % (want_cols,
                                                                 want_rows)))))

                            ret = term.inkey(timeout=0.25)

                            if ret in (term.KEY_ENTER, u'\r', u'\n'):
                                break

                if term.width != want_cols or term.height != want_rows:
                    echo(u'\r\nYour dimensions: %s by %s; '
                         u'emulating %s by %s' % (term.width, term.height,
                                                  want_cols, want_rows,))

                    # hand-hack, its ok ... really
                    store_cols, store_rows = term.width, term.height
                    term.columns, term.rows = want_cols, want_rows
                    term.inkey(timeout=1)

            if activity is not None:
                session.activity = activity
            elif name is not None:
                session.activity = 'Playing %s' % name
            else:
                session.activity = 'Playing a door game'

            if drop_folder is not None:
                if not os.path.isabs(drop_folder):
                    drop_folder = os.path.join(dosdropdir, drop_folder)

                Dropfile(getattr(Dropfile, drop_type)).save(drop_folder)

            door = None

            if dos is not None:
                # launch a dosemu door
                cmd = None

                if command is not None:
                    cmd = command
                else:
                    cmd = dosbin
                    args = dosopts.replace('%c', '"' + args + '"')

                door = DOSDoor(cmd, shlex.split(args), cp437=True,
                               env_home=doshome, env_path=dospath,
                               env_term=env_term)
            else:
                # launch a unix program
                door = Door(command, shlex.split(args), cp437=cp437,
                            env_term=env_term)

            door.run()
        finally:
            if store_rows is not None and store_cols is not None:
                term.rows, term.columns = store_rows, store_cols
                echo(u'\x1b[8;%d;%dt' % (store_rows, store_cols,))
                term.inkey(timeout=0.25)

            if name is not None and drop_type:
                session.send_event(
                    event='lock-%s/%d' % (name, int(strnode) - 1),
                    data=('release', None))
                logger.info('Released virtual node %s-%s', name, strnode)
