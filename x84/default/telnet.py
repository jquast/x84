"""
telnet client for X/84 BBS, https://github.com/jquast/x84/
"""
TIME_POLL = 0.05

import telnetlib
import sys
# pylint: disable=W0614
#        Unused import from wildcard import
from x84.bbs import *


def main(host, port=None):
    """
    Call script with argument host and optional argument port to connect to a
    telnet server. ctrl-^ to disconnect.
    """
    session, term = getsession(), getterminal()
    session.activity = 'connecting to %s' % (host,)
    port = int(port) if port is not None else 23
    telnet_client = telnetlib.Telnet()

    echo(term.clear)
    echo(u'\r\nTrying %s:%s... ' % (host, port,))
    try:
        telnet_client.open(host, port)
    except Exception, err:
        e_type, e_value, e_tb = sys.exc_info()
        echo(term.bold_red('%s: %s\r\n' % (e_type, e_value,)))
        echo(u'\r\n\r\n press any key ..')
        getch()
        return

    echo(u'\r\nConnected to %s.' % (host,))
    echo(u"\r\nEscape character is 'ctrl-^.'")
    session.activity = 'connected to %s' % (host,)
    getch(3)

    swp = session.enable_keycodes
    session.enable_keycodes = False
    while True:
        inp = getch(timeout=TIME_POLL)
        try:
            unistring = from_cp437(telnet_client.read_very_eager())
            if 0 != len(unistring):
                echo(unistring)

            if inp == unichr(30):  # ^^
                telnet_client.close()
                echo(u'\r\n' + term.clear_el + term.normal)
                break
            elif inp == '\r':
                telnet_client.write('\r\x00')  # RFC telnet return ..
            elif inp is not None:
                telnet_client.write(inp)
        except Exception, err:
            e_type, e_value, e_tb = sys.exc_info()
            echo(term.normal)
            echo(term.bold_red('%s: %s\r\n' % (e_type, e_value,)))
            break
    echo(u'\r\nConnection closed.\r\n')
    echo(u''.join(('\r\n\r\n', term.clear_el, term.normal, 'press any key')))
    session.flush_event('input')
    getch()
    session.enable_keycodes = swp
    return
