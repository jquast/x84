"""
input package for X/84 BBS, https://github.com/jquast/x84
"""
import bbs.session
import bbs.output

def getch(timeout=None):
    """
    Retrieve a keystroke from 'input' queue, blocking forever or, when
    specified, None when timeout has elapsed.
    """
    event, data = bbs.session.getsession().read_event(
            events=('input',), timeout=timeout)
    return data

def getpos(timeout=None):
    """
    Return current terminal position as (y,x). (Blocking). This is used in
    only rare circumstances, it is more likely you would want to use
    term.save and term.restore cursor.
    """
    bbs.session.getsession().send_event('pos', timeout)
    event, data = bbs.session.getsession().read_event(
            events=['pos-reply'], timeout=timeout)
    return data[0]

# deprecate here, down

def readline(width, value=u'', hidden=u'', paddchar=u' ', events=('input',),
        timeout=None, interactive=False, silent=False):
    import warnings
    warnings.warn('deprecated', DeprecationWarning, 2)
    (value, event, data) = readlineevent(
            width, value, hidden, paddchar, events, timeout,
            interactive, silent)
    return value

def readlineevent(width, value=u'', hidden=u'', paddchar=u' ',
        events=('input',), timeout=None, interactive=False, silent=False):
    import warnings
    warnings.warn('deprecated', DeprecationWarning, 2)
    # please stop using this ...
    term = bbs.session.getsession().terminal

    if not hidden and value:
        bbs.output.echo (value)
    elif value:
        bbs.output.echo (hidden *len(value))

    while 1:
        event, data = bbs.session.getsession().read_event(events, timeout)

        # pass-through non-input data
        if event != 'input':
            return (value, event, data)

        if data == term.KEY_EXIT:
            return (None, 'input', None) # ugh

        elif data == term.KEY_ENTER:
            return (value, 'input', term.KEY_ENTER) # ugh

        elif data == term.KEY_BACKSPACE:
            if len(value) > 0:
                value = value [:-1]
                bbs.output.echo (u'\b' + paddchar + u'\b')

        elif isinstance(data, int):
            pass # unhandled keycode ...

        elif len(value) < width:
            value += data
            if hidden:
                bbs.output.echo (hidden)
            else:
                bbs.output.echo (data)
        elif not silent:
            bbs.output.echo (u'\a')
        if interactive:
            return (value, 'input', None)
