"""
x84net message network client/server
"""

""" TCP server for x84net """

import SocketServer
import multiprocessing

""" server and its queues """
class MessageNetworkServer(SocketServer.TCPServer):
    INQUEUE = multiprocessing.Queue()
    OUTQUEUE = multiprocessing.Queue()
    allow_reuse_address = True

""" method for handling individual requests """
class MessageNetworkServerHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        import socket
        from x84.telnet import TelnetClient
        from x84.terminal import ConnectTelnet
        import json

        queue = MessageNetworkServer.INQUEUE
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        tc = TelnetClient(s, ('msgserve', 0))
        tc.env['TERM'] = 'xterm-256color'
        c = ConnectTelnet(tc)
        c._set_socket_opts()
        c._spawn_session()
        queue.put(json.loads(self.rfile.readline().strip()))
        queue = MessageNetworkServer.OUTQUEUE
        self.wfile.write(json.dumps(queue.get()) + u'\n')
        self.wfile.flush()
        s.close()

""" functions for processing the request within x84 """

""" helper method for logging and returning errors """
def server_error(logger, queue, logtext, message=None):
    if message is None:
        message = logtext
    logger.error(logtext)
    queue.put({u'response': False, u'message': message})

""" server request handling process """
def main():
    from x84.bbs import ini, msgbase, DBProxy, getsession
    from x84.bbs.aes import encryptData, decryptData
    from x84.bbs.msgbase import to_utctime, to_localtime, Msg
    from base64 import standard_b64encode, standard_b64decode
    import hashlib
    import time
    import logging

    queue = MessageNetworkServer.INQUEUE
    session = getsession()
    logger = logging.getLogger()
    data = queue.get(True, 5)
    queue = MessageNetworkServer.OUTQUEUE

    if not data:
        return server_error(logger, queue, u'No data')

    if 'network' not in data.keys():
        return server_error(logger, queue, u'Network not specified')

    if 'action' not in data.keys():
        return server_error(logger, queue, u'Action not specified')

    if 'auth' not in data.keys():
        return server_error(logger, queue, u'Auth token missing')

    auth = data['auth'].split('|')

    if len(auth) != 3:
        return server_error(logger, queue, u'Improper token')

    board_id = int(auth[0])
    token = auth[1]
    when = int(auth[2])
    now = int(time.time())
    netcfg = 'msgnet_%s' % data['network']
    logger.info(u"client %d connecting for '%s' %s" % (board_id, data['network'], data['action']))

    if not ini.CFG.has_option(netcfg, 'keys_db_name'):
        return server_error(logger, queue, u'No keys database config for this network', u'Server error')

    keysdb = DBProxy(ini.CFG.get(netcfg, 'keys_db_name'))

    if str(board_id) not in keysdb.keys():
        return server_error(logger, queue, u'No such key for this network')

    board_key = keysdb[str(board_id)]

    if when > now or now - when > 15:
        return server_error(logger, queue, u'Expired token')

    if token != hashlib.sha256('%s%d' % (board_key, when)).hexdigest():
        return server_error(logger, queue, u'Invalid token')

    if not ini.CFG.has_option(netcfg, 'source_db_name'):
        return server_error(logger, queue, u'Source DB not configured', u'Server error')

    if not ini.CFG.has_option(netcfg, 'trans_db_name'):
        return server_error(logger, queue, u'Translation DB not configured', u'Server error')

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

        try:
            response = {u'response': True, u'messages': None}
            response[u'messages'] = standard_b64encode(encryptData(board_key.decode('hex'), json.dumps(msgs)))
            queue.put(response)
        except Exception, e:
            return server_error(logger, queue, u'Encryption error: %s' % str(e), u'Server error')
    elif data['action'] == 'push':

        """ client is requesting to push messages """

        if 'message' not in data.keys():
            return server_error(logger, queue, u'No message')

        pullmsg = data['message']

        try:
            pullmsg = json.loads(decryptData(board_key.decode('hex'), standard_b64decode(pullmsg)))
        except Exception, e:
            return server_error(logger, queue, u'Decryption exception: %s' % str(e))

        for k in [u'author', u'recipient', u'subject', u'parent', u'tags', u'ctime', u'body']:
            if k not in pullmsg.keys():
                return server_error(logger, queue, u'Missing %s' % k)

        msg = Msg()
        msg.author = pullmsg['author']
        msg.recipient = pullmsg['recipient']
        msg.subject = pullmsg['subject']
        msg.parent = pullmsg['parent']
        msg.tags = set(pullmsg['tags'] + [data['network']])
        msg.body = pullmsg['body']

        try:
            msg.save(noqueue=True, ctime=to_localtime(pullmsg['ctime'].partition('.')[0]))
        except Exception, e:
            return server_error('Error saving message: %s' % str(e))

        sourcedb.acquire()
        transdb.acquire()
        sourcedb[msg.idx] = board_id
        transdb[msg.idx] = msg.idx
        sourcedb.release()
        transdb.release()
        queue.put({u'response': True, u'id': msg.idx})
