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

    # def tag(self, value):
    #    self.tags.update ((value,))

    def save(self):
        """
        Save message to database
        """
        MSGDB.acquire()
        nxt = max([int(key) for key in MSGDB.keys()] or [-1]) + 1
        self.idx = nxt
        self._stime = datetime.datetime.now()
        MSGDB[nxt] = self
        MSGDB.release()

#    def set(self, key, value):
#        " set key, value of msg record "
#        self.__setattr__(key, value)
##    self.save ()
#
#    def delete(self, force=False, killer=None):
#        " delete message from the database "
#        if force and db.has_key(self.number):
#            del db[self.number]
#        else:
#            if killer:
#                self.set('deleted', killer)
#            else:
#                self.set('deleted', True)
#
#    def undelete(self):
#        " un-delete a message from the database "
#        if self.deleted:
#            self.setmsg('deleted', False)
#            return True
#        return False
#
#
#    def addtag(self, tag):
#        " Add tag to message "
#        if not tag in self.tags:
#            self.tags.append (tag)
#            self.save ()
#            return True
#
#    def deltag(self, tag):
#        " Remove tag from message "
#        if tag in self.tags:
#            self.tags.remove (tag)
#            self.save ()
#            return True
#
#    def readBy(self, handle):
#        return (self.public and handle in self.read) \
#        or (not self.public and self.recipient == handle and self.read)
#
#    def send(self):
#        " Create a new message record in the database "
#        self.sendtime = time.time()
#        if self.public:
#            self.read = []
#        else:
#            self.read = False
#        if self.parent:
#            replyto = getmsg(self.parent)
#            if not self.number in replyto.threads:
#                # append our index to thread in parent message
#                replyto.set ('threads', replyto.threads + [self.number])
#        self.save ()
