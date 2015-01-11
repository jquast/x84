"""
x84net message network web host for x/84, https://github.com/jquast/x84

This is a RESTful API server. Data is represented as JSON.

To configure the message network server, you must first configure the
web server. See x84/webserve.py for more information.

Add 'msgserve' to your 'modules' in the [web] section of default.ini.

Then, you must create a 'tag', that is, name your message network(s),
with a comma-delimited list of ``server_tags`` of the ``[msg]``
section.  The name of this tag will become the prefix of a series of
database files, and must be named appropriately (that is, contain
only alphanumerics).

Example default.ini settings:

[msg]
# The name of the message networks hosted
server_tags = x84net
"""
import logging
import hashlib
import json
import time
import web

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


def parse_auth(request_data):
    """
    Parse and return tuple of 'auth' token if valid.

    :raises ValueError:  token is too far from future or past.
    """
    board_id, token, when = request_data.get('auth', '').split('|')
    when = int(when)
    if time.time() > when + AUTH_EXPIREY:
        raise ValueError('Token is from the future')
    elif time.time() - when > AUTH_EXPIREY:
        raise ValueError('Token too far in the past')
    return (board_id, token, when)


class MessageApi(object):

    """ message network web API endpoint """

    # todo: validate messages much earlier (here, not below the scissor-line)

    def GET(self, network, last):
        " GET method - pull messages "
        log = logging.getLogger(__name__)
        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            log.error(u'Unauthorized connection')
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        # prepare request for message, last is the highest
        # index previously received by client
        response_data = get_response(request_data={
            'auth': web.ctx.env['HTTP_AUTH_X84NET'],
            'network': network,
            'action': 'pull',
            'last': max(0, int(last)),
        })

        # return response data as json (200 OK)
        return self._jsonify(response_data, log)

    def PUT(self, network, *args):
        " PUT method - post messages "
        log = logging.getLogger(__name__)
        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            log.error(u'Unauthorized connection')
            raise web.HTTPError('401 Unauthorized', {}, 'Unauthorized')

        # parse incoming message
        webdata = web.input()
        response_data = get_response(request_data={
            'auth': web.ctx.env['HTTP_AUTH_X84NET'],
            'network': network,
            'action': 'push',
            'message': json.loads(webdata.message)
        })

        # return response data as json
        return self._jsonify(response_data, log)

    @staticmethod
    def _jsonify(response_data, log):
        try:
            return json.dumps(response_data)
        except ValueError as err:
            log.error('{err}: response_data={response_data!r}'.format(
                err=err, response_data=response_data))
            raise web.HTTPError('500 Server Error', {}, RESP_FAIL)


def web_module():
    """
    Return dictionary of url routes and function mappings for this module.

    Called by x84/webserve.py on server start.
    """
    return {
        'urls': ('/messages/([^/]+)/([^/]*)/?', 'messages'),
        'funcs': {
            'messages': MessageApi
        }
    }

# Above is the module definition.
#
# ---8<---
#
# Below is the method for serving requests and some helper funcs.


def server_error(log_func, log_msg, status, http_msg=None):
    """
    Helper function for logging and returning web.HTTPError.

    :param callable log_func: logging function.
    :param str log_msg: log message.
    :param int status: HTTP status code.
    :param str http_msg: HTTP response body.
    :returns: exception object that should be raised by caller.
    :rtype: web.HTTPError
    """
    http_msg = http_msg or log_msg
    log_func('{0} {1}'.format(status, log_msg))
    web.ctx.status = status
    return {u'response': False, u'message': http_msg}


def serve_messages_for(board_id, request_data, db_source):
    " Reply-to api client request to receive new messages. "
    from x84.bbs import DBProxy, msgbase
    from x84.bbs.msgbase import to_utctime
    log = logging.getLogger(__name__)
    # log.error(msg)
    db_tags = DBProxy(msgbase.TAGDB, use_session=False)
    db_messages = DBProxy(msgbase.MSGDB, use_session=False)

    def message_owned_by(msg_id, board_id):
        return (msg_id in db_source and
                db_source[msg_id] == board_id)

    def msgs_after(idx=None):
        for msg_id in db_tags.get(request_data['network'], []):
            if idx is None:
                yield db_messages[idx]
            elif (int(msg_id) > int(idx) and
                  not message_owned_by(msg_id, board_id)):
                yield db_messages[msg_id]

    last_seen = request_data.get('last', None)
    pending_messages = msgs_after(last_seen)
    return_messages = list()
    num_sent = 0
    for num_sent, msg in enumerate(pending_messages, start=1):
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

    return {u'response': True, u'messages': return_messages}


def receive_message_from(board_id, request_data,
                         db_source, db_transactions):
    " Reply-to api client request to post a new message. "
    from x84.bbs.msgbase import to_localtime, Msg
    log = logging.getLogger(__name__)

    if 'message' not in request_data:
        return server_error(log.info, u'No message', 400)  # bad request

    pullmsg = request_data['message']

    # validate
    for key in (_key for _key in VALIDATE_MSG_KEYS if _key not in pullmsg):
        return server_error(
            log_func=log.info,
            log_msg=('Missing message sub-field, {key!r}'
                     .format(key=key)),
            status=400,  # bad request
        )

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

    web.ctx.status = '201 Created'
    return {u'response': True, u'id': msg.idx}


def get_response(request_data):
    """ Serve one API server request and return. """
    # todo: The caller runs a while loop .. this should be a script
    # that does a while loop and imports x84.webserve.

    from x84.bbs import DBProxy, get_ini
    log = logging.getLogger(__name__)

    # validate primary json request keys
    for key in (_key for _key in VALIDATE_FIELDS
                if _key not in request_data):
        return server_error(
            log_func=log.warn,
            log_msg=('Missing field, {key!r}, request_data={data!r}'
                     .format(key=key, data=request_data)),
            status=400,  # bad request
        )

    # validate this server offers such message network
    server_tags = get_ini(section='msg', key='server_tags', split=True)

    if not request_data['network'] in server_tags:
        return server_error(
            log_func=log.warn,
            log_msg=('[{data[network]}] not in server_tags ({server_tags})'
                     .format(data=request_data, server_tags=server_tags)),
            http_msg=u'Server error',
            status=404,  # not found
        )
    tag = request_data['network']

    # validate authentication token
    try:
        board_id, token, auth_tmval = parse_auth(request_data)
    except ValueError, err:
        return server_error(
            status=401,  # unauthorized
            log_func=log.warn,
            log_msg=('[{data[network]}] Bad token: {err}'
                     .format(data=request_data, err=err)),
            http_msg=u'Invalid auth token')
    else:
        log.debug('[{data[network]}] board_id={board_id} request'
                  ': {data[action]}'.format(data=request_data,
                                            board_id=board_id))

    # validate board auth-key
    keysdb = DBProxy('{0}keys'.format(tag), use_session=False)
    try:
        client_key = keysdb[board_id]
    except KeyError:
        return server_error(
            log_func=log.warn,
            log_msg=('[{data[network]}] board_id={board_id}'
                     ': No such key for this network'
                     .format(data=request_data,
                             board_id=board_id)),
            http_msg=u'board_id not valid for this server.',
            status=401,  # unauthorized
        )
    else:
        server_key = hashlib.sha256('{0}{1}'.format(client_key, auth_tmval))
        if token != server_key.hexdigest():
            return server_error(
                log_func=log.warn,
                log_msg=('[{data[network]}] board_id={board_id}'
                         ': auth-key mismatch'
                         .format(data=request_data,
                                 board_id=board_id)),
                http_msg=u'Invalid board token',
                status=401,  # Unauthorized
            )

    # these need to be better named for their transmission direction,
    # its very clear how they are consumed as they are currently named.
    db_source = DBProxy('{0}source'.format(tag), use_session=False)
    db_transactions = DBProxy('{0}trans'.format(tag), use_session=False)

    if request_data.get('action', None) == 'pull':
        # client is requesting to pull messages
        return serve_messages_for(board_id=board_id,
                                  request_data=request_data,
                                  db_source=db_source)

    elif request_data.get('action', None) == 'push':
        # client is sending a message to the network
        return receive_message_from(board_id=board_id,
                                    request_data=request_data,
                                    db_source=db_source,
                                    db_transactions=db_transactions)

    return server_error(
        log_func=log.info,
        log_msg=('[{data[network]}] Unknown action, {data[action]!r}'
                 .format(data=request_data)),
        http_msg=('action {data[action]!r} invalid.'
                  .format(data=request_data)),
        status=405,  # method not allowed
    )
