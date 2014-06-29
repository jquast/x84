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

INQUEUE = None
OUTQUEUE = None
LOCK = None
QUEUE_TIMEOUT = 60
EMPTY_ERR = {u'response': False, u'message': u'No response'}


import web


class messages():
    """
    message network server api endpoint
    """

    def GET(self, network, last):
        """ GET method - pull messages """
        import json
        import Queue
        import logging
        from x84.webserve import queues, locks

        global INQUEUE, OUTQUEUE, LOCK, QUEUE_TIMEOUT
        logger = logging.getLogger()

        if len(last) <= 0:
            last = 0
        else:
            last = int(last)

        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        data = {
            'auth': web.ctx.env['HTTP_AUTH_X84NET'],
            'network': network,
            'action': 'pull',
            'last': last,
        }

        locks[LOCK].acquire()
        queues[INQUEUE].put(data)
        try:
            response = queues[OUTQUEUE].get(True, QUEUE_TIMEOUT)
        except Queue.Empty:
            logger.error(u'Empty queue')
            raise web.HTTPError('500 Server Error', {}, json.dumps(EMPTY_ERR))
        finally:
            locks[LOCK].release()

        try:
            return json.dumps(response)
        except:
            logger.error(u'Unable to serialize: %r' % response)
            raise web.HTTPError('500 Server Error', {}, json.dumps(EMPTY_ERR))

    def PUT(self, network, *args):
        """ PUT method - post messages """
        import json
        import Queue
        import logging
        from x84.webserve import queues, locks

        global INQUEUE, OUTQUEUE, LOCK, QUEUE_TIMEOUT
        logger = logging.getLogger()

        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            logger.error(u'Unauthorized connection')
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        webdata = web.input()

        data = {
            'auth': web.ctx.env['HTTP_AUTH_X84NET'],
            'network': network,
            'action': 'push',
            'message': json.loads(webdata.message)
        }

        locks[LOCK].acquire()
        queues[INQUEUE].put(data)

        try:
            response = queues[OUTQUEUE].get(True, QUEUE_TIMEOUT)
        except Queue.Empty:
            logger.error(u'Empty queue')
            raise web.HTTPError('500 Server Error', {}, json.dumps(EMPTY_ERR))
        finally:
            locks[LOCK].release()

        try:
            return json.dumps(response)
        except:
            logger.error(u'Unable to serialize: {0!r}'.format(response))
            raise web.HTTPError('500 Server Error', {}, json.dumps(EMPTY_ERR))


# functions for processing the request within x84
def server_error(log, queue, msg, http_msg=None):
    """ helper method for logging and returning errors """
    http_msg = http_msg or msg
    log.error(msg)
    queue.put({u'response': False, u'message': http_msg})


def main():
    """ server request handling process """
    from x84.bbs import ini, msgbase, DBProxy
    from x84.bbs.msgbase import to_utctime, to_localtime, Msg
    from x84.webserve import queues
    import hashlib
    import time
    import logging
    import Queue

    global INQUEUE, OUTQUEUE, LOCK, QUEUE_TIMEOUT
    log = logging.getLogger()

    try:
        data = queues[INQUEUE].get(True, QUEUE_TIMEOUT)
    except Queue.Empty:
        return

    queue = queues[OUTQUEUE]

    if 'network' not in data:
        server_error(log=log, queue=queue,
                     msg=u'Network not specified')
        return

    if 'action' not in data:
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]}] Action not specified'
                          .format(data=data)),
                     http_msg=u'No action given')
        return

    if 'auth' not in data:
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]}] Auth token missing'
                          .format(data=data)),
                     http_msg=u'No auth token given')
        return

    auth = data['auth'].split('|')

    if len(auth) != 3:
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]}] Improper token'
                          .format(data=data)),
                     http_msg=u'Bad token given')
        return

    board_id = int(auth[0])
    token = auth[1]
    when = int(auth[2])
    now = int(time.time())
    netcfg = 'msgnet_%s' % data['network']
    log.debug(u"[{data[network]] client {board_id} request for {data[action]}"
              .format(data=data, board_id=board_id))

    if not ini.CFG.has_option(netcfg, 'keys_db_name'):
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]}] No keys database config'
                          .format(data=data)),
                     http_msg=u'Server error')
        return

    keysdb = DBProxy(ini.CFG.get(netcfg, 'keys_db_name'))

    if str(board_id) not in keysdb.keys():
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]}] No such key for this network'
                          .format(data=data)),
                     http_msg=u'Invalid key')
        return

    board_key = keysdb[str(board_id)]

    if when > now or now - when > 15:
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]} Expired token'
                          .format(data=data)),
                     http_msg=u'Expired token')
        return

    if token != hashlib.sha256('%s%d' % (board_key, when)).hexdigest():
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]} Invalid token'
                          .format(data=data)),
                     http_msg=u'Bad token')
        return

    if not ini.CFG.has_option(netcfg, 'source_db_name'):
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]} Source DB not configured'
                          .format(data=data)),
                     http_msg=u'Server error')
        return

    if not ini.CFG.has_option(netcfg, 'trans_db_name'):
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]} Translation DB not configured'
                          .format(data=data)),
                     http_msg=u'Server error')
        return

    tagdb = DBProxy(msgbase.TAGDB)
    msgdb = DBProxy(msgbase.MSGDB)
    sourcedb = DBProxy(ini.CFG.get(netcfg, 'source_db_name'))
    transdb = DBProxy(ini.CFG.get(netcfg, 'trans_db_name'))

    # XXX to sub-func
    if data['action'] == 'pull':
        # client is requesting to pull messages

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
                log.info(u'Too many messages, sending partial response')
                break

            if last != None and int(m) <= last:
                continue

            count += 1
            msg = msgdb[m]

            # don't pull messages that the client posted
            if sourcedb.has_key(msg.idx) and sourcedb[msg.idx] == int(board_id):
                continue

            pushmsg = {
                u'id': msg.idx,
                u'author': msg.author,
                u'recipient': msg.recipient,
                u'parent': msg.parent,
                u'subject': msg.subject,
                u'tags': [tag for tag in msg.tags if tag != data['network']],
                u'ctime': to_utctime(msg.ctime),
                u'body': msg.body
            }
            msgs.append(pushmsg)

        howmany = len(msgs)

        if howmany > 0:
            log.info(u'[{data[network]} {num} msgs sent to board_id {board_id}'
                     .format(data=data, num=howmany, board_id=board_id))

        queue.put({u'response': True, u'messages': msgs})

    elif data['action'] == 'push':
        # client is requesting to push messages

        if 'message' not in data.keys():
            server_error(log, queue, u'No message')
            return

        pullmsg = data['message']

        # validate
        for key in (u'author', u'recipient', u'subject', u'parent',
                    u'tags', u'ctime', u'body', ):
            if key not in pullmsg.keys():
                server_error(log=log, queue=queue,
                             msg=(u'Missing key in message: {key}'
                                  .format(key=key)))
                return

        msg = Msg()
        msg.author = pullmsg['author']
        msg.recipient = pullmsg['recipient']
        msg.subject = pullmsg['subject']
        msg.parent = pullmsg['parent']
        msg.tags = set(pullmsg['tags'] + [data['network']])
        msg.body = pullmsg['body']
        msg.save(noqueue=True,
                 ctime=to_localtime(pullmsg['ctime'].partition('.')[0]))
        sourcedb.acquire()
        transdb.acquire()
        sourcedb[msg.idx] = board_id
        transdb[msg.idx] = msg.idx
        sourcedb.release()
        transdb.release()
        queue.put({u'response': True, u'id': msg.idx})
    else:
        server_error(log=log, queue=queue,
                     msg=(u'[{data[network]}] Unknown action, {data[action]!r}'
                          .format(data=data)),
                     http_msg=(u'Unknown action, {data[action]!r}'
                               .format(data=data)))


def web_module():
    """ Setup the module and return a dict of its REST API """
    from threading import Lock
    from multiprocessing import Queue
    from x84.webserve import queues, locks
    from x84.bbs.telnet import connect_bot

    global INQUEUE, OUTQUEUE, LOCK
    queues[INQUEUE] = Queue()
    queues[OUTQUEUE] = Queue()
    locks[LOCK] = Lock()
    connect_bot(u'msgserve')

    return {
        'urls': ('/messages/([^/]+)/([^/]*)/?', 'messages'),
        'funcs': {
            'messages': messages
        }
    }
