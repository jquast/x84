"""
script for launching dummy processes for x/84 bbs https://github.com/jquast/x84
"""

def main():
    from x84.bbs import getsession, echo
    from x84.bbs.userbase import User
    import logging

    logger = logging.getLogger()
    session = getsession()

    if session.user.handle == u'msgserve':
        from x84 import webserve
        from x84.webmodules import msgserve
        session.send_event('set-timeout', 0)
        session.activity = u'Serving messages'
        while True:
            try:
                msgserve.main()
            except KeyboardInterrupt:
                webserve.QUEUES[msgserve.OUTQUEUE].put({u'response': False, u'message': u'Error'})
                break
    elif session.user.handle == u'msgpoll':
        from x84 import msgpoll
        session.activity = u'Polling for messages'
        msgpoll.main()
    else:
        logger.error(u'Unknown bot connected; aborting')
