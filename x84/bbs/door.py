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
    > information to doors; this was usually done with "dropfiles", small
    > binary or text files dropped into known locations in the BBS's file
    > system.
    """

    #: Dropfile type constants
    (DOORSYS, DOOR32, CALLINFOBBS, DORINFO) = range(4)

    def __init__(self, filetype=None, node=None):
        """
        Class initializer.

        :param int filetype: dropfile type. One of ``Dropfile.DOORSYS``,
                             ``Dropfile.DOOR32``, ``Dropfile.CALLINFOBBS``,
                             or ``Dropfile.DORINFO``.
        :param int node: A node number specified by caller; for some DOS
                         doors, this is a very specific and limited number
                         bounded and lock-acquired per-door by sesame.py.
                         For others, it is inconsequential, in which case
                         the session's system-wide node number is used.
        """
        self._filetype = filetype
        self._node = node

    def save(self, folder):
        """ Save dropfile to destination ``folder``. """
        f_path = os.path.join(folder, self.filename)
        with codecs.open(f_path, 'w', 'ascii', 'replace') as out_p:
            out_p.write(self.__str__())

    @property
    def node(self):
        """ User's node number. """
        return self._node or getsession().node

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
        if self._filetype == self.DOORSYS:
            return 'DOOR.SYS'
        elif self._filetype == self.DOOR32:
            return 'DOOR32.SYS'
        elif self._filetype == self.CALLINFOBBS:
            return 'CALLINFO.BBS'
        elif self._filetype == self.DORINFO:
            # n in DORINFO<n>.DEF is 1-9,0,a-z
            if self.node == 10:
                nodeid = '0'
            elif self.node < 10:
                nodeid = str(self.node)
            else:
                nodeid = chr(ord('a') + (self.node - 11))
                assert ord(nodeid) <= ord('z')
            return 'DORINFO{0}.DEF'.format(nodeid).upper()
        else:
            raise ValueError('filetype is unknown: {0}'.format(self._filetype))

    def __str__(self):
        """ Return dropfile content. """
        method = {
            self.DOORSYS: self._get_doorsys,
            self.DOOR32: self._get_door32,
            self.CALLINFOBBS: self._get_callinfo,
            self.DORINFO: self._get_dorinfo,
        }.get(self._filetype, None)
        if method is None:
            raise ValueError('unknown dropfile filetype: {self._filetype}'
                             .format(self=self))
        return method()

    def _get_doorsys(self):
        """ Return door.sys-formatted dropfile content. """
        return (u'{self.comport}:\r\n'
                u'{self.comspeed}\r\n'
                u'{self.parity}\r\n'
                u'{self.node}\r\n'
                u'{self.comspeed}\r\n'
                u'Y\r\n'                     # screen?
                u'Y\r\n'                     # printer?
                u'Y\r\n'                     # pager alarm?
                u'Y\r\n'                     # caller alartm?
                u'{self.fullname}\r\n'
                u'{self.location}\r\n'
                u'123-456-7890\r\n'          # phone number1
                u'123-456-7890\r\n'          # phone number2
                u'{self.password}\r\n'
                u'{self.securitylevel}\r\n'
                u'{self.numcalls}\r\n'
                u'{self.lastcall_date}\r\n'
                u'{self.remaining_secs}\r\n'
                u'{self.remaining_mins}\r\n'
                u'GR\r\n'                    # graphics mode
                u'{self.pageheight}\r\n'
                u'N\r\n'                     # expert mode?
                u'1,2,3,4,5,6,7\r\n'         # conferences
                u'1\r\n'                     # conf. sel, exp. date
                u'01/01/99\r\n'              # exp. date
                u'{self.usernum}\r\n'
                u'{self.xferprotocol}\r\n'
                u'0\r\n'                     # total num. uploads
                u'0\r\n'                     # total num, downloads
                u'0\r\n'                     # daily d/l limit
                u'9999999\r\n'               # return val/write val
                u'01/01/2001\r\n'            # birthdate
                # TODO
                u'C:\\XXX\r\n'               # filepaths to bbs files ...
                u'C:\\XXX\r\n'               # filepaths to bbs files ...
                u'{self.sysopname}\r\n'      # sysop's name
                u'{self.alias}\r\n'          # user's alias
                u'00:05\r\n'                 # event time(?)
                u'Y\r\n'                     # error-correcting connection
                u'Y\r\n'                     # is ANSI in NG mode?
                u'Y\r\n'                     # use record locking?
                u'7\r\n'                     # default color ..
                u'{self.remaining_mins}\r\n'
                u'09/09/99\r\n'              # last new file scan,
                u'{self.lastcall_time}\r\n'  # time of this call
                u'{self.lastcall_time}\r\n'  # time of last call
                u'9999\r\n'                  # max daily files
                u'0\r\n'                     # num. files today
                u'0\r\n'                     # u/l Kb today
                u'0\r\n'                     # d/l Kb today
                u'None\r\n'                  # user comment
                u'0\r\n'                     # doors opened
                u'0\n'                       # msgs left
                .format(self=self))

    def _get_door32(self):
        """ Return door32.sys-formatted dropfile content. """
        return (u'{self.comtype}\r\n'
                u'{self.comhandle}\r\n'
                u'{self.comspeed}\r\n'
                u'{self.systemname}\r\n'
                u'{self.usernum}\r\n'
                u'{self.fullname}\r\n'
                u'{self.alias}\r\n'
                u'{self.securitylevel}\r\n'
                u'{self.remaining_mins}\r\n'
                u'1\r\n'                  # emulation (1=ansi)
                u'{self.node}\n'
                .format(self=self))

    def _get_callinfo(self):
        """ Return callinfo.BBS-formatted dropfile content. """
        return (u'{self.alias}\r\n'
                u'{self.comspeed}\r\n'
                u'{self.location}\r\n'
                u'{self.securitylevel}\r\n'
                u'{self.remaining_mins}\r\n'
                u'COLOR\r\n'              # COLOR=ansi
                u'{self.password}\r\n'
                u'{self.usernum}\r\n'
                u'{self.time_used}\r\n'
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
                u'{self.xferprotocol}\r\n'
                u'01/01/90\r\n'           # unknown date
                u'{self.numcalls}\r\n'
                u'{self.pageheight}\r\n'
                u'0\r\n'                  # ptr to new msgs?
                u'0\r\n'                  # total u/l
                u'0\r\n'                  # total d/l
                u'{self.parity}\r\n'      # ?? like 8,N,1 ??
                u'REMOTE\r\n'             # local or remote?
                u'{self.comport}\r\n'
                u'{self.comspeed}\r\n'
                u'FALSE\r\n'              # unknown,
                u'Normal Connection\r\n'  # unknown,
                u'01/02/94 01:20\r\n'     # unknown date/time
                u'0\r\n'                  # task #
                u'1\n'                    # door #
                .format(self=self))

    def _get_dorinfo(self):
        """ Return DORINFO.DEF-formatted dropfile content. """
        return (u'{self.systemname}\r\n'
                u'{self.sysopname}\r\n'   # sysop f.name
                u'{self.sysopname}\r\n'   # sysop l.name
                u'{self.comport}\r\n'
                u'{self.comspeed}\r\n'
                u'0\r\n'                  # "networked"?
                u'{self.alias}\r\n'       # user f.name
                u'{self.alias}\r\n'       # user l.name
                u'{self.location}\r\n'
                u'1\r\n'                  # term (1=ansi)
                u'{self.securitylevel}\r\n'
                u'{self.remaining_mins}\r\n'
                u'-1\n'                   # fossil (-1=external)
                .format(self=self))


class Door(object):

    """ Spawns a subprocess and pipes input and output over bbs session. """

    time_ipoll = 0.05
    time_opoll = 0.05
    blocksize = 7680
    master_fd = None

    def __init__(self, cmd='/bin/uname', args=(), env=None, cp437=False):
        """
        Class initializer.

        :param str cmd: full path of command to execute.
        :param tuple args: command arguments as tuple.
        :param bool cp437: When true, forces decoding of external program as
                           codepage 437.  This is the most common encoding used
                           by DOS doors.
        :param dict env: Environment variables to extend to the sub-process.
                         You should more than likely specify values for TERM,
                         PATH, HOME, and LANG.
        """
        self._session, self._term = getsession(), getterminal()
        self.cmd = cmd
        if isinstance(args, tuple):
            self.args = (self.cmd,) + args
        elif isinstance(args, list):
            self.args = [self.cmd, ] + args
        else:
            raise ValueError('args must be tuple or list')

        self.log = logging.getLogger(__name__)
        self.env = (env or {}).copy()
        self.env.update(
            {'LANG': env.get('LANG', 'en_US.UTF-8'),
             'TERM': env.get('TERM', self._term.kind),
             'PATH': env.get('PATH', get_ini('door', 'path')),
             'HOME': env.get('HOME', os.getenv('HOME')),
             'LINES': str(self._term.height),
             'COLUMNS': str(self._term.width),
             })

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
        except ImportError as err:
            raise OSError('door support not (yet) supported on {0} platform.'
                          .format(sys.platform.lower()))

        self.log.debug('os.execvpe(cmd={self.cmd}, args={self.args}, '
                       'env={self.env})'.format(self=self))
        try:
            pid, self.master_fd = pty.fork()
        except OSError as err:
            # too many open files, out of memory, no such file/directory
            self.log.error('OSError in pty.fork(): %s', err)
            return

        # child process
        if pid == pty.CHILD:
            sys.stdout.flush()

            # send initial screen size
            _bytes = struct.pack(
                'HHHH', self._term.height, self._term.width, 0, 0)

            # pylint: disable=E1101
            #         Instance of 'DummyStream' has no 'fileno' member
            fcntl.ioctl(sys.stdout.fileno(), termios.TIOCSWINSZ, _bytes)

            try:
                os.execvpe(self.cmd, self.args, self.env)

            except OSError as err:
                # we cannot log an exception, only print to stderr and have
                # it captured by the parent process; this is because our
                # 'log' instance is dangerously forked, and any attempt to
                # communicate with multiprocessing pipes, loggers, etc. will
                # cause the value and state of many various file descriptors
                # to become corrupted, as our file descriptors are shared.

                sys.stderr.write('%s\n' % (err,))

            # pylint: disable=W0212
            #         Access to a protected member _exit of a client class
            os._exit(1)

        # parent process
        #
        # execute self._loop() and catch all i/o and o/s errors
        try:
            self.log.info('exec/%s: %r, env=%r', pid, self.args, self.env)
            self._loop()

        except IOError as err:
            self.log.error('IOError: %s', err)

        except OSError as err:
            # errno 5 is OK: it occurs when a read() call occurs after
            # sys.stdout has been closed by the child.
            if err.errno != 5:
                self.log.error('OSError: %s', err)

        (pid, status) = os.waitpid(pid, 0)
        res = status >> 8

        log_func = self.log.error if res != 0 else self.log.debug
        log_func('%s child %s exit %d', self.cmd, pid, res)

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
        initializer, convert to utf8 glyphs using cp437 encoding;
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
        _bytes = struct.pack('HHHH',
                             self._term.height,
                             self._term.width,
                             0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, _bytes)

    def _loop(self):
        """ Main event loop, polling i/o of pty and session. """
        while True:
            # block up to self.time_opoll for screen output
            if self.master_fd == -1:
                # pty file descriptor closed by child,
                # early termination!
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
                        self.log.warn('re-buffer_input(%r)!', data[n_written:])


class DOSDoor(Door):

    """
    Door-derived class with special handlers for executing dosemu.

    This Door-derived class removes the "report cursor position" query
    sequence, which is sent by DOSEMU on startup. It also removes the "switch
    to alternate screen mode" set and reset (blessings terminals provide this
    with the context manager, using statement ``with term.fullscreen():``).

    It would appear that any early keyboard input received (esp. in response
    to "report cursor position") prior to DOOR execution in DOSEMU causes all
    input to be bitshifted and invalid and/or broken.

    This class resolves that issue by overriding ``output_filter`` to remove
    such sequences, and ``input_filter`` which only allows input after a few
    seconds have elapsed.
    """

    #: regular expression of sequences to be replaced by ``term.clear``
    #: during ``START_BLOCK`` delay in ``output_filter``
    RE_REPWITH_CLEAR = (r'\033\[('
                        r'1;80H.*\033\[1;1H'
                        r'|H\033\[2J'
                        r'|\d+;1H.*\033\[1;1H'
                        r')')

    #: regular expression of sequences to strip entirely during
    #: ``START_BLOCK`` delay in ``output_filter``.
    RE_REPWITH_NONE = (r'\033\[('
                       r'6n'
                       r'|\?1049[lh]'
                       r'|\d+;\d+r'
                       r'|1;1H\033\[\dM)')

    #: Number of seconds to allow to elapse for ``input_filter`` and
    #: ``output_filter`` as a workaround for stripping startup sequences
    #: and working around a strange keyboard input bug.
    START_BLOCK = 4.0

    def __init__(self, cmd='/bin/uname', args=(), env=None, cp437=True):
        """
        Class initializer.

        :param str cmd: full path of command to execute.
        :param tuple args: command arguments as tuple.
        :param bool cp437: When true, forces decoding of external program as
                           codepage 437.  This is the most common encoding used
                           by DOS doors.
        :param dict env: Environment variables to extend to the sub-process.
                         You should more than likely specify values for TERM,
                         PATH, HOME, and LANG.
        """
        Door.__init__(self, cmd=cmd, args=args, env=env, cp437=cp437)
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

    def resize(self):
        """ Signal resize of terminal to DOS -- does nothing. """
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
        self._stime = time.time()

        Door.run(self)

        # fight against 'set scrolling region' by resetting, LORD
        # contains, for example: \x1b[3;22r after 'E'nter the realm
        echo(u''.join((self._term.normal,
                       self._term.move(self._term.height, self._term.width),
                       u"\x1b[r",
                       self._term.move(self._term.height, 0),
                       u'\r\n\r\n')))

        # flush any previously decoded but unreceived keystrokes,
        # and any unprocessed input from telnet session not yet processed.
        self._term.kbflush()
        self._session.flush_event('input')
