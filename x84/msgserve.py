"""
x84net message network server for x/84, https://github.com/jquast/x84

To configure the message network server, you must first configure the
web server. See webserve.py for more information.

Add 'msgserve' to your 'modules' in the [web] section of default.ini.
Next, you will need to add the tag for the network to the 'server_tags'
attribute of the [msg] section.
Finally, create a section in default.ini with the name of that tag,
prefixed with 'msgnet_'. If your network name is 'x84net', for example,
you would create a [msgnet_x84net] section.

The following attributes are required:
 - trans_db_name: The alphanumeric name of the translation database.
 - keys_db_name: The alphanumeric name of the keys database.
 - source_db_name: The alphanumeric name of the source database.

You must assign each board in the network an ID (an integer) and
a key in the keys database. Use a script invoked by gosub() to
leverage DBProxy for this, like so:

    from x84.bbs import DBProxy, ini.CFG
    db = DBProxy(ini.CFG.get('msgnet_x84net', 'keys_db_name'))
    db.acquire()
    db['1'] = 'somereallylongkey'
    db.release()

Example default.ini settings:

[msg]
# other stuff goes here
server_tags = x84net

[msgnet_x84net]
trans_db_name = x84nettrans
keys_db_name = x84netkeys
source_db_name = x84netsrc
"""

import web

class MessageNetworkServer():
    """ server queues and locking mechanism """
    iqueue = None
    oqueue = None
    lock = None

class messages():
    """
    message network server api endpoint
    """

    def GET(self, network, last):
        """ GET method - pull messages """
        import json
        import Queue
        import logging

        logger = logging.getLogger()

        if len(last) <= 0:
            last = 0
        else:
            last = int(last)

        if not 'HTTP_AUTH_X84NET' in web.ctx.env.keys():
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        data = {
            'auth': web.ctx.env['HTTP_AUTH_X84NET']
            , 'network': network
            , 'action': 'pull'
            , 'last': last
        }

        MessageNetworkServer.lock.acquire()
        MessageNetworkServer.iqueue.put(data)

        try:
            response = MessageNetworkServer.oqueue.get(True, 60)
        except Queue.Empty:
            logger.error(u'Empty queue')
            raise web.HTTPError('500 Server Error', {}, json.dumps({u'response': False, u'message': u'No response'}))
        finally:
            MessageNetworkServer.lock.release()

        try:
            return json.dumps(response)
        except:
            logger.error(u'Unable to serialize: %r' % response)
            raise web.HTTPError('500 Server Error', {}, json.dumps({u'response': False, u'message': u'Error'}))

    def PUT(self, network, null):
        """ PUT method - post messages """
        import json
        import Queue
        import logging

        logger = logging.getLogger()

        if not 'HTTP_AUTH_X84NET' in web.ctx.env.keys():
            logger.error(u'Unauthorized connection')
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        webdata = web.input()

        data = {
            'auth': web.ctx.env['HTTP_AUTH_X84NET']
            , 'network': network
            , 'action': 'push'
            , 'message': json.loads(webdata.message)
        }

        MessageNetworkServer.lock.acquire()
        MessageNetworkServer.iqueue.put(data)

        try:
            response = MessageNetworkServer.oqueue.get(True, 60)
        except Queue.Empty:
            logger.error(u'Empty queue')
            raise web.HTTPError('500 Server Error', {}, json.dumps({u'response': False, u'message': u'No response'}))
        finally:
            MessageNetworkServer.lock.release()

        try:
            return json.dumps(response)
        except:
            logger.error(u'Unable to serialize: %r' % response)
            raise web.HTTPError('500 Server Error', {}, json.dumps({u'response': False, u'message': u'Error'}))

"""
functions for processing the request within x84
"""

def server_error(logger, queue, logtext, message=None):
    """ helper method for logging and returning errors """
    if message is None:
        message = logtext
    logger.error(logtext)
    queue.put({u'response': False, u'message': message})

def main():
    """ server request handling process """
    from x84.bbs import ini, msgbase, DBProxy, getsession, echo, getterminal
    from x84.bbs.msgbase import to_utctime, to_localtime, Msg
    import hashlib
    import time
    import logging
    import json
    import Queue

    session = getsession()
    logger = logging.getLogger()
    term = getterminal()

    try:
        data = MessageNetworkServer.iqueue.get(True, 60)
    except Queue.Empty:
        return

    queue = MessageNetworkServer.oqueue

    if 'network' not in data.keys():
        server_error(logger, queue, u'Network not specified')
        return

    if 'action' not in data.keys():
        server_error(logger, queue, u'[%s] Action not specified' % data['network'], u'No action given')
        return

    if 'auth' not in data.keys():
        server_error(logger, queue, u'[%s] Auth token missing' % data['network'], u'No auth token given')
        return

    auth = data['auth'].split('|')

    if len(auth) != 3:
        server_error(logger, queue, u'[%s] Improper token' % data['network'], u'Bad token given')
        return

    board_id = int(auth[0])
    token = auth[1]
    when = int(auth[2])
    now = int(time.time())
    netcfg = 'msgnet_%s' % data['network']
    logger.debug(u"[%s] client %d connecting for %s" % (data['network'], board_id, data['action']))

    if not ini.CFG.has_option(netcfg, 'keys_db_name'):
        server_error(logger, queue, u'[%s] No keys database config' % data['network'], u'Server error')
        return

    keysdb = DBProxy(ini.CFG.get(netcfg, 'keys_db_name'))

    if str(board_id) not in keysdb.keys():
        server_error(logger, queue, u'[%s] No such key for this network' % data['network'], u'Invalid key')
        return

    board_key = keysdb[str(board_id)]

    if when > now or now - when > 15:
        server_error(logger, queue, u'[%s] Expired token' % data['network'], u'Expired token')
        return

    if token != hashlib.sha256('%s%d' % (board_key, when)).hexdigest():
        server_error(logger, queue, u'[%s] Invalid token' % data['network'], u'Bad token')
        return

    if not ini.CFG.has_option(netcfg, 'source_db_name'):
        server_error(logger, queue, u'[%s] Source DB not configured' % data['network'], u'Server error')
        return

    if not ini.CFG.has_option(netcfg, 'trans_db_name'):
        server_error(logger, queue, u'[%s] Translation DB not configured' % data['network'], u'Server error')
        return

    tagdb = DBProxy(msgbase.TAGDB)
    msgdb = DBProxy(msgbase.MSGDB)
    sourcedb = DBProxy(ini.CFG.get(netcfg, 'source_db_name'))
    transdb = DBProxy(ini.CFG.get(netcfg, 'trans_db_name'))

    if data['action'] == 'pull':

        """ client is requesting to pull messages """

        if data['network'] not in tagdb.keys():
            queue.put({u'response': True, u'messages': []})
            return

        msgs = list()
        last = None

        if 'last' in data.keys():
            last = int(data['last'])

        count = 0

        for m in tagdb[data['network']]:
            if count == 20:
                logger.info(u'Too many messages, sending partial response')
                break

            if last != None and int(m) <= last:
                continue

            count += 1
            msg = msgdb[m]

            # don't pull messages that the client posted
            if sourcedb.has_key(msg.idx) and sourcedb[msg.idx] == int(board_id):
                continue

            pushmsg = {
                u'id': msg.idx
                , u'author': msg.author
                , u'recipient': msg.recipient
                , u'parent': msg.parent
                , u'subject': msg.subject
                , u'tags': [tag for tag in msg.tags if tag != data['network']]
                , u'ctime': to_utctime(msg.ctime)
                , u'body': msg.body
            }
            msgs.append(pushmsg)

        howmany = len(msgs)

        if howmany > 0:
            logger.info(u'[%s] Delivered %d messages to board %d' % (data['network'], howmany, int(board_id)))

        queue.put({u'response': True, u'messages': msgs})
    elif data['action'] == 'push':

        """ client is requesting to push messages """

        if 'message' not in data.keys():
            server_error(logger, queue, u'No message')
            return

        pullmsg = data['message']

        for k in [u'author', u'recipient', u'subject', u'parent', u'tags', u'ctime', u'body']:
            if k not in pullmsg.keys():
                server_error(logger, queue, u'Missing %s' % k)
                return

        msg = Msg()
        msg.author = pullmsg['author']
        msg.recipient = pullmsg['recipient']
        msg.subject = pullmsg['subject']
        msg.parent = pullmsg['parent']
        msg.tags = set(pullmsg['tags'] + [data['network']])
        msg.body = pullmsg['body']
        msg.save(noqueue=True, ctime=to_localtime(pullmsg['ctime'].partition('.')[0]))
        sourcedb.acquire()
        transdb.acquire()
        sourcedb[msg.idx] = board_id
        transdb[msg.idx] = msg.idx
        sourcedb.release()
        transdb.release()
        queue.put({u'response': True, u'id': msg.idx})
    else:
        server_error(logger, queue, u'Unknown action: %s' % data['action'])
