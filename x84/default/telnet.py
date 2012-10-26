"""
telnet client for X/84 BBS, https://github.com/jquast/x84/
"""
TIME_POLL = 0.05

#pylint: disable=W0614
#        Unused import from wildcard import
from bbs import *

def main(host, port=None):
    """
    Call script with argument host and optional argument port to connect to a
    telnet server. ^] to exit.
    """
    import telnetlib
    import sys
    session, term = getsession(), getterminal()
    session.activity = 'telneting to %s' % (host,)
    port = port if port is not None else 23
    telnet_client = telnetlib.Telnet()

    echo (term.clear)
    echo (u'\r\nTrying %s... ' % (host,))
    oflush ()
    try:
        telnet_client.open (host, port)
    except:
        type, value, tb = sys.exc_info ()
        echo (u'%s%s' % (color(*LIGHTRED), value))
        echo (u'\r\n\r\n%s%s' % (color(), 'press any key'))
        getch ()
        return

    echo (u'\r\nConnected to %s.' % (host,))
    echo (u"\r\nEscape character is '^].'")
    getch (1)

    chk = session.enable_keycodes
    session.enable_keycodes = False
    while True:
        inp = getch (timeout=TIME_POLL)
        try:
            unistring = from_cp437(telnet_client.read_very_eager())
            if 0 != len(unistring):
                echo (unistring)

            if inp == '\035': # ^]
                telnet_client.close ()
                echo (u'\r\n%sConnection closed.' % (term.clear_el +
                    term.normal))
            elif inp == '\r':
                telnet_client.write ('\r\x00') # RFC telnet return ..
            elif inp is not None:
                telnet_client.write (inp)
        except:
            exctype, value, tb = sys.exc_info ()
            echo (u''.join((term.normal, term.clear_el,)))
            echo (u''.join(('\r\n\r\n', term.bold_red, repr(value))))
            break
    echo (u''.join(('\r\n\r\n', term.clear_el, term.normal, 'press any key')))
    getch ()
    session.enable_keycodes = chk
    return
