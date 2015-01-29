#!/usr/bin/env python2.7
""" x84net message poll for x/84. """

# std imports
import logging
import hashlib
import time
import json
import os

# local
from . import cmdline

# 3rd-party
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


def pull_rest(net, last_msg_id):
    """ pull messages for a given network newer than the 'last' message idx """
    url = '%smessages/%s/%s' % (net['url_base'], net['name'], last_msg_id)

    log = logging.getLogger(__name__)

    try:
        req = requests.get(url,
                           headers={'Auth-X84net': get_token(net)},
                           verify=net['verify'])
    except requests.ConnectionError as err:
        log.warn('[{net[name]}] ConnectionError in pull_rest: {err}'
                 .format(net=net, err=err))
        return False
    except Exception as err:
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
    except Exception as err:
        log.exception('[{net[name]}] JSON error: {err}'
                      .format(net=net, err=err))
        return False


def push_rest(net, msg, parent):
    """ push message for a given network and append an origin line """
    msg_data = prepare_message(msg, net, parent)
    url = '{net[url_base]}messages/{net[name]}/'.format(net=net)
    data = {'message': json.dumps(msg_data)}

    log = logging.getLogger(__name__)

    try:
        req = requests.put(url,
                           headers={'Auth-X84net': get_token(net)},
                           data=data,
                           verify=net['verify'])
    except Exception as err:
        log.exception('[{net[name]}] exception in push_rest: {err}'
                      .format(net=net, err=err))
        return False

    if req.status_code not in (200, 201):
        log.error('{net[name]} HTTP error, code={req.status_code}'
                  .format(net=net, req=req))
        return False

    try:
        response = json.loads(req.text)
    except Exception as err:
        log.exception('[{net[name]}] JSON error: {err}'
                      .format(net=net, err=err))
    else:
        if response['response'] and 'id' in response:
            return response['id']
    return False


def get_networks():
    """ Get list configured message networks. """
    from x84.bbs import get_ini

    log = logging.getLogger(__name__)

    # pull list of network-associated tags
    network_list = get_ini(section='msg',
                           key='network_tags',
                           split=True)

    # expected configuration options,
    net_options = ('url_base token board_id'.split())

    networks = list()
    for net_name in network_list:
        net = {'name': net_name}

        section = 'msgnet_{0}'.format(net_name)
        configured = True
        for option in net_options:
            if not get_ini(section=section, key=option):
                log.error('[{net_name}] Missing configuration, '
                          'section=[{section}], option={option}.'
                          .format(net_name=net_name,
                                  section=section,
                                  option=option))
                configured = False
            net[option] = get_ini(section=section, key=option)
        if not configured:
            continue

        # make last_file an absolute path, relative to `datapath`
        net['last_file'] = os.path.join(
            os.path.expanduser(get_ini(section='system', key='datapath')),
            '{net[name]}_last'.format(net=net))

        net['verify'] = True
        ca_path = get_ini(section=section, key='ca_path')
        if ca_path:
            ca_path = os.path.expanduser(ca_path)
            if not os.path.isfile(ca_path):
                log.warn("File not found for Config section [{section}], "
                         "option {key}, value={ca_path}.  default ca_verify "
                         "will be used. ".format(section=section,
                                                 key='ca_path',
                                                 ca_path=ca_path))
            else:
                net['verify'] = ca_path

        networks.append(net)
    return networks


def get_last_msg_id(last_file):
    """ Get the "last message id" by data file ``last_file``. """
    # TODO(jquast): This should have been done internally (and far
    #               more easily!) by a DBProxy database.
    last_msg_id = -1

    log = logging.getLogger(__name__)

    try:
        # May raise IOError (File not Found)
        with open(last_file, 'r') as last_fp:
            last_msg_id = int(last_fp.read().strip())

    except IOError:
        # So, create it; but this too, may raise an
        # OSError (Permission Denied), handled by caller.
        with open(last_file, 'w') as last_fp:
            last_fp.write(str(last_msg_id))

        log.info('last_file created: {0}'.format(last_file))

    return last_msg_id


def poll_network_for_messages(net):
    """ Poll for new messages of network, ``net``. """
    from x84.bbs import Msg, DBProxy
    from x84.bbs.msgbase import to_localtime

    log = logging.getLogger(__name__)

    log.debug(u'[{net[name]}] Polling for new messages.'.format(net=net))

    try:
        last_msg_id = get_last_msg_id(net['last_file'])
    except (OSError, IOError) as err:
        log.error('[{net[name]}] skipping network: {err}'
                  .format(net=net, err=err))
        return

    msgs = pull_rest(net=net, last_msg_id=last_msg_id)

    if msgs:
        log.info('[{net[name]}] Retrieved {num} messages.'
                 .format(net=net, num=len(msgs)))
    else:
        log.debug('[{net[name]}] No messages.'.format(net=net))
        return

    transdb = DBProxy('{0}trans'.format(net['name']), use_session=False)
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
            log.warn("[{net[name]}] No recipient (msg_id={msg[id]}), "
                     "adding 'public' tag".format(net=net, msg=msg))
            store_msg.tags.add(u'public')

        if (msg['parent'] is not None and
                str(msg['parent']) not in transkeys):
            log.warn('[{net[name]}] No such parent message ({msg[parent]}, '
                     'msg_id={msg[id]}), removing reference.'
                     .format(net=net, msg=msg))
        elif msg['parent'] is not None:
            store_msg.parent = int(transdb[msg['parent']])

        if msg['id'] in transkeys:
            log.warn('[{net[name]}] dupe (msg_id={msg[id]}) discarded.'
                     .format(net=net, msg=msg))
        else:
            # do not save this message to network, we already received
            # it from the network, set send_net=False
            store_msg.save(send_net=False, ctime=to_localtime(msg['ctime']))
            with transdb:
                transdb[msg['id']] = store_msg.idx
            transkeys.append(msg['id'])
            log.info('[{net[name]}] Processed (msg_id={msg[id]}) => {new_id}'
                     .format(net=net, msg=msg, new_id=store_msg.idx))

        if 'last' not in net.keys() or int(net['last']) < int(msg['id']):
            net['last'] = msg['id']

    if 'last' in net.keys():
        with open(net['last_file'], 'w') as last_fp:
            last_fp.write(str(net['last']))

    return


def publish_network_messages(net):
    """ Push messages to network, ``net``. """
    from x84.bbs import DBProxy
    from x84.bbs.msgbase import format_origin_line, MSGDB

    log = logging.getLogger(__name__)

    log.debug(u'[{net[name]}] publishing new messages.'.format(net=net))

    queuedb = DBProxy('{0}queues'.format(net['name']), use_session=False)
    transdb = DBProxy('{0}trans'.format(net['name']), use_session=False)
    msgdb = DBProxy(MSGDB, use_session=False)

    # publish each message
    for msg_id in sorted(queuedb.keys(),
                         cmp=lambda x, y: cmp(int(x), int(y))):
        if msg_id not in msgdb:
            log.warn('[{net[name]}] No such message (msg_id={msg_id})'
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
                log.warn('[{net[name]}] Parent ID {msg.parent} '
                         'not in translation-DB (msg_id={msg_id})'
                         .format(net=net, msg=msg, msg_id=msg_id))

        trans_id = push_rest(net=net, msg=msg, parent=trans_parent)
        if trans_id is False:
            log.error('[{net[name]}] Message not posted (msg_id={msg_id})'
                      .format(net=net, msg_id=msg_id))
            continue

        if trans_id in transdb.keys():
            log.error('[{net[name]}] trans_id={trans_id} conflicts with '
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
        log.info('[{net[name]}] Published (msg_id={msg_id}) => {trans_id}'
                 .format(net=net, msg_id=msg_id, trans_id=trans_id))


def poller(poll_interval):
    """ Blocking function periodically polls configured message networks. """
    log = logging.getLogger(__name__)

    # get all networks
    networks = get_networks()

    if networks:
        while True:
            do_poll(networks)
            time.sleep(poll_interval)
    else:
        log.error(u'No networks configured for poll/publish.')


def main(background_daemon=True):
    """
    Entry point to configure and begin network message polling.

    Called by x84/engine.py, function main() as unmanaged thread.

    :param bool background_daemon: When True (default), this function returns
                and web modules are served in an unmanaged, background (daemon)
                thread.  Otherwise, function call to ``main()`` is blocking.
    :rtype: None
    """
    from threading import Thread
    from x84.bbs.ini import get_ini

    log = logging.getLogger(__name__)

    poll_interval = get_ini(section='msg',
                            key='poll_interval',
                            getter='getint'
                            ) or 1984

    if background_daemon:
        t = Thread(target=poller, args=(poll_interval,))
        t.daemon = True
        log.info('msgpoll at {0}s intervals.'.format(poll_interval))
        t.start()
    else:
        poller(poll_interval)


def do_poll(networks):
    """
    Message polling process.

    Function is called periodically by :func:`poller`.
    """
    # pull-from all networks
    map(poll_network_for_messages, networks)

    # publish-to all networks
    map(publish_network_messages, networks)

if __name__ == '__main__':
    # load only message polling module when executing this script directly.
    #
    # as we are running outside of the 'engine' context, it is necessary
    # for us to initialize the .ini configuration scheme so that the list
    # of web modules and ssl options may be gathered.
    import x84.bbs.ini
    x84.bbs.ini.init(*cmdline.parse_args())

    # do not execute message polling as a background thread.
    main(background_daemon=False)
