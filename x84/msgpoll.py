"""
x84net message poll for x/84, https://github.com/jquast/x84

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
network_tags = x84net
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

# local imports
import logging
import hashlib
import time
import json
import os

# 3rd party imports
import requests


def get_token(network):
    """ get token for authentication """
    tm_value = int(time.time())
    token = hashlib.sha256('{0}{1}'.format(network['token'], tm_value))
    return '{0}|{1}|{2}'.format(network['board_id'],
                                token.hexdigest(),
                                tm_value)


def prepare_message(msg, network, parent):
    """ turn a Msg object into a dict for transfer """
    from x84.bbs.msgbase import format_origin_line, to_utctime

    return {
        'author': msg.author,
        'subject': msg.subject,
        'recipient': msg.recipient,
        'parent': parent,
        'tags': [tag for tag in msg.tags if tag != network['name']],
        'body': u''.join((msg.body, format_origin_line())),
        'ctime': to_utctime(msg.ctime)
    }


def pull_rest(net, last_msg_id, log=None):
    """ pull messages for a given network newer than the 'last' message idx """
    log = log or logging.getLogger(__name__)
    url = '%smessages/%s/%s' % (net['url_base'], net['name'], last_msg_id)

    try:
        req = requests.get(url,
                           headers={'Auth-X84net': get_token(net)},
                           verify=net['ca_path'])
    except Exception, err:
        log.exception('[{net[name]}] exception in pull_rest: {err}'
                      .format(net=net, err=err))
        return False

    if req.status_code != 200:
        log.error('[{net[name]}] HTTP error, code={req.status_code}'
                  .format(net=net, req=req))
        return False

    try:
        response = json.loads(req.text)
        return response['messages'] if response['response'] else []
    except Exception, err:
        log.exception('[{net[name]}] JSON error: {err}'
                      .format(net=net, err=err))
        return False


def push_rest(net, msg, parent, log=None):
    """ push message for a given network and append an origin line """
    log = log or logging.getLogger(__name__)

    msg_data = prepare_message(msg, net, parent)
    url = '{net[url_base]}messages/{net[name]}/'.format(net=net)
    data = {'message': json.dumps(msg_data)}

    try:
        req = requests.put(url,
                           headers={'Auth-X84net': get_token(net)},
                           data=data,
                           verify=net['ca_path'])
    except Exception, err:
        log.exception('[{net[name]}] exception in push_rest: {err}'
                      .format(net=net, err=err))
        return False

    if req.status_code != 200:
        log.error('{net[name]} HTTP error, code={req.status_code}'
                  .format(net=net, req=req))
        return False

    try:
        response = json.loads(req.text)
    except Exception, err:
        log.exception('[{net[name]}] JSON error: {err}'
                      .format(net=net, err=err))
    else:
        if response['response'] and 'id' in response:
            return response['id']
    return False


def get_networks(cfg, log=None):
    " Get configured message networks. "

    log = log or logging.getLogger(__name__)

    # pull list of network-associated tags
    network_list = []
    if cfg.has_option('msg', 'network_tags'):
        net_names = cfg.get('msg', 'network_tags').split(',')
        network_list = map(str.strip, net_names)

    # expected configuration options,
    net_options = ('url_base token board_id trans_db_name '
                   'queue_db_name last_file'.split())

    networks = list()
    for net_name in network_list:
        section = 'msgnet_{0}'.format(net_name)
        net_type = cfg.get(section, 'type')
        assert net_type == 'rest', ('Only "rest" is supported', net_type)
        net = {'name': net_name, 'type': net_type}
        if not cfg.has_section(section):
            log.error('[{net_name}] No such config section: {section}'
                      .format(net_name=net_name, section=section))
            continue

        for option in net_options:
            if not cfg.has_option(section, option):
                log.error('[{net_name}] No such config option: {option}'
                          .format(net_name=net_name, option=option))
                continue
            net[option] = cfg.get(section, option)

        # make last_file absolute path, relative to datapath
        net['last_file'] = os.path.join(
            os.path.expanduser(cfg.get('system', 'datapath')),
            net['last_file'])

        if not cfg.has_option(section, 'ca_path'):
            ca_path = True
        else:
            ca_path = os.path.expanduser(cfg.get(section, 'ca_path'))
            if not os.path.isfile(ca_path):
                log.warn("CFG option section {section}, File not found for "
                         "{key} = {value}, default ca verify will be used. "
                         .format(section=section,
                                 key='ca_path',
                                 value=ca_path))
        net['ca_path'] = ca_path

        networks.append(net)
    return networks


def poll_network_for_messages(net, log=None):
    " pull for new messages of network, storing locally. "
    from x84.bbs import Msg, DBProxy
    from x84.bbs.msgbase import to_localtime
    log = log or logging.getLogger(__name__)

    last_msg_id, msgs = -1, []
    try:
        with open(net['last_file'], 'r') as last_fp:
            last_msg_id = int(last_fp.read().strip())
    except IOError as err:
        try:
            with open(net['last_file'], 'w') as last_fp:
                last_fp.write(str(last_msg_id))

            log.info('[{net[name]}] last_file created'.format(net=net))

        except OSError as err:
            log.error('[{net[name]}] skipping network: {err}'
                      .format(net=net, err=err))
            return

    msgs = pull_rest(net=net, last_msg_id=last_msg_id)

    if msgs is not False:
        log.info('{net[name]} Retrieved {num} messages'
                 .format(net=net, num=len(msgs)))
    else:
        log.debug('{net[name]} no messages.'.format(net=net))
        return

    transdb = DBProxy(net['trans_db_name'], use_session=False)
    transkeys = transdb.keys()
    msgs = sorted(msgs, cmp=lambda x, y: cmp(int(x['id']), int(y['id'])))

    # store messages locally, saving their translated IDs to the transdb
    for msg in msgs:
        store_msg = Msg()
        store_msg.recipient = msg['recipient']
        store_msg.author = msg['author']
        store_msg.subject = msg['subject']
        store_msg.body = msg['body']
        store_msg.tags = set(msg['tags'])
        store_msg.tags.add(u''.join((net['name'])))

        if msg['recipient'] is None and u'public' not in msg['tags']:
            log.warn("{net[name]} No recipient (msg_id={msg[id]}), "
                     "adding 'public' tag".format(net=net, msg=msg))
            store_msg.tags.add(u'public')

        if (msg['parent'] is not None and
                str(msg['parent']) not in transkeys):
            log.warn('{net[name]} No such parent message ({msg[parent]}, '
                     'msg_id={msg[id]}), removing reference.'
                     .format(net=net, msg=msg))
        elif msg['parent'] is not None:
            store_msg.parent = int(transdb[msg['parent']])

        if msg['id'] in transkeys:
            log.warn('{net[name]} dupe (msg_id={msg[id]}) discarded.'
                     .format(net=net, msg=msg))
        else:
            # do not save this message to network, we already received
            # it from the network, set send_net=False
            store_msg.save(send_net=False, ctime=to_localtime(msg['ctime']))
            with transdb:
                transdb[msg['id']] = store_msg.idx
            transkeys.append(msg['id'])
            log.info('{net[name]} Processed (msg_id={msg[id]}) => {new_id}'
                     .format(net=net, msg=msg, new_id=store_msg.idx))

        if 'last' not in net.keys() or int(net['last']) < int(msg['id']):
            net['last'] = msg['id']

    if 'last' in net.keys():
        with open(net['last_file'], 'w') as last_fp:
            last_fp.write(str(net['last']))

    return


def publish_network_messages(net, log=None):
    " Push messages to network. "
    from x84.bbs import DBProxy
    from x84.bbs.msgbase import format_origin_line, MSGDB

    log = log or logging.getLogger(__name__)
    queuedb = DBProxy(net['queue_db_name'], use_session=False)
    transdb = DBProxy(net['trans_db_name'], use_session=False)
    msgdb = DBProxy(MSGDB, use_session=False)

    # publish each message
    for msg_id in sorted(queuedb.keys(),
                         cmp=lambda x, y: cmp(int(x), int(y))):
        if msg_id not in msgdb:
            log.warn('{net[name]} No such message (msg_id={msg_id})'
                     .format(net=net, msg_id=msg_id))
            del queuedb[msg_id]
            continue

        msg = msgdb[msg_id]

        trans_parent = None
        if msg.parent is not None:
            matches = [key for key, data in transdb.items()
                       if int(data) == msg.parent]

            if len(matches) > 0:
                trans_parent = matches[0]
            else:
                log.warn('{net[name]} Parent ID {msg.parent} '
                         'not in translation-DB (msg_id={msg_id})'
                         .format(net=net, msg=msg, msg_id=msg_id))

        trans_id = push_rest(net=net, msg=msg, parent=trans_parent)
        if trans_id is False:
            log.error('{net[name]} Message not posted (msg_id={msg_id})'
                      .format(net=net['name'], msg_id=msg_id))
            continue

        if trans_id in transdb.keys():
            log.error('{net[name]} trans_id={trans_id} conflicts with '
                      '(msg_id={msg_id})'
                      .format(net=net, trans_id=trans_id, msg_id=msg_id))
            with queuedb:
                del queuedb[msg_id]
            continue

        # transform, and possibly duplicate(?) message ..
        with transdb, msgdb, queuedb:
            transdb[trans_id] = msg_id
            msg.body = u''.join((msg.body, format_origin_line()))
            msgdb[msg_id] = msg
            del queuedb[msg_id]
        log.info('{net[name]} Published (msg_id={msg_id}) => {trans_id}'
                 .format(net=net, msg_id=msg_id, trans_id=trans_id))

def start_polling():
    """ launch method for polling process """

    def polling_thread(poll_interval):
        import time

        last_poll = 0

        while True:
            now = time.time()
            if now - last_poll >= poll_interval:
                poll()
                last_poll = now
            time.sleep(1)

    from threading import Thread
    from x84.bbs.ini import CFG
    import logging

    log = logging.getLogger('x84.engine')
    poll_interval = CFG.getint('msg', 'poll_interval')
    t = Thread(target=polling_thread, args=(poll_interval,))
    t.daemon = True
    t.start()
    log.info('msgpoll will poll at {0}s intervals.'
              .format(poll_interval))

def poll():
    """ message polling process """
    import x84.bbs.ini

    log = logging.getLogger(__name__)

    # get all networks
    networks = get_networks(cfg=x84.bbs.ini.CFG)
    log.debug(u'Begin poll/publish process for networks: {net_names}.'
              .format(net_names=', '.join(net['name'] for net in networks)))

    # pull/push to all networks
    for net in networks:
        poll_network_for_messages(net)
        publish_network_messages(net)
    num = len(networks)
    log.debug('Message poll/publish complete for {n} network{s}.'
              .format(n=num, s='s' if num != 1 else ''))
