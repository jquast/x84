"""
telnet client for X/84 BBS, https://github.com/jquast/x84/
"""
KEY_POLL = 0.015
IS = chr(0)
SEND = chr(1)


def main(host, port=None, encoding='cp437'):
    """
    Call script with argument host and optional argument port to connect to a
    telnet server. ctrl-^ to disconnect.
    """
    # pylint: disable=R0914,R0912,R0915
    #         Too many local variables
    #         Too many branches
    #         Too many statements
    import telnetlib
    import struct
    from x84.bbs import getsession, getterminal, echo, getch, from_cp437
    import logging
    log = logging.getLogger()

    assert encoding in ('utf8', 'cp437')
    session, term = getsession(), getterminal()
    session.activity = 'connecting to %s' % (host,)
    port = int(port) if port is not None else 23
    telnet_client = telnetlib.Telnet()

    def callback_cmdopt(socket, cmd, opt):
        """ Callback for telnetlib.Telnet.set_option_negotiation_callback. """
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
    # pylint: disable=W0703
    #         Catching too general exception Exception
    try:
        telnet_client.open(host, port)
    except Exception as err:
        echo(term.bold_red('\r\n%s\r\n' % (err,)))
        echo(u'\r\n press any key ..')
        getch()
        return

    echo(u'\r\n... ')
    inp = session.read_event('input', timeout=0)
    echo(u'\r\nConnected to %s.' % (host,))
    session.activity = 'connected to %s' % (host,)
    carriage_returned = False
    with term.fullscreen():
        while True:
            if encoding == 'cp437':
                try:
                    unistring = from_cp437(
                            telnet_client.read_very_eager().decode('iso8859-1'))
                except EOFError:
                    break
            else:
                unistring = telnet_client.read_very_eager().decode('utf8')
            if 0 != len(unistring):
                echo(unistring)
            if inp is not None:
                if inp == chr(30):  # ctrl-^
                    telnet_client.close()
                    echo(u'\r\n' + term.clear_el + term.normal)
                    break
                elif not carriage_returned and inp in (b'\x0d', b'\x0a'):
                    telnet_client.write(b'\x0d')
                    log.debug('send {!r}'.format(b'\x0d'))
                    carriage_returned = True
                elif carriage_returned and inp in (b'\x0a', b'\x00'):
                    carriage_returned = False
                elif inp is not None:
                    telnet_client.write(inp)
                    log.debug('send {!r}'.format(inp))
                    carriage_returned = False
            inp = session.read_event('input', timeout=KEY_POLL)
    echo(u'\r\nConnection closed.\r\n')
    echo(u''.join(('\r\n\r\n', term.clear_el, term.normal, 'press any key')))
    echo(u'\x1b[r') # unset 'set scrolling region', sometimes set by BBS's
    session.flush_event('input')
    getch()
    return
