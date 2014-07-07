"""
telnet extras for x/x84 bbs, https://github.com/jquast/x84
"""
import functools
import threading


def callback_cmdopt(socket, cmd, opt, env_term=None, width=None, height=None):
    """ Callback for telnetlib.Telnet.set_option_negotiation_callback. """
    import telnetlib
    import struct
    IS = chr(0)  # Sub-process negotiation IS command
    if env_term is None:
        env_term = 'vt220'
    width = width or 80
    height = height or 24
    if cmd == telnetlib.WILL:
        if opt in (telnetlib.ECHO, telnetlib.SGA):
            socket.sendall(telnetlib.IAC + telnetlib.DO + opt)
    elif cmd == telnetlib.DO:
        if opt == telnetlib.SGA:
            socket.sendall(telnetlib.IAC + telnetlib.WILL + opt)
        elif opt == telnetlib.TTYPE:
            socket.sendall(telnetlib.IAC + telnetlib.WILL + opt)
            socket.sendall(telnetlib.IAC + telnetlib.SB
                           + telnetlib.TTYPE + IS + env_term
                           + chr(0) + telnetlib.IAC + telnetlib.SE)
        elif opt == telnetlib.NAWS:
            socket.sendall(telnetlib.IAC + telnetlib.WILL + opt)
            socket.sendall(telnetlib.IAC + telnetlib.SB
                           + telnetlib.NAWS
                           + struct.pack('!HH', width, height)
                           + telnetlib.IAC + telnetlib.SE)
        else:
            socket.sendall(telnetlib.IAC + telnetlib.WONT + opt[0])
    elif cmd == telnetlib.SB:
        if opt[0] == telnetlib.TTYPE and opt[1] == SEND:
            socket.sendall(telnetlib.IAC + telnetlib.SB
                           + telnetlib.TTYPE + IS + env_term
                           + chr(0) + telnetlib.IAC + telnetlib.SE)


def connect_bot(botname):
    """ Make a zombie telnet connection to the board as the given bot. """
    def read_forever(client):
        client.read_all()

    import telnetlib
    from x84.bbs.ini import CFG
    from x84.bbs.session import BOTLOCK, BOTQUEUE
    telnet_addr = CFG.get('telnet', 'addr')
    telnet_port = CFG.getint('telnet', 'port')
    with BOTLOCK:
        client = telnetlib.Telnet()
        client.set_option_negotiation_callback(callback_cmdopt)
        client.open(telnet_addr, telnet_port)
        BOTQUEUE.put(botname)
        t = threading.Thread(target=read_forever, args=(client,))
        t.daemon = True
        t.start()
