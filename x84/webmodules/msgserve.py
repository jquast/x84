"""
x84net message network web host for x/84, https://github.com/jquast/x84

This is a RESTful API server. Data is represented as JSON.

To configure the message network server, you must first configure the
web server. See x84/webserve.py for more information.

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

Example default.ini settings:

[msg]
# The name of the message networks hosted
server_tags = x84net

[msgnet_x84net]
trans_db_name = x84nettrans
keys_db_name = x84netkeys
source_db_name = x84netsrc
"""
import multiprocessing
import threading
import logging
import hashlib
import Queue
import json
import time
import web

# global singletons configured by engine ...
INQUEUE = None
OUTQUEUE = None
LOCK = None

#: maximum time for serving requests until giving up
QUEUE_TIMEOUT = 60

#: response for general errors
RESP_FAIL = json.dumps({u'response': False, u'message': u'Error'})

#: token validation time in seconds
AUTH_EXPIREY = 15

#: maximum number of messages to reply in batches
BATCH_MSGS = 20

#: primary json fields
VALIDATE_FIELDS = ('network', 'action', 'auth',)

#: sub-fields of 'message'
VALIDATE_MSG_KEYS = (u'author', u'recipient', u'subject',
                     u'parent', u'tags', u'ctime', u'body', )

#: required ini configuration options for section msgnet_{network_name}
# todo: should generate database names, not require configuration
VALIDATE_CFG = ('keys_db_name', 'source_db_name', 'trans_db_name',)


def parse_auth(request_data):
    """
    Parse and return tuple of 'auth' token if valid.
    Otherwise, throw ValueError.
    """
    board_id, token, when = request_data.get('auth', '').split('|')
    when = int(when)
    if time.time() > when + AUTH_EXPIREY:
        raise ValueError('Token is from the future')
    elif time.time() - when > AUTH_EXPIREY:
        raise ValueError('Token too far in the past')
    return (board_id, token, when)


class MessageApi(object):
    " message network web API endpoint "

    # todo: validate messages much earlier (here, not below the scissor-line)

    def GET(self, network, last):
        " GET method - pull messages "
        log = logging.getLogger(__name__)
        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            log.error(u'Unauthorized connection')
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        # prepare request for message, last is the highest
        # index previously received by client
        return self._get_response(data={
            'auth': web.ctx.env['HTTP_AUTH_X84NET'],
            'network': network,
            'action': 'pull',
            'last': max(0, int(last)),
        })

    def PUT(self, network, *args):
        " PUT method - post messages "
        log = logging.getLogger(__name__)
        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            log.error(u'Unauthorized connection')
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        # parse incoming message
        webdata = web.input()
        return self._get_response(data={
            'auth': web.ctx.env['HTTP_AUTH_X84NET'],
            'network': network,
            'action': 'push',
            'message': json.loads(webdata.message)
        })

    @staticmethod
    def _get_response(data):
        """ Acquire web server lock and queue request ``data``
            to internal "bots" service via queues[INQUEUE], blocking
            until a response is received in queues[OUTQUEUE].

            Serialize as json and return.
        """
        from x84.webserve import queues, locks
        log = logging.getLogger(__name__)
        receive_queue, return_queue = queues[INQUEUE], queues[OUTQUEUE]

        # acquire lock,
        with locks[LOCK]:
            receive_queue.put(data)
            try:
                # blocking request for server to process message
                response_data = return_queue.get(True, QUEUE_TIMEOUT)
            except Queue.Empty:
                # we should tell the client we gave up, or earmark with an ID,
                # otherwise high server load or denial-of-service would cause
                # us to serve the last client's request to the next.
                log.error('Server did not process request, is it dead?')
                raise web.HTTPError('500 Server Error', {}, RESP_FAIL)

        # return request for message as json
        try:
            return json.dumps(response_data)
        except ValueError as err:
            log.error('{err}: response_data={response_data!r}'.format(
                err=err, response_data=response_data))
            raise web.HTTPError('500 Server Error', {}, RESP_FAIL)

def web_module():
    """
    Setup the module and return a dict of its REST API.

    Called only once on server start.
    """
    from x84.webserve import queues, locks
    from x84.bbs.telnet import connect_bot

    # Create receive_queue and return_queue (INQUEUE, OUTQUEUE) of
    # global singleton 'queues' and 'locks' of x84.webserve. todo:
    # rename to simply RECEIVE_QUEUE and RETURN_QUEUE. Better: use
    # the full-duplex event queue and locks that god gave us in
    # engine.py
    global queues, locks
    queues[INQUEUE] = multiprocessing.Queue()
    queues[OUTQUEUE] = multiprocessing.Queue()
    locks[LOCK] = threading.Lock()
    connect_bot(u'msgserve')

    return {
        'urls': ('/messages/([^/]+)/([^/]*)/?', 'messages'),
        'funcs': {
            'messages': MessageApi
        }
    }

# You may pretend this file is split into two execution halves.
# The above receives messages from web api clients and forwards
# their requests into the receive_queue and blocks reading
# for a response from the return_queue.
#
# scissor cut .............8=X---------------------------------
#
# While below, this runs currently as a "bot" (actually, a telnet
# client session, believe it or not) that serves responses, such
# as retrieving messages or storing new ones, and sends a response
# back to the web api through the return_queue.


def server_error(log_func, return_queue, log_msg, http_msg=None):
    " helper method for logging and returning errors "
    http_msg = http_msg or log_msg
    log_func(log_msg)
    return_queue.put({u'response': False, u'message': http_msg})


def serve_messages_for(board_id, request_data, return_queue, db_source):
    " Reply-to api client request to receive new messages. "
    from x84.bbs import DBProxy, msgbase
    from x84.bbs.msgbase import to_utctime
    log = logging.getLogger(__name__)
    #log.error(msg)
    db_tags = DBProxy(msgbase.TAGDB)
    db_messages = DBProxy(msgbase.MSGDB)

    def message_owned_by(msg_id, board_id):
        return (msg_id in db_source and
                db_source[msg_id] == board_id)

    def msgs_after(idx=None):
        for msg_id in db_tags.get(request_data['network'], []):
            if idx is None:
                yield db_messages[idx]
            elif (int(msg_id) > int(idx) and
                  not message_owned_by(msg_id, board_id)):
                yield db_messages[idx]

    last_seen = request_data.get('last', None)
    pending_messages = msgs_after(last_seen)
    return_messages = list()
    num_sent = 0
    for num_sent, msg in enumerate(pending_messages):
        return_messages.append({
            u'id': msg.idx,
            u'author': msg.author,
            u'recipient': msg.recipient,
            u'parent': msg.parent,
            u'subject': msg.subject,
            u'tags': list(msg.tags ^ set([request_data['network']])),
            u'ctime': to_utctime(msg.ctime),
            u'body': msg.body
        })
        if num_sent >= BATCH_MSGS:
            log.warn('[{request_data[network]}] Batch limit reached for '
                     'board {board_id}; halting'
                     .format(request_data=request_data, board_id=board_id))
            break

    if num_sent > 0:
        log.info('[{request_data[network]}] {num_sent} messages '
                 'served to {board_id}'.format(request_data=request_data,
                                               num_sent=num_sent,
                                               board_id=board_id))

    return_queue.put({u'response': True, u'messages': return_messages})


def receive_message_from(board_id, request_data, return_queue,
                         db_source, db_transactions):
    " Reply-to api client request to post a new message. "
    from x84.bbs.msgbase import to_localtime, Msg
    log = logging.getLogger(__name__)

    if 'message' not in request_data:
        return server_error(log.info, return_queue, u'No message')

    pullmsg = request_data['message']

    # validate
    for key in (_key for _key in VALIDATE_MSG_KEYS if _key not in pullmsg):
        return server_error(log_func=log.info, return_queue=return_queue,
                            log_msg=('Missing message sub-field, {key!r}'
                                     .format(key=key)))

    msg = Msg()
    msg.author = pullmsg['author']
    msg.recipient = pullmsg['recipient']
    msg.subject = pullmsg['subject']
    msg.parent = pullmsg['parent']
    msg.tags = set(pullmsg['tags'] + [request_data['network']])
    msg.body = pullmsg['body']
    # ?? is this removing millesconds, or ?
    _ctime = to_localtime(pullmsg['ctime'].split('.', 1)[0])
    msg.save(send_net=False, ctime=_ctime)
    with db_source, db_transactions:
        db_source[msg.idx] = board_id
        db_transactions[msg.idx] = msg.idx
    return_queue.put({u'response': True, u'id': msg.idx})


def main():
    """
    Serve one API server request and return.
    """
    # todo: The caller runs a while loop .. this should be a script
    # that does a while loop and imports x84.webserve.

    from x84.bbs import ini, DBProxy
    from x84.webserve import queues
    log = logging.getLogger(__name__)

    receive_queue, return_queue = queues[INQUEUE], queues[OUTQUEUE]
    try:
        request_data = receive_queue.get(True, QUEUE_TIMEOUT)
    except Queue.Empty:
        return

    # validate primary json request keys
    for key in (_key for _key in VALIDATE_FIELDS
                if _key not in request_data):
        return server_error(log_func=log.warn,
                            return_queue=return_queue,
                            log_msg='Missing field, {key!r}'.format(key=key))

    # validate message network & configuration.
    section = 'msgnet_{data[network]}'.format(data=request_data)
    for option in VALIDATE_CFG:
        if not ini.CFG.has_option(section, option):
            return server_error(log_func=log.warn,
                                return_queue=return_queue,
                                log_msg=('[{data[network]}] missing config '
                                         'for section [{section}]: {option!r}'
                                         .format(data=request_data,
                                                 section=section,
                                                 option=option)),
                                http_msg=u'Server error')

    # validate authentication token
    try:
        board_id, token, auth_tmval = parse_auth(request_data)
    except ValueError, err:
        return server_error(log_func=log.warn,
                            return_queue=return_queue,
                            log_msg=('[{data[network]}] Bad token: {err}'
                                     .format(data=request_data, err=err)),
                            http_msg=u'Invalid token')
    else:
        log.debug('[{data[network]}] client {board_id} request '
                  '{data[action]}'.format(data=request_data,
                                          board_id=board_id))

    # validate board auth-key
    keysdb = DBProxy(ini.CFG.get(section, 'keys_db_name'))
    try:
        client_key = keysdb[board_id]
    except KeyError:
        return server_error(log_func=log.warn,
                            return_queue=return_queue,
                            log_msg=('[{data[network]}] board_id={board_id} '
                                     ': No such key for this network'
                                     .format(data=request_data,
                                             board_id=board_id)),
                            http_msg=u'board_id not valid for this server.')
    else:
        server_key = hashlib.sha256('{0}{1}'.format(client_key, auth_tmval))
        if token != server_key.hexdigest():
            return server_error(log_func=log.warn,
                                return_queue=return_queue,
                                log_msg=('[{data[network]}] auth-key mismatch'
                                         .format(data=request_data)),
                                http_msg=u'Invalid token')

    # these need to be better named for their transmission direction,
    # its very clear how they are consumed as they are currently named.
    db_source = DBProxy(ini.CFG.get(section, 'source_db_name'))
    db_transactions = DBProxy(ini.CFG.get(section, 'trans_db_name'))

    if request_data.get('action', None) == 'pull':
        # client is requesting to pull messages
        serve_messages_for(board_id=board_id,
                           request_data=request_data,
                           return_queue=return_queue,
                           db_source=db_source)

    elif request_data.get('action', None) == 'push':
        # client is sending a message to the network
        receive_message_from(board_id=board_id,
                             request_data=request_data,
                             return_queue=return_queue,
                             db_source=db_source,
                             db_transactions=db_transactions)

    else:
        server_error(log_func=log.info, return_queue=return_queue,
                     log_msg=('[{data[network]}] Unknown action, {data[action]!r}'
                              .format(data=request_data)),
                     http_msg=('action {data[action]!r} invalid.'
                               .format(data=request_data)))
# XX this should be automatic. cryptography.Fernet.generate_key()
# XX 'somereallylongkey' encourages not very strong keys ..
#
# You must assign each board in the network an ID (an integer) and
# a key in the keys database. Use a script invoked by gosub() to
# leverage DBProxy for this, like so:
#
#     from x84.bbs import DBProxy, ini.CFG
#     db = DBProxy(ini.CFG.get('msgnet_x84net', 'keys_db_name'))
#     db.acquire()
#     db['1'] = 'somereallylongkey'
#     db.release()
# XX
# XX
