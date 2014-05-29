"""
script for launching dummy processes for x/84 bbs https://github.com/jquast/x84
"""

def main():
    from x84.engine import BlackHoleServer
    from x84.bbs import getsession, echo
    from x84.bbs.userbase import User
    import logging

    logger = logging.getLogger()
    session = getsession()
    whoami = session.sid.split(':')[0]

    if whoami == 'msgserve':
        from x84 import msgserve
        from x84.msgserve import MessageNetworkServer
        session.user = User(u'x84net server')
        session.send_event('set-timeout', 0)
        session.activity = u'Serving messages'
        while True:
            try:
                msgserve.main()
            except KeyboardInterrupt:
                print 'KeyboardInterrupt'
                MessageNetworkServer.oqueue.put({u'response': False, u'message': u'Error'})
                break
            except Exception, e:
                logger.exception(u'%r' % e)
                MessageNetworkServer.oqueue.put({u'response': False, u'message': u'Error'})
    elif whoami == 'msgpoll':
        from x84 import msgpoll
        session.user = User(u'x84net client')
        session.activity = u'Polling for messages'
        msgpoll.main()
    else:
        logger.error(u'Unknown bot connected; aborting')
