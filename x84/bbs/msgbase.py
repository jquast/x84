"""
msgbase package for x/84, https://github.com/jquast/x84
"""
import logging
import datetime
from x84.bbs.dbproxy import DBProxy

MSGDB = 'msgbase'
TAGDB = 'tags'

# pylint: disable=C0103
#        Invalid name "logger" for type constant (should match
logger = logging.getLogger()


def get_msg(idx=0):
    """
    Return Msg record instance by index ``idx``.
    """
    return DBProxy(MSGDB)['%d' % (idx,)]


def list_msgs(tags=None):
    """
    Return set of Msg keys matching 1 or more ``tags``, or all.
    """
    if tags is not None and 0 != len(tags):
        msgs = set()
        db_tag = DBProxy(TAGDB)
        for tag in (_tag for _tag in tags if _tag in db_tag):
            msgs.update(db_tag[tag])
        return msgs
    return set([int(key) for key in DBProxy(MSGDB).keys()])


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
        self._ctime = datetime.datetime.now()
        self._stime = None
        self.author = getsession().handle
        self.recipient = recipient
        self.subject = subject
        self.body = body
        self.tags = set()
        # reply-to tracking
        self.children = set()
        self.parent = None

    def save(self):
        """
        Save message in 'Msgs' sqlite db, and record index in 'tags' db.
        """
        db_msg = DBProxy(MSGDB)
        new = self.idx is None or self._stime is None
        # persist message record to MSGDB
        db_msg.acquire()
        if new:
            self.idx = max([int(key) for key in db_msg.keys()] or [-1]) + 1
            self._stime = datetime.datetime.now()
            new = True
        db_msg['%d' % (self.idx,)] = self
        db_msg.release()

        # persist message idx to TAGDB
        db_tag = DBProxy(TAGDB)
        db_tag.acquire()
        for tag, msgs in db_tag.iteritems():
            if tag in self.tags and not self.idx in msgs:
                msgs.add(self.idx)
                db_tag[tag] = msgs
                logger.info(u"msg %s tagged '%s'", self.idx, tag,)
            elif tag not in self.tags and self.idx in msgs:
                msgs.remove(self.idx)
                db_tag[tag] = msgs
                logger.info(u"msg %s untagged '%s'", self.idx, tag,)
        for tag in [_tag for _tag in self.tags if not _tag in db_tag]:
            db_tag[tag] = set([self.idx])
        db_tag.release()

        # persist message as child to parent;
        if not hasattr(self, 'parent'):
            self.parent = None
        assert self.parent not in self.children
        if self.parent is not None:
            parent_msg = get_msg(self.parent)
            if not hasattr(parent_msg, 'children'):
                parent_msg.children = set(
                )  # intermediary conversion; deleteme
            parent_msg.children.add(self.idx)
            parent_msg.save()

        logger.info(u"saved %s%s%s, addressed to '%s'.",
                    'new ' if new else u'',
                    'public ' if 'public' in self.tags else u'',
                    'message' if self.parent is None else u'reply',
                    self.recipient,)
