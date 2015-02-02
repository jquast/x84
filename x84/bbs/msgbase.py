""" Messaging database package for x/84. """
# std imports
import datetime
import logging

# local
from x84.bbs.dbproxy import DBProxy
from x84.bbs.session import getsession
from x84.bbs.ini import get_ini

# 3rd party
import dateutil.tz

MSGDB = 'msgbase'
TAGDB = 'tags'
PRIVDB = 'privmsg'

# TODO(jquast, maze): Use modeling to construct rfc-compliant mail messaging
# formats.  It would be possible to use standard mbox-formatted mail boxes,
# and integrate with external systems.  This is a v3.0 release.


def to_localtime(tm_value):
    """ convert given UTC time to local time """
    utcz = dateutil.tz.tzutc()
    locz = dateutil.tz.tzlocal()
    utime = datetime.datetime.strptime(tm_value, '%Y-%m-%d %H:%M:%S')
    utime = utime.replace(tzinfo=utcz)
    ltime = utime.astimezone(locz)
    return ltime.replace(tzinfo=None)


def to_utctime(tm_value):
    """ convert given local time to UTC time """
    utcz = dateutil.tz.tzutc()
    locz = dateutil.tz.tzlocal()
    ltime = tm_value.replace(tzinfo=locz)
    utime = ltime.astimezone(utcz)
    return utime.replace(tzinfo=None).isoformat(' ').partition('.')[0]


def get_origin_line():
    """ Return ``origin`` configuration item of ``[msg]`` section. """
    return get_ini(section='msg', key='origin_line') or (
        'Sent from {0}'.format(
            get_ini(section='system', key='bbsname')))


def format_origin_line():
    """ Format origin line for message quoting. """
    return u''.join((u'\r\n---\r\n', get_origin_line()))


def get_msg(idx=0):
    """ Return Msg record instance by index ``idx``. """
    return DBProxy(MSGDB)['%d' % int(idx)]


def list_msgs(tags=None):
    """ Return set of indices matching ``tags``, or all by default. """
    if tags is not None and 0 != len(tags):
        msgs = set()
        db_tag = DBProxy(TAGDB)
        for tag in (_tag for _tag in tags if _tag in db_tag):
            msgs.update(db_tag[tag])
        return msgs
    return set(int(key) for key in DBProxy(MSGDB).keys())


def list_privmsgs(handle=None):
    """ Return all private messages for given user handle. """
    db_priv = DBProxy(PRIVDB)
    if handle:
        return db_priv.get(handle, set())
    # flatten list of [set(1, 2), set(3, 4)] to set(1, 2, 3, 4)
    return set([_idx for indices in db_priv.values() for _idx in indices])


def list_tags():
    """ Return set of available tags. """
    return [_tag.decode('utf8') for _tag in DBProxy(TAGDB).keys()]


class Msg(object):

    """
    A record spec for messages held in the msgbase.

    It contains many default properties to describe a conversation:

    - ``stime``, the time the message was sent.

    - ``author``, ``recipient``, ``subject``, and ``body`` are envelope
      parameters.

    - ``tags`` is for use with message groupings, containing a list of strings
      that other messages may share in relation.

    - ``parent`` points to the message this message directly refers to.

    - ``children`` is a set of indices replied by this message.
    """

    # pylint: disable=R0902
    #         Too many instance attributes
    @property
    def ctime(self):
        """
        Datetime message was instantiated

        :rtype: datetime.datetime
        """
        return self._ctime

    @property
    def stime(self):
        """
        Datetime message was saved to database

        :rtype: datetime.datetime
        """
        return self._stime

    def __init__(self, recipient=None, subject=u'', body=u''):
        self.author = None
        session = getsession()
        if session:
            self.author = session.user.handle

        self._ctime = datetime.datetime.now()
        self._stime = None
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.tags = set()
        self.children = set()
        self.parent = None
        self.idx = None

    def save(self, send_net=True, ctime=None):
        """
        Save message to database, recording 'tags' db.

        As a side-effect, it may queue message for delivery to
        external systems, when configured.
        """
        log = logging.getLogger(__name__)
        session = getsession()
        use_session = bool(session is not None)
        new = self.idx is None or self._stime is None

        # persist message record to MSGDB
        with DBProxy(MSGDB, use_session=use_session) as db_msg:
            if new:
                self.idx = max(map(int, db_msg.keys()) or [-1]) + 1
                if ctime is not None:
                    self._ctime = self._stime = ctime
                else:
                    self._stime = datetime.datetime.now()
                new = True
            db_msg['%d' % (self.idx,)] = self

        # persist message idx to TAGDB
        with DBProxy(TAGDB, use_session=use_session) as db_tag:
            for tag in db_tag.keys():
                msgs = db_tag[tag]
                if tag in self.tags and self.idx not in msgs:
                    msgs.add(self.idx)
                    db_tag[tag] = msgs
                    log.debug("msg {self.idx} tagged '{tag}'"
                              .format(self=self, tag=tag))
                elif tag not in self.tags and self.idx in msgs:
                    msgs.remove(self.idx)
                    db_tag[tag] = msgs
                    log.info("msg {self.idx} removed tag '{tag}'"
                             .format(self=self, tag=tag))
            for tag in [_tag for _tag in self.tags if _tag not in db_tag]:
                db_tag[tag] = set([self.idx])

        # persist message as child to parent;
        assert self.parent not in self.children, ('circular reference',
                                                  self.parent, self.children)
        if self.parent is not None:
            try:
                parent_msg = get_msg(self.parent)
            except KeyError:
                log.warn('Child message {0}.parent = {1}: '
                         'parent does not exist!'.format(self.idx, self.parent))
            else:
                if self.idx != parent_msg.idx:
                    parent_msg.children.add(self.idx)
                    parent_msg.save()
                else:
                    log.error('Parent idx same as message idx; stripping')
                    self.parent = None
                    with db_msg:
                        db_msg['%d' % (self.idx)] = self

        # persist message record to PRIVDB
        if 'public' not in self.tags:
            with DBProxy(PRIVDB, use_session=use_session) as db_priv:
                db_priv[self.recipient] = (
                    db_priv.get(self.recipient, set()) | set([self.idx]))

        # if either any of 'server_tags' or 'network_tags' are enabled,
        # then queue for potential delivery.
        if send_net and new and (
            get_ini(section='msg', key='network_tags') or
            get_ini(section='msg', key='server_tags')
        ):
            self.queue_for_network()

        log.info(
            u"saved {new} {public_or_private} {message_or_reply}"
            u", addressed to '{self.recipient}'."
            .format(new='new ' if new else '',
                    public_or_private=('public' if 'public' in self.tags
                                       else 'private'),
                    message_or_reply=('message' if self.parent is None
                                      else 'reply'),
                    self=self))

    def queue_for_network(self):
        """ Queue message for networks, hosting or sending. """
        log = logging.getLogger(__name__)

        # check all tags of message; if they match a message network,
        # either record for hosting servers, or schedule for delivery.
        for tag in self.tags:

            # server networks offered by this server,
            # message is for a network we host
            if tag in get_ini(section='msg', key='server_tags', split=True):
                with DBProxy('{0}trans'.format(tag)) as transdb:
                    self.body = u''.join((self.body, format_origin_line()))
                    self.save()
                    transdb[self.idx] = self.idx
                log.info('[{tag}] Stored for network (msgid {self.idx}).'
                         .format(tag=tag, self=self))

            # server networks this server is a member of,
            # message is for a another network, queue for delivery
            elif tag in get_ini(section='msg', key='network_tags', split=True):
                with DBProxy('{0}queues'.format(tag)) as queuedb:
                    queuedb[self.idx] = tag
                log.info('[{tag}] Message (msgid {self.idx}) queued '
                         'for delivery'.format(tag=tag, self=self))
