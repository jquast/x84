"""
x84net message network polling mechanism for x/84, https://github.com/jquast/x84

To configure message polling, add a tag for the network to the 'server_tags'
attribute in the [msg] section of your default.ini.
Next, create a section using the name of that tag, prefixed with 'msgnet_'.
(Example: if the tag is 'x84net', create a 'msgnet_x84net' section.)

The following attributes are required:
 - type: Must be 'rest', as REST APIs are the only supported type (for now).
 - url_base: The base URL for the message network's REST API.
 - board_id: Your board's ID in the network.
 - token: Your board's secure token, assigned to you by the network admin.
 - trans_db_name: The alphanumeric name of the translation database.
 - queue_db_name: The alphanumeric name of the queue database.
 - last_file: The filename of the file that stores the last-retrieved message
   index number (relative to your data directory)

The following attribute is optional:
 - ca_path: The path to a CA bundle if the server's CA is not already
   included in your operating system.

If you wish to tag your messages with a custom origin line when they are
delivered to the network hub, add an 'origin_line' attribute to the [msg]
section of your default.ini.

Example default.ini configuration:

[msg]
server_tags = x84net
origin_line = Sent from The Best BBS In The World, baby!

[msgnet_x84net]
type = rest
url_base = https://some.server:8443/api/messages/
board_id = 1
token = somereallylongtoken
trans_db_name = x84nettrans
queue_db_name = x84netqueue
last_file = x84net_last
"""

def get_token(network):
    """ get token for authentication """
    import time
    import hashlib

    t = int(time.time())
    return '%s|%s|%s' % (network['board_id'], hashlib.sha256('%s%s' % (network['token'], t)).hexdigest(), t)

def prepare_message(msg, network, parent):
    """ turn a Msg object into a dict for transfer """
    from x84.bbs.msgbase import format_origin_line, to_utctime

    return {
        'author': msg.author
        , 'subject': msg.subject
        , 'recipient': msg.recipient
        , 'parent': parent
        , 'tags': [tag for tag in msg.tags if tag != network['name']]
        , 'body': u''.join((msg.body, format_origin_line()))
        , 'ctime': to_utctime(msg.ctime)
    }

"""
REST network client methods
"""

def pull_rest(network, last, ca_path=True):
    """ pull messages for a given network newer than the 'last' message idx """
    import requests
    import json
    import logging

    logger = logging.getLogger()
    url = '%smessages/%s/%s' % (network['url_base'], network['name'], last)
    r = None

    try:
        r = requests.get(url, headers={'Auth-X84net': get_token(network)}, verify=ca_path)
    except Exception, e:
        logger.exception(u'[%s] Request error: %s' % (network['name'], str(e)))
        return False

    # oh noes!
    if r.status_code != 200:
        logger.error(u'[%s] HTTP error: %s' % (network['name'], r.status_code))
        return False

    try:
        response = json.loads(r.text)
        return response['messages']
    except Exception, e:
        logger.exception(u'[%s] JSON error: %s' % (network['name'], str(e)))
        return False

def push_rest(network, msg, parent, origin_line, ca_path=True):
    """ push message for a given network and append an origin line """
    import requests
    import json
    import logging

    msg_data = prepare_message(msg, network, parent)
    logger = logging.getLogger()
    url = '%smessages/%s/' % (network['url_base'], network['name'])
    data = {'message': json.dumps(msg_data)}
    r = None

    try:
        r = requests.put(url, headers={'Auth-X84net': get_token(network)}, data=data, verify=ca_path)
    except Exception, err:
        logger.exception(u'[%s] Request error: %s' % (network['name'], str(err)))
        return False

    # oh noes!
    if r.status_code != 200:
        logger.error(u'[%s] HTTP error: %s' % (network['name'], r.status_code))
        return False

    try:
        response = json.loads(r.text)
        return response['id']
    except Exception, err:
        logger.exception(u'[%s] JSON error: %s' % (network['name'], str(err)))
        return False

def main():
    """ message polling process """
    import logging
    import x84.bbs.ini
    from x84.bbs import Msg, msgbase, DBProxy
    from x84.bbs.msgbase import format_origin_line, to_localtime, to_utctime
    import os
    import time
    import ssl

    # load config
    cfg_bbs = x84.bbs.ini.CFG
    logger = logging.getLogger()
    logger.debug(u'Beginning poll/publish process')
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

    # can manually specify path to ca-certs bundle if necessary
    ca_path = True

    if cfg_bbs.has_option(netcfg, 'ca_path'):
        ca_path = os.path.expanduser(cfg_bbs.get(netcfg, 'ca_path'))

    # handle supported networks
    for i in [net for net in networks if net['type'] in ['rest']]:

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

        logger.debug(u'[%s] Begin polling' % net['name'])

        if net['type'] == 'rest':
            msgs = pull_rest(net, last, ca_path)
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
        logger.debug(u'[%s] Begin publishing' % net['name'])
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
                transid = push_rest(net, msg, trans_parent, origin_line, ca_path)
            # <-- redis, etc. would go here

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

    logger.debug(u'Message poll/publish complete')

def do_poll():
    """ fire up a thread to poll for messages """
    def read_forever(client):
        client.read_all()

    import telnetlib
    from threading import Thread
    from x84.bbs import session
    from x84.bbs.ini import CFG
    session.BOTLOCK.acquire()
    client = telnetlib.Telnet()
    client.open(CFG.get('telnet', 'addr'), CFG.getint('telnet', 'port'))
    session.BOTQUEUE.put('msgpoll')
    t = Thread(target=read_forever, args=[client])
    t.daemon = True
    t.start()
    session.BOTLOCK.release()
