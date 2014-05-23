"""
script for launching dummy processes for x/84 bbs https://github.com/jquast/x84
"""

def main():
    from x84.bbs import getsession, getterminal
    from x84.bbs.userbase import User
    import logging

    logger = logging.getLogger()
    session, term = getsession(), getterminal()
    whoami = session.sid.split(':')[0]

    if whoami == 'msgserve':
        from x84 import msgserve
        session.user = User(u'x84net server')
        session.activity = u'Processing request'
        msgserve.main()
        return
    elif whoami == 'msgpoll':
        from x84 import msgpoll
        session.user = User(u'x84net client')
        session.activity = u'Polling for messages'
        msgpoll.main()
        return
    else:
        logger.error(u'Unknown bot connected; aborting')
        return
