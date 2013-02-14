"""
telnet client for X/84 BBS, https://github.com/jquast/x84/
"""
KEY_POLL = 0.015



def main(host, port=None, encoding='cp437'):
    """
    Call script with argument host and optional argument port to connect to a
    telnet server. ctrl-^ to disconnect.
    """
    import telnetlib
    import struct
    import sys
    from x84.bbs import getsession, getterminal, echo, getch, from_cp437
    assert encoding in ('utf8', 'cp437')
    session, term = getsession(), getterminal()
    session.activity = 'connecting to %s' % (host,)
    port = int(port) if port is not None else 23
    telnet_client = telnetlib.Telnet()
    IS = chr(0)
    SEND = chr(1)

    def callback_cmdopt(socket, cmd, opt):
        if cmd == telnetlib.WILL:
            if opt in (telnetlib.ECHO, telnetlib.SGA):
                socket.sendall(telnetlib.IAC + telnetlib.DO + opt)
        elif cmd == telnetlib.DO:
            if opt == telnetlib.SGA:
                socket.sendall(telnetlib.IAC + telnetlib.WILL + opt)
            elif opt == telnetlib.TTYPE:
                socket.sendall(telnetlib.IAC + telnetlib.WILL + opt)
                socket.sendall(telnetlib.IAC + telnetlib.SB
                        + telnetlib.TTYPE + IS + session.env.get('TERM')
                        + chr(0) + telnetlib.IAC + telnetlib.SE)
            elif opt == telnetlib.NAWS:
                socket.sendall(telnetlib.IAC + telnetlib.WILL + opt)
                socket.sendall(telnetlib.IAC + telnetlib.SB
                        + telnetlib.NAWS
                        + struct.pack('!HH', term.width, term.height)
                        + telnetlib.IAC + telnetlib.SE)
            else:
                socket.sendall(telnetlib.IAC + telnetlib.WONT + opt[0])
        elif cmd == telnetlib.SB:
            if opt[0] == telnetlib.TTYPE and opt[1] == SEND:
                socket.sendall(telnetlib.IAC + telnetlib.SB
                        + telnetlib.TTYPE + IS + session.env.get('TERM')
                        + chr(0) + telnetlib.IAC + telnetlib.SE)
    telnet_client.set_option_negotiation_callback(callback_cmdopt)

    echo(u"\r\n\r\nEscape character is 'ctrl-^.'")
    if not session.user.get('expert', False):
        getch(3)
    echo(u'\r\nTrying %s:%s... ' % (host, port,))
    try:
        telnet_client.open(host, port)
    except:
        e_type, e_value, e_tb = sys.exc_info()
        echo(term.bold_red('\r\n%s: %s\r\n' % (e_type, e_value,)))
        echo(u'\r\n press any key ..')
        getch()
        return

    swp = session.enable_keycodes
    session.enable_keycodes = False
    inp = session.poll_event('input')
    echo(u'\r\nConnected to %s.' % (host,))
    session.activity = 'connected to %s' % (host,)

    while True:
        try:
            unistring = (from_cp437(telnet_client.read_very_eager())
                    if encoding == 'cp437' else
                    telnet_client.read_very_eager().decode('utf8'))
            if 0 != len(unistring):
                echo(unistring)
            if inp == unichr(30):  # ctrl-^
                telnet_client.close()
                echo(u'\r\n' + term.clear_el + term.normal)
                break
            elif inp in ('\r', '\n'):
                telnet_client.write('\r')
            elif inp is not None:
                telnet_client.write(inp)
        except:
            e_type, e_value, e_tb = sys.exc_info()
            echo(term.normal + u'\r\n')
            echo(term.bold_red('%s: %s\r\n' % (e_type, e_value,)))
            break
        inp = getch(timeout=KEY_POLL)
    echo(u'\r\nConnection closed.\r\n')
    echo(u''.join(('\r\n\r\n', term.clear_el, term.normal, 'press any key')))
    session.flush_event('input')
    getch()
    session.enable_keycodes = swp
    return
