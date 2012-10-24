"""
input package for x/84, https://github.com/jquast/x84
"""
import bbs.session

def getch(timeout=None):
    """
    Retrieve a keystroke from 'input' queue, blocking forever or, when
    specified, None when timeout has elapsed.
    """
    return bbs.session.getsession().read_event('input', timeout)

#def getpos(timeout=None):
#    """
#    Return current terminal position as (y,x). (Blocking). This is used in
#    only rare circumstances, it is more likely you would want to use
#    term.save and term.restore to temporarily move the cursor.
#    """
#    bbs.session.getsession().send_event('pos', timeout)
#    return bbs.session.getsession().read_event('pos-reply', timeout)
