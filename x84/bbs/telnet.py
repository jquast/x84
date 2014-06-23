"""
telnet extras for x/x84 bbs, https://github.com/jquast/x84
"""

def callback_cmdopt(socket, cmd, opt, env_term=None, term=None):
	""" Callback for telnetlib.Telnet.set_option_negotiation_callback. """
	import telnetlib
	import struct
	IS = chr(0)  # Sub-process negotiation IS command
	if env_term is None:
		env_term = 'vt220'
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
						   + struct.pack('!HH', term.width, term.height)
						   + telnetlib.IAC + telnetlib.SE)
		else:
			socket.sendall(telnetlib.IAC + telnetlib.WONT + opt[0])
	elif cmd == telnetlib.SB:
		if opt[0] == telnetlib.TTYPE and opt[1] == SEND:
			socket.sendall(telnetlib.IAC + telnetlib.SB
						   + telnetlib.TTYPE + IS + env_term
						   + chr(0) + telnetlib.IAC + telnetlib.SE)
