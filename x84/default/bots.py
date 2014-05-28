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
        session.activity = u'Serving messages'
        while True:
            try:
                msgserve.main()
            except KeyboardInterrupt:
                MessageNetworkServer.oqueue.put('Error')
                break
            except Exception:
                MessageNetworkServer.oqueue.put('Error')
    elif whoami == 'msgpoll':
        from x84 import msgpoll
        session.user = User(u'x84net client')
        session.activity = u'Polling for messages'
        msgpoll.main()
    else:
        logger.error(u'Unknown bot connected; aborting')
