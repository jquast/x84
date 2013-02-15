"""
msgbase package for x/84, https://github.com/jquast/x84
"""
import datetime
from x84.bbs.dbproxy import DBProxy

MSGDB = DBProxy('Msgs')
TAGDB = DBProxy('tags')


def get_msg(idx):
    """
    Return Msg record by index
    """
    return MSGDB[idx]


def list_msgs(tags=('public',)):
    """
    Return set of Msg record indicies matching 1 or more ``tags``.
    """
    msgs = set()
    for tag in (_tag for _tag in tags if _tag in TAGDB):
        msgs.update(TAGDB[tag])
    return msgs


def list_tags():
    """
    Return set of available tags.
    """
    return TAGDB.keys()


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
    idx = None
    tags = set()

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

    def __init__(self, recipient=None, subject=u'', body=u''):
        from x84.bbs.session import getsession
        self._ctime = datetime.datetime.now()
        self._stime = None
        self.author = getsession().handle
        self.recipient = recipient
        self.subject = subject
        self.body = body

    def save(self):
        """
        Save message in 'Msgs' sqlite db, and record index in 'tags' db.
        """
        MSGDB.acquire()
        msg_idx = max([int(key) for key in MSGDB.keys()] or [-1]) + 1
        self.idx = msg_idx
        self._stime = datetime.datetime.now()
        MSGDB[msg_idx] = self
        MSGDB.release()

        TAGDB.acquire()
        for tag in self.tags:
            if not tag in TAGDB:
                TAGDB[tag] = set([msg_idx])
            else:
                TAGDB[tag].add(msg_idx)
        TAGDB.release()
