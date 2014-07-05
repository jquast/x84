"""
script for launching dummy processes for x/84 bbs https://github.com/jquast/x84
"""


def main():
    from x84.bbs import getsession
    import logging

    log = logging.getLogger(__name__)
    session = getsession()

    if session.user.handle == u'msgserve':
        # todo: we should be able to gosub directly to a small
        # script that does the actual imports of msgserve and
        # perform the while loop
        from x84.webserve import queues
        from x84.webmodules import msgserve
        session.send_event('set-timeout', 0)
        session.activity = u'Serving messages'
        while True:
            try:
                msgserve.main()
            except KeyboardInterrupt:
                queues[msgserve.OUTQUEUE].put(msgserve.RESP_FAIL)
                break
    elif session.user.handle == u'msgpoll':
        from x84 import msgpoll
        session.activity = u'Polling for messages'
        msgpoll.main()
    else:
        log.error(u"Unknown bot connected, '{0}'; aborting"
                  .format(session.user.handle))
