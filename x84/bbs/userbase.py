"""
Userbase record access for x/84, https://github.com/jquast/x84/
"""
import logging
from x84.bbs.dbproxy import DBProxy

FN_PASSWORD_DIGEST = None
GROUPDB = 'groupbase'
USERDB = 'userbase'


def list_users():
    """
    Returns all user handles.
    """
    return [handle.decode('utf8')
            for handle in DBProxy(USERDB).keys()]


def get_user(handle):
    """
    Returns User record, keyed by handle.
    """
    return DBProxy(USERDB)[handle]


def find_user(handle):
    """
    Given handle, discover and return matching database key case insensitively.
    The returned value may not be equal to the argument, or None if not found.
    """
    for key in DBProxy(USERDB).keys():
        if handle.lower() == key.decode('utf8').lower():
            return key


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
        # pylint: disable=C0111
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
        log = logging.getLogger(__name__)
        log.info("Group({!r}).add({!r})".format(self.name, handle))
        self._members.add(handle)

    def remove(self, handle):
        """
        Remove user from group.
        """
        log = logging.getLogger(__name__)
        log.info("Group({!r}).remove({!r})".format(self.name, handle))
        self._members.remove(handle)

    def save(self):
        """
        Save group record to database.
        """
        DBProxy(GROUPDB)[self.name] = self

    def delete(self):
        """
        Delete group record from database, and from .groups of any users.
        """
        udb = DBProxy(USERDB)
        for chk_user in self.members:
            user = udb[chk_user]
            if self.name in user.groups:
                user.group_del(self.name)
                user.save()
        del DBProxy(GROUPDB)[self.name]


class User(object):

    """
    A simple user record object with setter and getter properties, 'handle',
    'location', 'email', 'password', 'groups', 'calls', 'lastcall', and 'plan'.
    """
    # pylint: disable=R0902,R0924
    #        Too many instance attributes (8/7)
    #        Badly implemented Container, implements
    #          __delitem__, __getitem__, __setitem__
    #          but not __len__

    def __init__(self, handle=u'anonymous'):
        """
        Initialize a user record, using handle
        """
        self._handle = handle
        self._password = (None, None)
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
        # pylint: disable=C0111
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
        """
        U.password = value
        """
        log = logging.getLogger(__name__)
        from x84.bbs import ini
        if ini.CFG.getboolean('system', 'pass_ucase'):
            # facebook and mystic storage style, i wouldn't
            # recommend it though.
            self._password = get_digestpw()(value.upper())
        else:
            self._password = get_digestpw()(value)
        log.info("set password for user {!r}.".format(self.handle))

    def auth(self, try_pass):
        """
        U.auth(unicode) --> boolean

        To authenticate, assert auth(try_pass) == True.
        """
        from x84.bbs import ini
        pass_ucase = ini.CFG.getboolean('system', 'pass_ucase')
        assert type(try_pass) is unicode
        assert len(try_pass) > 0
        assert self.password != (None, None), ('account is without password')
        salt = self.password[0]
        digestpw = get_digestpw()
        return (self.password == digestpw(try_pass, salt) or pass_ucase
                and self.password == digestpw(try_pass.upper(), salt))

    def __setitem__(self, key, value):
        # pylint: disable=C0111,
        #        Missing docstring
        log = logging.getLogger(__name__)
        adb = DBProxy(USERDB, 'attrs')

        if self.handle == 'anonymous':
            log.debug("set attr {!r} not possible for 'anonymous'".format(key))
            return

        with adb:
            if self.handle not in adb:
                adb[self.handle] = dict([(key, value), ])
            else:
                attrs = adb[self.handle]
                attrs.__setitem__(key, value)
                adb[self.handle] = attrs
        log.debug("set attr {!r} for user {!r}.".format(key, self.handle))
    __setitem__.__doc__ = dict.__setitem__.__doc__

    def get(self, key, default=None):
        # pylint: disable=C0111,
        #        Missing docstring
        from x84.bbs import ini
        log = logging.getLogger(__name__)
        adb = DBProxy(USERDB, 'attrs')

        if self.handle not in adb:
            if ini.CFG.getboolean('session', 'tap_db'):
                log.debug('User({!r}).get(key={!r}) returns default={!r}'
                          .format(self.handle, key, default))
            return default

        attrs = adb.get(self.handle, {})
        if key not in attrs:
            if ini.CFG.getboolean('session', 'tap_db'):
                log.debug('User({!r}.get(key={!r}) returns default={!r}'
                          .format(self.handle, key, default))
            return default

        if ini.CFG.getboolean('session', 'tap_db'):
            log.debug('User({!r}.get(key={!r}) returns value.'
                      .format(self.handle, key))
        return attrs[key]
    get.__doc__ = dict.get.__doc__

    def __getitem__(self, key):
        # pylint: disable=C0111,
        #        Missing docstring
        return DBProxy(USERDB, 'attrs')[self.handle][key]
    __getitem__.__doc__ = dict.__getitem__.__doc__

    def __delitem__(self, key):
        # pylint: disable=C0111,
        #        Missing docstring
        log = logging.getLogger(__name__)
        uadb = DBProxy(USERDB, 'attrs')
        with uadb:
            # retrieve attributes from uadb,
            attrs = uadb.get(self.handle, {})
            # delete attribute if exists
            if key in attrs:
                attrs.__delitem__(key)
                uadb[self.handle] = attrs
                log.info("User({!r}) delete attr {!r}."
                         .format(self.handle, key))
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
        (re-)Save user record to database. Changes to user record to not
        automatically persist.  A call to the .save() method must be done.
        """
        log = logging.getLogger(__name__)
        assert type(self._handle) is unicode, ('handle must be unicode')
        assert len(self._handle) > 0, ('handle must be non-zero length')
        assert (None, None) != self._password, ('password must be set')
        assert self._handle != u'anonymous', ('anonymous may not be saved.')
        udb = DBProxy(USERDB)
        with udb:
            if 0 == len(udb) and self.is_sysop is False:
                log.warn('{!r}: First new user becomes sysop.'
                         .format(self.handle))
                self.group_add(u'sysop')
            udb[self.handle] = self
        adb = DBProxy(USERDB, 'attrs')
        with adb:
            if self.handle not in adb:
                adb[self.handle] = dict()
        self._apply_groups()
        log.info("saved user '%s'.", self.handle)

    def delete(self):
        """
        Remove user record from database, and as a member of any groups.
        """
        log = logging.getLogger(__name__)
        gdb = DBProxy(GROUPDB)
        with gdb:
            for gname in self._groups:
                group = gdb[gname]
                if self.handle in group.members:
                    group.remove(self.handle)
                    group.save()
        udb = DBProxy(USERDB)
        with udb:
            del udb[self.handle]
        log.info("deleted user '%s'.", self.handle)

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
        # pylint: disable=C0111
        #         Missing docstring
        self._lastcall = value

    @property
    def calls(self):
        """Legacy, number of times user has 'called' this board."""
        return self._calls

    @calls.setter
    def calls(self, value):
        # pylint: disable=C0111
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
        # pylint: disable=C0111
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
        # pylint: disable=C0111
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
        # pylint: disable=C0111
        #         Missing docstring
        self._plan = value

    def _apply_groups(self):
        """
        Inspect all groupbase members and enforce referential integrity.
        """
        log = logging.getLogger(__name__)
        gdb = DBProxy(GROUPDB)
        with gdb:
            for chk_grp in self._groups:
                if chk_grp not in gdb:
                    gdb[chk_grp] = Group(chk_grp, set([self.handle]))
                    log.info("created group {!r} for user {!r}."
                             .format(chk_grp, self.handle))
                # ensure membership in existing groups
                group = gdb[chk_grp]
                if self.handle not in group.members:
                    group.add(self.handle)
                    group.save()
            for gname, group in gdb.items():
                if gname not in self._groups and self.handle in group.members:
                    group.remove(self.handle)
                    group.save()


def _digestpw_bcrypt(password, salt=None):
    """
    Password digest using bcrypt (optional)
    """
    import bcrypt
    if not salt:
        salt = bcrypt.gensalt()
    if isinstance(password, unicode):
        password = password.encode('utf8')
    return salt, bcrypt.hashpw(password, salt)


def _digestpw_internal(password, salt=None):
    """
    Password digest using regular python libs (slow)
    """
    import hashlib
    import base64
    import os
    if not salt:
        salt = base64.b64encode(os.urandom(32))
    digest = salt + password
    for _count in range(0, 100000):
        # pylint: disable=E1101
        #         Module 'hashlib' has no 'sha256'
        digest = hashlib.sha256(digest).hexdigest()
    return salt, digest


def _digestpw_plaintext(password, salt=None):
    """
    No password digest, just store the passwords in plain text
    """
    if not salt:
        salt = 'none'
    return salt, password


def get_digestpw():
    """
    Returns singleton to password digest routine.
    """
    global FN_PASSWORD_DIGEST
    if FN_PASSWORD_DIGEST is not None:
        return FN_PASSWORD_DIGEST

    from x84.bbs.ini import CFG
    FN_PASSWORD_DIGEST = {
        'bcrypt': _digestpw_bcrypt,
        'internal': _digestpw_internal,
        'plaintext': _digestpw_plaintext,
    }.get(CFG.get('system', 'password_digest'))
    return FN_PASSWORD_DIGEST


def check_new_user(username):
    """ Boolean return when username matches ``newcmds`` ini cfg. """
    from x84.bbs import get_ini
    matching = get_ini(section='matrix',
                       key='newcmds',
                       split=True)
    allowed = get_ini(section='nua',
                      key='allow_apply',
                      getter='getboolean')
    return allowed and username in matching


def check_bye_user(username):
    """ Boolean return when username matches ``byecmds`` in ini cfg. """
    from x84.bbs import get_ini
    matching = get_ini(section='matrix', key='byecmds', split=True)
    return matching and username in matching


def check_anonymous_user(username):
    """ Boolean return when user is anonymous and is allowed. """
    from x84.bbs import get_ini
    matching = get_ini(section='matrix',
                       key='anoncmds',
                       split=True)
    allowed = get_ini(section='matrix',
                      key='enable_anonymous',
                      getter='getboolean',
                      split=False)
    return allowed and username in matching


def check_user_password(username, password):
    """ Boolean return when username and password match user record. """
    from x84.bbs import find_user, get_user
    handle = find_user(username)
    if handle is None:
        return False
    user = get_user(handle)
    if user is None:
        return False
    return password and user.auth(password)


def parse_public_key(user_pubkey):
    """ Return paramiko key class instance of a user's public key text. """
    import paramiko

    if len(user_pubkey.split()) == 3:
        key_msg, key_data, _ = user_pubkey.split()
    elif len(user_pubkey.split()) == 2:
        key_msg, key_data = user_pubkey.split()
    elif len(user_pubkey.split()) == 1:
        # when no key-type is specified, assume rsa
        key_msg, key_data = 'ssh-rsa', user_pubkey
    else:
        raise ValueError('Malformed public key format: {0!r}'
                         .format(user_pubkey))
    try:
        key_bytes = key_data.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError('Malformed public key encoding: {0!r}'
                         .format(key_data))
    decoded_keybytes = paramiko.py3compat.decodebytes(key_bytes)
    try:
        return {'ssh-rsa': paramiko.RSAKey,
                'ssh-dss': paramiko.DSSKey,
                'ecdsa-sha2-nistp256': paramiko.ECDSAKey,
                }.get(key_msg)(data=decoded_keybytes)
    except KeyError:
        raise ValueError('Malformed public key_msg: {0!r}'
                         .format(key_msg))


def check_user_pubkey(username, public_key):
    """ Boolean return when public_key matches user record. """
    from x84.bbs import find_user, get_user
    log = logging.getLogger(__name__)
    handle = find_user(username)
    if handle is None:
        return False
    user_pubkey = get_user(handle).get('pubkey', False)
    if not user_pubkey:
        log.debug('pubkey authentication by {0!r} but no '
                  'public key on record for the user.'
                  .format(username))
        return False
    try:
        stored_pubkey = parse_public_key(user_pubkey)
    except (ValueError, Exception):
        import sys
        (exc_type, exc_value, exc_traceback) = sys.exc_info()
        log.debug('{0} for stored public key of user {1!r}: '
                  '{2}'.format(exc_type, username, exc_value))
    else:
        return stored_pubkey == public_key
