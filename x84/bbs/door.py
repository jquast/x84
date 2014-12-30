"""
Door package for x/84 BBS http://github.com/jquast/x84
"""
import logging
import select
import codecs
import struct
import shlex
import time
import sys
import os
import re


class Dropfile(object):
    (DOORSYS, DOOR32, CALLINFOBBS, DORINFO) = range(4)
    DOORSYS_GM = 'GR'  # graphics mode

    def __init__(self, filetype=None):
        assert filetype in (self.DOORSYS, self.DOOR32,
                            self.CALLINFOBBS, self.DORINFO)
        self.filetype = filetype

    def save(self, folder):
        """ Save dropfile to folder """
        f_path = os.path.join(folder, self.filename)
        with codecs.open(f_path, 'w', 'ascii', 'replace') as out_p:
            out_p.write(self.__str__())

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
        return time.strftime(
            '%m/%d/%y', time.localtime(getsession().user.lastcall))

    @property
    def lastcall_time(self):
        from x84.bbs import getsession
        return time.strftime(
            '%H:%M', time.localtime(getsession().user.lastcall))

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
        return 0  # Line 1 : Comm type (0=local, 1=serial, 2=telnet)

    @property
    def comhandle(self):
        return 0  # Line 2 : Comm or socket handle

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
        return 'X'  # x-modem for now, we don't have any xfer code/prefs

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
            return 'DORINFO{0}.DEF'.format(nodeid)
        else:
            raise ValueError('filetype is unknown')

    def __str__(self):
        method = {
            self.DOORSYS: self.get_doorsys,
            self.DOOR32: self.get_door32,
            self.CALLINFOBBS: self.get_callinfo,
            self.DORINFO: self.get_dorinfo,
        }.get(self.filetype)
        if method is None:
            raise ValueError('filetype {0} is unknown: '.format(method))
        return method()

    def get_doorsys(self):
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

    def get_door32(self):
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

    def get_callinfo(self):
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
                u'8  { Databits }\r\n'  # ?? like 8,N,1 ??
                u'REMOTE\r\n'             # local or remote?
                u'{s.comport}\r\n'
                u'{s.comspeed}\r\n'
                u'FALSE\r\n'              # unknown,
                u'Normal Connection\r\n'  # unknown,
                u'01/02/94 01:20\r\n'     # unknown date/time
                u'0\r\n'                  # task #
                u'1\n'                    # door #
                .format(s=self))

    def get_dorinfo(self):
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
                 env_term=None, env_path=None, env_home=None, cp437=False,
                 env=None):
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
            self.args = [self.cmd, ] + args
        else:
            raise ValueError('args must be tuple or list')
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
        self.env = env or {}
        self.cp437 = cp437
        self._utf8_decoder = codecs.getincrementaldecoder('utf8')()

    def run(self):
        """
        Begin door execution. pty.fork() is called, child process
        calls execvpe() while the parent process pipes telnet session
        IPC data to and from the slave pty until child process exits.
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
        logger.debug('os.execvpe(cmd={self.cmd}, args={self.args}, '
                     'env={self.env}'.format(self=self))
        try:
            # on Solaris we would need to use something like I've done
            # in pexpect project, a custom pty fork implementation.
            pid, self.master_fd = pty.fork()
        except OSError, err:
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
        return self.master_fd != -1 and (
            self.master_fd in select.select([self.master_fd, ], (), (), 0)[0])

    def resize(self):
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
        # pylint: disable=R0914
        #         Too many local variables (21/15)
        """
        Poll input and outpout of ptys,
        """
        from x84.bbs import echo
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

    def __init__(self, cmd='/bin/uname', args=(), env_lang='en_US.UTF-8',
                 env_term=None, env_path=None, env_home=None, cp437=False):
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


def launch(dos=None, cp437=True, drop_type=None,
           drop_folder=None, name=None, args='',
           forcesize=None, activity=None, command=None,
           nodes=None, forcesize_func=None, env_term=None):
    """
    helper function for launching doors with inline configuration
    also handles resizing of screens and virtual node pools

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
    from x84.bbs import getsession, getterminal, echo, ini

    session, term = getsession(), getterminal()
    logger = logging.getLogger()
    echo(term.clear)

    with term.fullscreen():
        store_rows, store_cols = None, None

        if env_term is None:
            env_term = session.env['TERM']

        strnode = None
        (dosbin, doshome, dospath, dosopts, dosdropdir, dosnodes) = (
            ini.CFG.get('dosemu', 'bin'),
            ini.CFG.get('dosemu', 'home'),
            ini.CFG.get('dosemu', 'path'),
            ini.CFG.get('dosemu', 'opts'),
            ini.CFG.get('dosemu', 'dropdir'),
            ini.CFG.getint('dosemu', 'nodes'))

        if drop_folder is not None and drop_type is None:
            drop_type = 'DOORSYS'

        if drop_type is not None and drop_folder is None:
            drop_folder = dosdropdir

        if drop_folder or drop_type:
            assert name is not None, (
                'name required for door using node pools')

            for node in range(nodes if nodes != None else dosnodes):
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
                    forcesize = [80, 25]
                else:
                    assert len(forcesize) == 2, forcesize

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
                    term.inkey(timeout=2)

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
                cmd = None

                if command != None:
                    cmd = command
                else:
                    cmd = dosbin
                    args = dosopts.replace('%c', '"' + args + '"')

                door = DOSDoor(cmd, shlex.split(args), cp437=True,
                               env_home=doshome, env_path=dospath,
                               env_term=env_term)
            else:
                door = Door(command, shlex.split(args), cp437=cp437,
                            env_term=env_term)

            door.run()
        except:
            raise
        finally:
            if store_rows != None and store_cols != None:
                term.rows, term.columns = store_rows, store_cols
                echo(u'\x1b[8;%d;%dt' % (store_rows, store_cols,))
                term.inkey(timeout=0.25)

            if name is not None and drop_type:
                session.send_event(
                    event='lock-%s/%d' % (name, int(strnode) - 1),
                    data=('release', None))
                logger.info('Released virtual node %s-%s', name, strnode)
