"""
Userbase record access for x/84, https://github.com/jquast/x84/
"""
import logging

import x84.bbs.dbproxy

#pylint: disable=C0103
#        Invalid name "logger" for type constant (should match
logger = logging.getLogger()


def list_users():
    """
    Returns all user handles.
    """
    return x84.bbs.dbproxy.DBProxy('userbase').keys()


def get_user(handle):
    """
    Returns User record, keyed by handle.
    """
    return x84.bbs.dbproxy.DBProxy('userbase')[handle]


def find_user(handle):
    """
    Given handle, discover and return matching database key case insensitively.
    The returned value may not be equal to the argument, or None if not found.
    """
    for key in x84.bbs.dbproxy.DBProxy('userbase').iterkeys():
        if handle.lower() == key.lower():
            return key


def digestpw_bcrypt(password, salt=None):
    """
    Password digest using bcrypt (optional)
    """
    import bcrypt
    if not salt:
        salt = bcrypt.gensalt()
    return salt, bcrypt.hashpw(password, salt)


def digestpw_internal(password, salt=None):
    """
    Password digest using regular python libs
    """
    import hashlib
    import base64
    import os
    if not salt:
        salt = base64.b64encode(os.urandom(32))
    digest = salt + password
    #pylint: disable=W0612
    #        Unused variable 'loop_cnt'
    for loop_cnt in range(0, 100000):
        digest = hashlib.sha256(digest).hexdigest()
    return salt, digest
digestpw = digestpw_internal


def digestpw_plaintext(password, salt=None):
    """
    No password digest, just store the passwords in plain text
    """
    if not salt:
        salt = 'none'
    return salt, password


def digestpw_init(password_digest):
    """
    Set which password digest routine to use
    """
    global digestpw
    if password_digest == 'bcrypt':
        digestpw = digestpw_bcrypt
    elif password_digest == 'internal':
        digestpw = digestpw_internal
    elif password_digest == 'plaintext':
        digestpw = digestpw_plaintext
    else:
        assert False, ('Invalid value for "system.password_digest"')


class Group(object):
    """
    A simple group record object with properties name', and 'members'.
    Use methods 'add' and 'remove' to add and remove users by handle,
    and 'save' to persist to disk (and other bbs sessions).
    """

    def __init__(self, name, members=()):
        """
        Initialize a group of name and members
        """
        self._name = name
        self._members = set(members)

    @property
    def name(self):
        """
        Name of this group.
        """
        return self._name

    @name.setter
    def name(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._name = value

    @property
    def members(self):
        """
        Members of this group as user handles.
        """
        return self._members

    def add(self, handle):
        """
        Add user to group.
        """
        logger.info('Group(%r).add(%r)', self.name, handle)
        self._members.add(handle)

    def remove(self, handle):
        """
        Remove user from group.
        """
        logger.info('Group(%r).remove(%r)', self.name, handle)
        self._members.remove(handle)

    def save(self):
        """
        Save group record to database.
        """
        x84.bbs.dbproxy.DBProxy('groupbase')[self.name] = self

    def delete(self):
        """
        Delete group record from database, and from .groups of any users.
        """
        udb = x84.bbs.dbproxy.DBProxy('userbase')
        for chk_user in self.members:
            user = udb[chk_user]
            if self.name in user.groups:
                user.group_del(self.name)
                user.save()
        del x84.bbs.dbproxy.DBProxy('groupbase')[self.name]


class User(object):
    """
    A simple user record object with setter and getter properties, 'handle',
    'location', 'email', 'password', 'groups', 'calls', 'lastcall', and 'plan'.
    """
    #pylint: disable=R0902
    #        Too many instance attributes (8/7)

    def __init__(self, handle=u'anonymous'):
        """
        Initialize a user record, using handle
        """
        self._handle = handle
        self._password = (None, None)
        self._handle = u''
        self._location = u''
        self._email = u''
        self._groups = set()
        self._calls = 0
        self._lastcall = 0
        self._plan = u''

    @property
    def handle(self):
        """
        U.handle() --> unicode

        User handle, also the database key.
        """
        return self._handle

    @handle.setter
    def handle(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._handle = value

    @property
    def password(self):
        """
        U.password() --> tuple

        Returns encrypted form of password as tuple (salt, hash).
        If a password has not yet been set, it is (None, None).
        """
        return self._password

    @password.setter
    def password(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._password = digestpw(value)
        logger.info('%s set new password', self.handle)

    def auth(self, try_pass):
        """
        U.auth(unicode) --> boolean

        To authenticate, assert auth(try_pass) == True.
        """
        assert type(try_pass) is unicode
        assert len(try_pass) > 0
        assert self.password != (None, None), ('account is without password')
        salt = self.password[0]
        return self.password == digestpw(try_pass, salt)

    def __setitem__(self, key, value):
        #pylint: disable=C0111,
        #        Missing docstring
        adb = x84.bbs.dbproxy.DBProxy('userbase', 'attrs')
        adb.acquire()
        attrs = adb[self.handle]
        attrs.__setitem__(key, value)
        adb[self.handle] = attrs
        adb.release()
        logger.info('%r setting %r = %r', self.handle, key, value)
    __setitem__.__doc__ = dict.__setitem__.__doc__

    def get(self, key, default=None):
        #pylint: disable=C0111,
        #        Missing docstring
        adb = x84.bbs.dbproxy.DBProxy('userbase', 'attrs')
        if not self.handle in adb:
            logger.info('%r GET %r: default; missing attrs.', self.handle, key)
            return default
        attrs = adb[self.handle]
        if not key in attrs:
            logger.info('%r GET %r: default; attr unset.', self.handle, key)
            return default
        logger.info('get %r GET %r: %d' % (self.handle, key, len(attrs[key])))
        return attrs[key]
    get.__doc__ = dict.get.__doc__

    def __getitem__(self, key):
        #pylint: disable=C0111,
        #        Missing docstring
        return x84.bbs.dbproxy.DBProxy('userbase', 'attrs')[self.handle][key]
    __getitem__.__doc__ = dict.__getitem__.__doc__

    def __delitem__(self, key):
        #pylint: disable=C0111,
        #        Missing docstring
        uadb = x84.bbs.dbproxy.DBProxy('userbase', 'attrs')
        uadb.acquire()
        attrs = uadb[self.handle]
        if key in attrs:
            attrs.__detitem__(key)
            uadb[self.handle] = attrs
        uadb.release()
        logger.info('del %s[%s]', self.handle, key)
    __delitem__.__doc__ = dict.__delitem__.__doc__

    @property
    def groups(self):
        """
        U.groups() --> set

        Set of Group records user is a member of.
        """
        return self._groups

    def group_add(self, group):
        """
        Add user to group.
        """
        return self._groups.add(group)

    def group_del(self, group):
        """
        Remove user from group.
        """
        return self._groups.remove(group)

    def save(self):
        """
        Save user record to databases.
        """
        assert type(self._handle) is unicode, ('handle must be unicode')
        assert len(self._handle) > 0, ('handle must be non-zero length')
        assert (None, None) != self._password, ('password must be set')
        assert self._handle != 'anonymous', ('anonymous user my not be saved.')
        udb = x84.bbs.dbproxy.DBProxy('userbase')
        adb = x84.bbs.dbproxy.DBProxy('userbase', 'attrs')
        gdb = x84.bbs.dbproxy.DBProxy('groupbase')
        udb.acquire()
        adb.acquire()
        gdb.acquire()
        if 0 == len(udb) and self.is_sysop is False:
            logger.warn('%s: First new user becomes sysop.', self.handle)
            self.group_add(u'sysop')
        udb[self.handle] = self
        adb[self.handle] = dict()
        self._apply_groups(gdb)
        udb.release()
        adb.release()
        gdb.release()

    def delete(self):
        """
        Remove user record from database, and as a member of any groups.
        """
        gdb = x84.bbs.dbproxy.DBProxy('groupbase')
        for gname in self._groups:
            group = gdb[gname]
            if self.handle in group.members:
                group.remove(self.handle)
                group.save()
        del x84.bbs.dbproxy.DBProxy('userbase')[self.handle]
        logger.info('%s deleted from userbase', self.handle)

    @property
    def is_sysop(self):
        """
        U.is_sysop --> boolean

        Returns True if user is in u'sysop' group.
        """
        return u'sysop' in self._groups

    @property
    def lastcall(self):
        """
        U.lastcall() --> float

        Time last called, time.time() epoch-formatted.
        """
        return self._lastcall

    @lastcall.setter
    def lastcall(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._lastcall = value

    @property
    def calls(self):
        """Legacy, number of times user has 'called' this board."""
        return self._calls

    @calls.setter
    def calls(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._calls = value

    @property
    def location(self):
        """
        Legacy, used as a geographical location, group names, etc.
        """
        return self._location

    @location.setter
    def location(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._location = value

    @property
    def email(self):
        """
        E-mail address. May be used for password resets.
        """
        return self._email

    @email.setter
    def email(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._email = value

    @property
    def plan(self):
        """
        Unix .plan contents, the original blogosphere.
        """
        return self._plan

    @plan.setter
    def plan(self, value):
        #pylint: disable=C0111
        #         Missing docstring
        self._plan = value

    def _apply_groups(self, gdb):
        """
        Inspect all groupbase members and enforce referential integrity.
        """
        for chk_grp in self._groups:
            if not chk_grp in gdb:
                gdb[chk_grp] = Group(chk_grp, set([self.handle]))
                logger.info('%s: Created new group, %r', self.handle, chk_grp)
            # ensure membership in existing groups
            group = gdb[chk_grp]
            if not self.handle in group.members:
                group.add(self.handle)
                group.save()
        for gname, group in gdb.iteritems():
            if gname not in self._groups and self.handle in group.members:
                group.remove(self.handle)
                group.save()
