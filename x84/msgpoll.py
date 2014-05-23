"""
x84net message network polling mechanism
"""

""" get token for authentication """
def get_token(network):
    import time
    import hashlib

    t = int(time.time())
    return '%s|%s|%s' % (network['board_id'], hashlib.sha256('%s%s' % (network['token'], t)).hexdigest(), t)

""" turn a Msg object into a dict for transfer """
def prepare_message(msg, network):
    from x84.bbs.msgbase import format_origin_line, to_utctime

    return {
        'author': msg.author
        , 'subject': msg.subject
        , 'recipient': msg.recipient
        , 'parent': msg.parent
        , 'tags': [tag for tag in msg.tags if tag != network['name']]
        , 'body': u''.join((msg.body, format_origin_line()))
        , 'ctime': to_utctime(msg.ctime)
    }

"""
TCP network client methods
"""

def pull_tcp(network, last):
    import socket
    import json
    import logging
    from x84.bbs.aes import decryptData
    from base64 import standard_b64decode
    from x84.bbs.msgbase import format_origin_line, to_localtime, to_utctime

    logger = logging.getLogger()
    data = {'auth': get_token(network), 'network': network['name'], 'action': 'pull'}

    if last != None:
        data['last'] = last

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((network['addr'], int(network['port'])))
        sfile = s.makefile('w+')
        sfile.write(json.dumps(data) + u'\n')
        sfile.flush()
        result = sfile.readline().strip()
        result = json.loads(result)
        s.close()

        if result['response'] == True:
            try:
                if 'messages' not in result.keys() or result['messages'] is None or len(result['messages']) == 0:
                    logger.info(u'[%s] Empty result' % network['name'])
                    return False

                dec = json.loads(decryptData(network['token'].decode('hex'), standard_b64decode(result['messages'])))
                return dec
            except Exception, e:
                logger.exception(u'[%s] Decryption exception: %s' % (network['name'], str(e)))
                return False
        else:
            if 'message' in result.keys():
                logger.error(u'[%s] Server error: %s' % (network['name'], result['message']))
            else:
                logger.error(u'[%s] Server error' % network['name'])

            return False
    except Exception, e:
        logger.exception(u'[%s] Exception: %s' % (network['name'], str(e)))
        return False

def push_tcp(network, msg, parent, origin_line):
    import socket
    import json
    import logging
    from x84.bbs.aes import encryptData
    from base64 import standard_b64encode

    logger = logging.getLogger()
    pushmsg = prepare_message(msg, network)
    pushmsg['parent'] = parent

    try:
        pushmsg = standard_b64encode(encryptData(network['token'].decode('hex'), json.dumps(pushmsg)))
    except Exception, e:
        logger.exception(u'[%s] Encryption exception: %s' % (network['name'], str(e)))
        return False

    data = {'auth': get_token(network), 'network': network['name'], 'action': 'push', 'message': pushmsg}

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((network['addr'], int(network['port'])))
        sfile = s.makefile('w+')
        sfile.write(json.dumps(data) + u'\n')
        sfile.flush()
        result = json.loads(sfile.readline().strip())

        if result[u'response'] == True:
            return result[u'id']
        else:
            logger.error(u'[%s] Server error: %s' % (network['name'], result['message']))
            return False
    except Exception, e:
        logger.exception(u'[%s] Exception: %s' % (network['name'], str(e)))
        return False

"""
REST network client methods
"""

def pull_rest(network, last):
    import requests
    import json
    import logging

    logger = logging.getLogger()
    url = '%smessage/%s' % (network['url_base'], last)
    r = None

    try:
        r = requests.get(url, headers={'Auth-X84net': get_token(network)})
    except Exception, err:
        logger.exception(u'[%s] Request error: %s' % (network['name'], str(err)))
        return False

    # oh noes!
    if r.status_code != 200:
        logger.error(u'[%s] HTTP error: %s' % (network['name'], r.status_code))
        return False

    try:
        response = json.loads(r.text)
        return response['response']
    except Exception, err:
        logger.exception(u'[%s] JSON error: %s' % (network['name'], str(err)))
        return False

def push_rest(network, msg, parent, origin_line):
    import requests
    import json
    import logging

    msg_data = prepare_message(msg, network)
    logger = logging.getLogger()
    url = '%smessage' % network['url_base']
    data = {'message': json.dumps(msg_data)}
    r = None

    try:
        r = requests.post(url, headers={'Auth-X84net': get_token(network)}, data=data)
    except Exception, err:
        logger.exception(u'[%s] Request error: %s' % (network['name'], str(err)))
        return False

    # oh noes!
    if r.status_code != 200:
        logger.error(u'[%s] HTTP error: %s' % (network['name'], r.status_code))
        return False

    try:
        response = json.loads(r.text)
        return response['response']
    except Exception, err:
        logger.exception(u'[%s] JSON error: %s' % (network['name'], str(err)))
        return False

""" message polling process """
def main():
    import logging
    import x84.bbs.ini
    from x84.bbs import Msg, msgbase, DBProxy
    from x84.bbs.msgbase import format_origin_line, to_localtime, to_utctime
    import os
    import time

    # load config
    cfg_bbs = x84.bbs.ini.CFG
    logger = logging.getLogger()
    logger.info(u'Beginning poll/publish process')
    # origin line
    origin_line = format_origin_line()
    # pull list of network-associated tags
    network_list = []

    if cfg_bbs.has_option('msg', 'network_tags'):
        network_list = [net.strip() for net in cfg_bbs.get('msg', 'network_tags').split(',')]

    networks = list()

    # build array of networks as dict items
    for net in network_list:
        netcfg = 'msgnet_%s' % net
        nettype = cfg_bbs.get(netcfg, 'type')
        network = {'name': net, 'type': nettype}

        if not cfg_bbs.has_section(netcfg):
            logger.error(u'[%s] No such configuration section: %s' % (net, netcfg))
            continue

        if nettype == 'rest':
            # rest networks
            for i in ['url_base', 'token', 'board_id', 'trans_db_name', 'queue_db_name', 'last_file']:
                if not cfg_bbs.has_option(netcfg, i):
                    logger.error(u'[%s] No such configuration option: %s' % (net, i))
                    continue

                network[i] = cfg_bbs.get(netcfg, i)
        elif nettype == 'tcp':
            # tcp networks
            for i in ['addr', 'port', 'token', 'board_id', 'trans_db_name', 'queue_db_name', 'last_file']:
                if not cfg_bbs.has_option(netcfg, i):
                    logger.error(u'[%s] No such configuration option: %s' % (net, i))
                    continue

                network[i] = cfg_bbs.get(netcfg, i)

        networks.append(network)

    datapath = os.path.expanduser(cfg_bbs.get('system', 'datapath'))
    server_tags = []

    if cfg_bbs.has_option('msgserver', 'server_tags'):
        server_tags = [tag.strip() for tag in cfg_bbs.get('msgserver', 'server_tags').split(',')]

    # handle supported networks
    for i in [net for net in networks if net['type'] in ['rest', 'tcp']]:
        # don't poll tcp-based networks we host ourselves
        if net['type'] == 'tcp' and net['name'] in server_tags:
            continue

        """ pull messages """

        last = -1
        msgs = []

        # load last parsed message id
        try:
            with open(os.path.join(datapath, net['last_file']), 'r') as f:
                last = int(f.read())
        except:
            logger.warn(u'[%s] last_file empty, corrupt, unreadable, or does not exist; using default value' % net['name'])

            try:
                with open(os.path.join(datapath, net['last_file']), 'w') as f:
                    f.write(str(last))

                logger.info(u'[%s] last_file created' % net['name'])
            except:
                logger.error(u'[%s] Could not create last_file; skipping network' % net['name'])
                continue

        logger.info(u'[%s] Begin polling' % net['name'])

        if net['type'] == 'rest':
            msgs = pull_rest(net, last)
        elif net['type'] == 'tcp':
            msgs = pull_tcp(net, last)
        # <-- redis, etc. would go here

        if msgs != False:
            logger.info(u'[%s] Retrieved %d messages' % (net['name'], len(msgs)))
        else:
            logger.error(u'[%s] Retrieval error' % net['name'])
            continue

        transdb = DBProxy(net['trans_db_name'])
        transkeys = transdb.keys()
        msgs = sorted(msgs, cmp=lambda x, y: cmp(int(x['id']), int(y['id'])))

        # "post" messages, saving their translated IDs to the transdb
        for m in msgs:
            newm = Msg()
            newm.recipient = m['recipient']
            newm.author = m['author']
            newm.subject = m['subject']
            newm.body = m['body']
            # newm.ctime = to_localtime(m['ctime'])
            newm.tags = set(m['tags'])
            newm.tags.add(u''.join((net['name'])))

            if m['recipient'] is None and u'public' not in m['tags']:
                logger.warn(u"[%s] No recipient (msgid %s), adding 'public' tag" % (net['name'], m['id']))
                newm.tags.add(u'public')

            if m['parent'] != None and str(m['parent']) not in transkeys:
                logger.warn(u'[%s] No such parent message (%s, msgid %s), stripping' % (net['name'], m['parent'], m['id']))
            elif m['parent'] != None:
                newm.parent = int(transdb[m['parent']])

            if m['id'] in transkeys:
                logger.warn(u'[%s] Duplicate message (msgid %s, %s), skipping' % (net['name'], m['id'], transdb[m['id']]))
            else:
                newm.save(noqueue=True, ctime=to_localtime(m['ctime']))
                transdb.acquire()
                transdb[m['id']] = newm.idx
                transdb.release()
                transkeys.append(m['id'])
                logger.info(u'[%s] Processed message (msgid %s) => %d' % (net['name'], m['id'], newm.idx))

            if 'last' not in net.keys() or int(net['last']) < int(m['id']):
                net['last'] = m['id']

        if 'last' in net.keys():
            with open(os.path.join(datapath, net['last_file']), 'w') as f:
                f.write(str(net['last']))

        """ push messages """

        queuedb = None
        queuedb = DBProxy(net['queue_db_name'])
        logger.info(u'[%s] Begin publishing' % net['name'])
        msgdb = DBProxy(msgbase.MSGDB)
        msgs = msgdb.keys()

        # publish each message
        for m in sorted(queuedb.keys(), cmp=lambda x, y: cmp(int(x), int(y))):
            if m not in msgs:
                logger.warn(u'[%s] No such message (msgid %s), skipping' % (net['name'], m))
                del queuedb[m]
                continue

            msg = msgdb[m]
            trans_parent = None

            if msg.parent != None:
                has_key = [key for key, data in transdb.iteritems() if data == msg.parent]

                if len(has_key) > 0:
                    trans_parent = has_key[0]
                else:
                    logger.warn(u'[%s] Parent ID %s not in translation DB (msgid %s)' % (net['name'], msg.parent, m))

            transid = None

            if net['type'] == 'rest':
                transid = push_rest(net, msg, trans_parent, origin_line)
            elif net['type'] == 'tcp':
                transid = push_tcp(net, msg, trans_parent, origin_line)

            if transid is False:
                logger.error(u'[%s] Message not posted (msgid %s)' % (net['name'], m))
                continue

            if transid in transdb.keys():
                logger.error(u'[%s] Translated ID %s already in database (msgid %s)' % (net['name'], transid, m))
                queuedb.acquire()
                del queuedb[m]
                queuedb.release()
                continue

            transdb.acquire()
            msgdb.acquire()
            queuedb.acquire()
            transdb[transid] = m
            msg.body = u''.join((msg.body, origin_line))
            msgdb[m] = msg
            del queuedb[m]
            transdb.release()
            msgdb.release()
            queuedb.release()
            logger.info(u'[%s] Published message (msgid %s) => %s' % (net['name'], m, transid))

    logger.info(u'Message poll/publish complete')
