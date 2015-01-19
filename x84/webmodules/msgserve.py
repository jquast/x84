"""
x84net message network web host for x/84.

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

    :raises ValueError: ``when`` value of token is out of bounds,
                        or could not be coerced to an integer.
    """
    values = request_data.get('auth', '').split('|')
    if len(values) != 3:
        raise ValueError('Token must be 3-part pipe-delimited')

    _, _, when = values
    when = int(when)
    if time.time() > when + AUTH_EXPIREY:
        raise ValueError('Token is from the future')
    elif time.time() - when > AUTH_EXPIREY:
        raise ValueError('Token too far in the past')

    return values


class MessageApi(object):

    """ message network web API endpoint """

    # todo: validate messages much earlier (here, not below the scissor-line)

    def GET(self, network, last):
        """ GET method - pull messages """
        log = logging.getLogger(__name__)
        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            raise server_error(
                log_func=log.info,
                log_msg=('request without header Auth-X84net.'),
                status_exc=web.NoMethod)

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

    def PUT(self, network, *_):
        """ PUT method - post messages. """
        log = logging.getLogger(__name__)
        if 'HTTP_AUTH_X84NET' not in web.ctx.env:
            raise server_error(
                log_func=log.info,
                log_msg='request without header Auth-X84net.',
                status_exc=web.NoMethod)

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
        """
        Return ``response_data`` as json.

        :raises web.HTTPError: response_data failed to encode to json.
        """
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


def server_error(log_func, log_msg, status_exc):
    """
    Helper function for logging and returning web.HTTPError.

    :param callable log_func: logging function.
    :param str log_msg: log message.
    :param web.HTTPError status_exc: exception class
    :raises: status_exc instance
    :returns: does not return.
    """
    exc = status_exc()
    log_func('{0}: {1}'.format(exc, log_msg))
    raise exc


def serve_messages_for(board_id, request_data, db_source):
    """ Reply-to api client request to receive new messages. """
    # pylint: disable=R0914
    #         Too many local variables (16/15)
    from x84.bbs import DBProxy, msgbase
    from x84.bbs.msgbase import to_utctime
    log = logging.getLogger(__name__)
    # log.error(msg)
    db_tags = DBProxy(msgbase.TAGDB, use_session=False)
    db_messages = DBProxy(msgbase.MSGDB, use_session=False)

    def message_owned_by(msg_id, board_id):
        """ Whether given message is owned by specified board. """
        return (msg_id in db_source and
                db_source[msg_id] == board_id)

    def msgs_after(idx=None):
        """
        Generator of network messages following index ``idx```.

        If ``idx`` is None, all messages are returned.
        """
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
    """ Reply-to api client request to post a new message. """
    from x84.bbs.msgbase import to_localtime, Msg
    log = logging.getLogger(__name__)

    if 'message' not in request_data:
        raise server_error(
            log_func=log.info,
            log_msg="request data missing 'message' content",
            status_exc=web.BadRequest)

    pullmsg = request_data['message']

    # validate
    for key in (_key for _key in VALIDATE_MSG_KEYS if _key not in pullmsg):
        raise server_error(
            log_func=log.info,
            log_msg=("request data 'message' missing sub-field {key!r}"
                     .format(key=key)),
            status_exc=web.BadRequest)

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
    # pylint: disable=R0914
    #         Too many local variables (16/15)
    from x84.bbs import DBProxy, get_ini
    log = logging.getLogger(__name__)

    # validate primary json request keys
    for key in (_key for _key in VALIDATE_FIELDS
                if _key not in request_data):
        raise server_error(
            log_func=log.info,
            log_msg=("request data 'message' missing sub-field {key!r}"
                     .format(key=key)),
            status_exc=web.BadRequest)

    # validate this server offers such message network
    server_tags = get_ini(section='msg', key='server_tags', split=True)

    if not request_data['network'] in server_tags:
        raise server_error(
            log_func=log.warn,
            log_msg=('[{data[network]}] not in server_tags ({server_tags})'
                     .format(data=request_data, server_tags=server_tags)),
            status_exc=web.NotFound)

    tag = request_data['network']

    # validate authentication token
    try:
        board_id, token, auth_tmval = parse_auth(request_data)
    except ValueError as err:
        raise server_error(
            log_func=log.warn,
            log_msg=('[{data[network]}] Bad token: {err}'
                     .format(data=request_data, err=err)),
            status_exc=web.Unauthorized)

    else:
        log.debug('[{data[network]}] board_id={board_id} request'
                  ': {data[action]}'.format(data=request_data,
                                            board_id=board_id))

    # validate board auth-key
    keysdb = DBProxy('{0}keys'.format(tag), use_session=False)
    try:
        client_key = keysdb[board_id]
    except KeyError:
        raise server_error(
            log_func=log.warn,
            log_msg=('[{data[network]}] board_id={board_id}'
                     ': No such key for this network'
                     .format(data=request_data,
                             board_id=board_id)),
            status_exc=web.Unauthorized)
    else:
        server_key = hashlib.sha256('{0}{1}'.format(client_key, auth_tmval))
        if token != server_key.hexdigest():
            raise server_error(
                log_func=log.warn,
                log_msg=('[{data[network]}] board_id={board_id}'
                         ': auth-key mismatch'
                         .format(data=request_data,
                                 board_id=board_id)),
                status_exc=web.Unauthorized,  # Unauthorized
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

    raise server_error(
        log_func=log.info,
        log_msg=('[{data[network]}] Unknown action, {data[action]!r}'
                 .format(data=request_data)),
        status_exc=web.NoMethod)
