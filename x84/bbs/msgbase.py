"""
msgbase package for x/84, https://github.com/jquast/x84
"""
import logging
import datetime
import dateutil.tz

MSGDB = 'msgbase'
TAGDB = 'tags'


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
    """ pull the origin line from config """
    from x84.bbs.ini import CFG
    return CFG.get('msg', 'origin_line', 'Sent from {0}'
                   .format(CFG.get('system', 'bbsname')))


def format_origin_line():
    """ format the origin line in preparation for appending to a message """
    return u''.join((u'\r\n---\r\n', get_origin_line()))


def get_msg(idx=0):
    """
    Return Msg record instance by index ``idx``.
    """
    from x84.bbs.dbproxy import DBProxy
    return DBProxy(MSGDB)['%d' % int(idx)]


def list_msgs(tags=None):
    """
    Return set of Msg keys matching 1 or more ``tags``, or all.
    """
    from x84.bbs.dbproxy import DBProxy
    if tags is not None and 0 != len(tags):
        msgs = set()
        db_tag = DBProxy(TAGDB)
        for tag in (_tag for _tag in tags if _tag in db_tag):
            msgs.update(db_tag[tag])
        return msgs
    return set(int(key) for key in DBProxy(MSGDB).keys())


def list_tags():
    """
    Return set of available tags.
    """
    return [_tag.decode('utf8') for _tag in DBProxy(TAGDB).keys()]


class Msg(object):
    """
    the Msg object is record spec for messages held in the msgbase.
    It contains many default properties to describe a conversation:

    'creationtime', the time the message was initialized

    'author', 'recipient', 'subject', and 'body' are envelope parameters.

    'read' becomes a list of handles that have viewed a public message, or a
    single time the message was read by the addressed for private messages.

    'tags' is for use with message groupings, containing a list of strings that
    other messages may share in relation.

    'parent' points to the message this message directly refers to, and
    'threads' points to messages that refer to this message. 'parent' must be
    explicitly set, but children are automaticly populated into 'threads' of
    messages replied to through the send() method.
    """
    # pylint: disable=R0902
    #         Too many instance attributes
    idx = None

    @property
    def ctime(self):
        """
        M.ctime() --> datetime

        Datetime message was instantiated
        """
        return self._ctime

    @property
    def stime(self):
        """
        M.stime() --> datetime

        Datetime message was saved to database
        """
        return self._stime

    def __init__(self, recipient=None, subject=u'', body=u''):
        from x84.bbs.session import getsession
        self.author = None
        session = getsession()
        if session:
            self.author = session.handle

        # msg attributes (todo: create method ..)
        self._ctime = datetime.datetime.now()
        self._stime = None
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.tags = set()
        self.children = set()
        self.parent = None

    def save(self, send_net=True, ctime=None):
        """
        Save message in 'Msgs' sqlite db, and record index in 'tags' db.
        """
        from x84.bbs.dbproxy import DBProxy
        from x84.bbs.ini import CFG
        from x84.bbs import getsession

        session = getsession()
        use_session = True if session is not None else False
        log = logging.getLogger(__name__)
        new = self.idx is None or self._stime is None
        # persist message record to MSGDB
        db_msg = DBProxy(MSGDB, use_session=use_session)
        with db_msg:
            if new:
                self.idx = max([int(key) for key in db_msg.keys()] or [-1]) + 1
                if ctime is not None:
                    self._ctime = self._stime = ctime
                else:
                    self._stime = datetime.datetime.now()
                new = True
            db_msg['%d' % (self.idx,)] = self

        # persist message idx to TAGDB
        db_tag = DBProxy(TAGDB, use_session=use_session)
        with db_tag:
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
        if not hasattr(self, 'parent'):
            self.parent = None
        assert self.parent not in self.children
        if self.parent is not None:
            parent_msg = get_msg(self.parent)
            if self.idx != parent_msg.idx:
                parent_msg.children.add(self.idx)
                parent_msg.save()
            else:
                log.error('Parent idx same as message idx; stripping')
                self.parent = None
                with db_msg:
                    db_msg['%d' % (self.idx)] = self

        if send_net and new and CFG.has_option('msg', 'network_tags'):
            self.queue_for_network()

        log.info(
            u"saved {new}{public}msg {post}, addressed to '{self.recipient}'."
            .format(new='new ' if new else '',
                    public='public ' if 'public' in self.tags else '',
                    post='post' if self.parent is None else 'reply',
                    self=self))

    def queue_for_network(self):
        " Queue message for networks, hosting or sending. "
        from x84.bbs.ini import CFG
        from x84.bbs.dbproxy import DBProxy

        log = logging.getLogger(__name__)
        network_names = CFG.get('msg', 'network_tags')
        member_networks = map(str.strip, network_names.split(','))

        my_networks = []
        if CFG.has_option('msg', 'server_tags'):
            my_netnames = CFG.get('msg', 'server_tags')
            my_networks = map(str.strip, my_netnames.split(','))

        # check all tags of message; if they match a message network,
        # either record for hosting servers, or schedule for delivery.
        for tag in self.tags:
            section = 'msgnet_{tag}'.format(tag=tag)

            # message is for a network we host
            if tag in my_networks:
                section = 'msgnet_{tag}'.format(tag=tag)
                transdb_name = CFG.get(section, 'trans_db_name')
                transdb = DBProxy(transdb_name)
                with transdb:
                    self.body = u''.join((self.body, format_origin_line()))
                    self.save()
                    transdb[self.idx] = self.idx
                log.info('[{tag}] Stored for network (msgid {self.idx}).'
                              .format(tag=tag, self=self))

            # message is for a another network, queue for delivery
            elif tag in member_networks:
                queuedb_name = CFG.get(section, 'queue_db_name')
                queuedb = DBProxy(queuedb_name)
                with queuedb:
                    queuedb[self.idx] = tag
                log.info('[{tag}] Message (msgid {self.idx}) queued '
                              'for delivery'.format(tag=tag, self=self))
