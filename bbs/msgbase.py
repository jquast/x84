"""
Message base for 'The Progressive' BBS.
Copyright (c) 2007 Jeffrey Quast.
$Id: msgbase.py,v 1.21 2009/05/18 03:11:50 dingo Exp $
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

import time
from dbproxy import DBSessionProxy
db = DBSessionProxy('msgbase')

def addmsg(msg):
    msg.send ()

sendmsg = addmsg

def getmsg(number):
    " Retrieve message by number "
    if db.has_key(number):
        return db[number]

def msgexist(number):
    " return True if message exists "
    return db.has_key(number)

def listmsgs(removedeleted=True):
    " return all message records in the database "
    mlist = []
    for number in db.keys():
        if not db[number].deleted:
            mlist.append (db[number])
        elif not removedeleted:
            mlist.append (db[number])
    return mlist

def listpublicmsgs(tags=None):
    " return indexes of all public messages "
    mlist = []
    for msg in listmsgs():
        if msg.public and \
        (( (not tags or tags in msg.tags) \
         and not (msg.draft) \
         or not msg.recipient)):
            mlist.append (msg.number)
    mlist.sort ()
    return mlist

def listprivatemsgs(recipient=None):
    " return indexes of all private messages "
    mlist = []
    for msg in listmsgs():
        if not msg.public \
        and (not recipient or recipient == msg.recipient) \
        and not (msg.draft):
            mlist.append (msg.number)
    mlist.sort ()
    return mlist

def listtags():
    " return list of all tags currently used in system "
    taglist = []
    for i in listpublicmsgs():
        for tag in getmsg(i).tags:
            if tag not in taglist:
                taglist.append (tags)
    taglist.sort ()
    return taglist

def taggedmsgs():
    " return dictionary, keyed by tags, containing list of message indexes "
    tmlist = {}
    for tag in listtags():
        tmlist[tag] = []
    for i in listpublicmsgs():
        msg = getmsg(i)
        for tag in msg.tags:
            tmlist[tag].append (msg.number)
    return tmlist

def tagged(tag):
    " return list of messages found using a tag "
    tm = taggedmsgs()
    if tm.has_key(tag):
        return tm[tag]
    return None

class Msg(dict):
    """
    the Msg object is record spec for messages held in the msgbase.
    It contains many default parameters to describe a conversation:

    .creationtime, the time the message was constructed, fe. msg = Msg(),

    .author, .recipient, .subject, and .body are standard envelope address
    parameters. when .public is set, all eyes may see it.

    .read becomes a list of handles that have viewed a public message, or a
    single time the message was read by the addressed.

    a message is set with .draft=True on creation, and is already stored.
    .draft is set to False on send, unless it is explicitly unset using
    msg.save (draft=True). A message is not recieved by recipients when
    set to True.

    a message may be deleted by setting .deleted=True through the .delete()
    method by passing Force=True

    the .tags method is for use with message groupings, containing a list of
    strings that other messages may share in relation.

    finally, .parent points to the message this message refers to, and .threads
    points to messages that refer to this message. .parent must be explicitly
    set, but children are automaticly populated into .threads[] of messages
    replied to through the send() method.
    """

    def __init__(s, author, recipient='', subject='', body=''):
        # message reference (unique Id)
        s.number = None

        s.creationtime = time.time()
        s.sendtime = None
        s.author = author
        s.recipient = recipient
        s.subject = subject
        s.body = body
        s.public = False
        s.read = False
        s.draft = True
        # set to true to delete
        s.deleted = False
        # tags describe the content of the mail, and can be filtered
        # or subscribed to via msgfilter('tag', ['grapes','green']) function
        s.tags = []
        # list of message indexes, indicating messages
        # that are reffer to this message (children)
        s.threads = []
        # message index of message this instance may
        # refer to (parent)
        s.parent = None

    def save(self, draft=False):
        " store record in message base "
        if draft and not self.draft:
            self.draft = True
        elif not draft:
            self.draft = False

        if db.keys():
            self.number = max(db.keys()) +1
        else:
            print 'first new system message'
            self.number = 0
        db[self.number] = self

    def set(self, key, value):
        " set key, value of msg record "
        self.__setattr__(key, value)
#    self.save ()

    def delete(self, force=False, killer=None):
        " delete message from the database "
        if force and db.has_key(self.number):
            del db[self.number]
        else:
            if killer:
                self.set('deleted', killer)
            else:
                self.set('deleted', True)

    def undelete(self):
        " un-delete a message from the database "
        if self.deleted:
            self.setmsg('deleted', False)
            return True
        return False


    def addtag(self, tag):
        " Add tag to message "
        if not tag in self.tags:
            self.tags.append (tag)
            self.save ()
            return True

    def deltag(self, tag):
        " Remove tag from message "
        if tag in self.tags:
            self.tags.remove (tag)
            self.save ()
            return True

    def readBy(self, handle):
        return (self.public and handle in self.read) \
        or (not self.public and self.recipient == handle and self.read)

    def send(self):
        " Create a new message record in the database "
        self.sendtime = time.time()
        if self.public:
            self.read = []
        else:
            self.read = False
        if self.parent:
            replyto = getmsg(self.parent)
            if not self.number in replyto.threads:
                # append our index to thread in parent message
                replyto.set ('threads', replyto.threads + [self.number])
        self.save ()
