"""
SFTP server for x/84 bbs https://github.com/jquast/x84

In order to configure x/84 as an SFTP server, you will need to add an [sftp]
section to your default.ini file and add a `root` option. This points to the
location of your SFTP server's root directory. Within that directory, ensure
that there is a directory named `__uploads__`.

This is based on paramiko's `StubSFTPServer` implementation.
"""

# std imports
import logging
import os

# 3rd-party
from paramiko import (
    SFTPServerInterface,
    SFTPServer,
    SFTPAttributes,
    SFTPHandle,
    SFTP_OK,
    SFTP_PERMISSION_DENIED,
)

# local
from x84.bbs import get_ini

# directory name for flagged files
flagged_dirname = '__flagged__'
uploads_dirname = '__uploads__'


class X84SFTPHandle (SFTPHandle):

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger('x84.engine')
        self.user = kwargs.pop('user')
        super(X84SFTPHandle, self).__init__(*args, **kwargs)

    def stat(self):
        self.log.debug('stat')
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)

    def chattr(self, attr):
        if not self.user.is_sysop:
            return SFTP_PERMISSION_DENIED
        self.log.debug('chattr ({0!r})'.format(attr))
        # python doesn't have equivalents to fchown or fchmod, so we have to
        # use the stored filename
        try:
            SFTPServer.set_file_attr(self.filename, attr)
            return SFTP_OK
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)


class X84SFTPServer (SFTPServerInterface):
    ROOT = get_ini(section='sftp',
                   key='root')
    UMASK = get_ini(section='sftp',
                         key='umask'
                    ) or 0o644

    def __init__(self, *args, **kwargs):
        from x84.bbs import DBProxy
        self.ssh_session = kwargs.pop('session')
        username = self.ssh_session.username
        userdb = DBProxy('userbase', use_session=False)
        self.user = None
        with userdb:
            self.user = userdb[username]
        self.flagged = self.user.get('flaggedfiles', set())
        self.log = logging.getLogger('x84.engine')
        super(X84SFTPServer, self).__init__(*args)  # , **kwargs)

    def _dummy_dir_stat(self):
        self.log.debug('_dummy_dir_stat')
        attr = SFTPAttributes.from_stat(
            os.stat(self.ROOT))
        attr.filename = flagged_dirname
        return attr

    def _realpath(self, path):
        self.log.debug('_realpath({0!r})'.format(path))
        if path.endswith(flagged_dirname):
            self.log.debug('fake dir path: {0!r}'.format(path))
            return self.ROOT + path
        elif path.find(flagged_dirname) > -1:
            self.log.debug('fake file path: {0!r}'.format(path))
            for f in self.flagged:
                fstripped = f[f.rindex(os.path.sep) + 1:]
                pstripped = path[path.rindex('/') + 1:]
                if fstripped == pstripped:
                    self.log.debug('file is actually {0}'.format(f))
                    return f
        return self.ROOT + self.canonicalize(path)

    def _is_uploaddir(self, path):
        return ('/{0}'.format(path) == uploads_dirname)

    def list_folder(self, path):
        self.log.debug('list_folder({0!r})'.format(path))
        rpath = self._realpath(path)
        if not self.user.is_sysop and self._is_uploaddir(path):
            return []
        try:
            out = []
            if path == u'/':
                out.append(self._dummy_dir_stat())
            elif flagged_dirname in path:
                for fname in self.flagged:
                    rname = fname
                    attr = SFTPAttributes.from_stat(os.stat(rname))
                    attr.filename = fname[fname.rindex('/') + 1:]
                    out.append(attr)
                return out
            flist = os.listdir(rpath)
            for fname in flist:
                attr = SFTPAttributes.from_stat(
                    os.stat(os.path.join(rpath, fname)))
                attr.filename = fname
                out.append(attr)
            return out
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)

    def stat(self, path):
        self.log.debug('stat({0!r})'.format(path))
        if path.endswith(flagged_dirname):
            return self._dummy_dir_stat()
        elif path.find(flagged_dirname) > -1:
            for f in self.flagged:
                fstripped = f[f.rindex(os.path.sep) + 1:]
                pstripped = path[path.rindex('/') + 1:]
                if fstripped == pstripped:
                    self.log.debug('file is actually {0}'.format(f))
                    return SFTPAttributes.from_stat(f)
        path = self._realpath(path)
        try:
            return SFTPAttributes.from_stat(os.stat(path))
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)

    def lstat(self, path):
        self.log.debug('lstat({0!r})'.format(path))
        if path.endswith(flagged_dirname):
            return self._dummy_dir_stat()
        elif path.find(flagged_dirname) > -1:
            for f in self.flagged:
                fstripped = f[f.rindex(os.path.sep) + 1:]
                pstripped = path[path.rindex('/') + 1:]
                if fstripped == pstripped:
                    self.log.debug('file is actually {0}'.format(f))
                    return SFTPAttributes.from_stat(f)
        path = self._realpath(path)
        try:
            return SFTPAttributes.from_stat(os.lstat(path))
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)

    def open(self, path, flags, attr):
        self.log.debug('lstat({0!r}, {1!r}, {2!r})'
                       .format(path, flags, attr))
        path = self._realpath(path)
        if (flags & os.O_CREAT and (uploads_dirname not in path and
                                    not self.user.is_sysop) or
                (uploads_dirname in path and os.path.exists(path))):
            return SFTP_PERMISSION_DENIED
        try:
            binary_flag = getattr(os, 'O_BINARY',  0)
            flags |= binary_flag
            fd = os.open(path, flags, self.UMASK)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        if (flags & os.O_CREAT) and (attr is not None):
            attr._flags &= ~attr.FLAG_PERMISSIONS
            SFTPServer.set_file_attr(path, attr)
        if flags & os.O_WRONLY:
            if flags & os.O_APPEND:
                fstr = 'ab'
            else:
                fstr = 'wb'
        elif flags & os.O_RDWR:
            if flags & os.O_APPEND:
                fstr = 'a+b'
            else:
                fstr = 'r+b'
        else:
            # O_RDONLY (== 0)
            fstr = 'rb'
        try:
            f = os.fdopen(fd, fstr)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        fobj = X84SFTPHandle(flags, user=self.user)
        fobj.filename = path
        fobj.readfile = f
        fobj.writefile = f

        if path in self.flagged:
            self.flagged.remove(path)
            self.user['flaggedfiles'] = self.flagged
        return fobj

    def remove(self, path):
        if not self.user.is_sysop or flagged_dirname in path:
            return SFTP_PERMISSION_DENIED
        self.log.debug('remove({0!r})'.format(path))
        path = self._realpath(path)
        try:
            os.remove(path)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        return SFTP_OK

    def rename(self, oldpath, newpath):
        if not self.user.is_sysop or flagged_dirname in path:
            return SFTP_PERMISSION_DENIED
        self.log.debug('rename({0!r}, {1!r})'.format(oldpath, newpath))
        oldpath = self._realpath(oldpath)
        newpath = self._realpath(newpath)
        try:
            os.rename(oldpath, newpath)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        return SFTP_OK

    def mkdir(self, path, attr):
        if not self.user.is_sysop or flagged_dirname in path:
            return SFTP_PERMISSION_DENIED
        self.log.debug('mkdir({0!r}, {1!r})'.format(path, attr))
        path = self._realpath(path)
        try:
            os.mkdir(path)
            if attr is not None:
                SFTPServer.set_file_attr(path, attr)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        return SFTP_OK

    def rmdir(self, path):
        if not self.user.is_sysop or flagged_dirname in path:
            return SFTP_PERMISSION_DENIED
        self.log.debug('rmdir({0!r})'.format(path))
        path = self._realpath(path)
        try:
            os.rmdir(path)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        return SFTP_OK

    def chattr(self, path, attr):
        if self._is_uploaddir(path):
            return SFTP_PERMISSION_DENIED
        elif not self.user.is_sysop or \
                uploads_dirname in path or \
                flagged_dirname in path:
            return SFTP_PERMISSION_DENIED
        self.log.debug('chattr({0!r})'.format(path))
        path = self._realpath(path)
        try:
            SFTPServer.set_file_attr(path, attr)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        return SFTP_OK

    def symlink(self, target_path, path):
        if not self.user.is_sysop or flagged_dirname in path:
            return SFTP_PERMISSION_DENIED
        self.log.debug('symlink({0!r}, {1!r})'.format(target_path, path))
        path = self._realpath(path)
        if (len(target_path) > 0) and (target_path[0] == '/'):
            # absolute symlink
            target_path = os.path.join(self.ROOT, target_path[1:])
            if target_path[:2] == '//':
                # bug in os.path.join
                target_path = target_path[1:]
        else:
            # compute relative to path
            abspath = os.path.join(os.path.dirname(path), target_path)
            if abspath[:len(self.ROOT)] != self.ROOT:
                # this symlink isn't going to work anyway
                # -- just break it immediately
                target_path = '<error>'
        try:
            os.symlink(target_path, path)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        return SFTP_OK

    def readlink(self, path):
        self.log.debug('readlink({0!r})'.format(path))
        path = self._realpath(path)
        try:
            symlink = os.readlink(path)
        except OSError as err:
            return SFTPServer.convert_errno(err.errno)
        # if it's absolute, remove the root
        if os.path.isabs(symlink):
            if symlink[:len(self.ROOT)] == self.ROOT:
                symlink = symlink[len(self.ROOT):]
                if (len(symlink) == 0) or (symlink[0] != '/'):
                    symlink = '/' + symlink
            else:
                symlink = '<error>'
        return symlink
