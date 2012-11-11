#!/usr/bin/env python
import termios
import struct
import signal
import fcntl
import sys
import os

# This script requires a modified version of pexpect,
import pexpect
from x84.bbs.cp437 import from_cp437

def main():
    assert os.getenv('LANG') == 'en_US.UTF-8', (
        'This program requires locale of en_US.UTF-8.')

    shell = pexpect.spawn(os.getenv('SHELL'))

    def propogate_winch(sig, data):
        height, width = struct.unpack('hhhh', fcntl.ioctl(
            sys.stdout.fileno(), termios.TIOCGWINSZ, '\000' * 8))[0:2]
        shell.setwinsize(height, width)

    # install signal handler to propogate window resize events to subprocess
    signal.signal(signal.SIGWINCH, propogate_winch)
    shell.interact(output_filter=from_cp437, encoding='utf8')


if __name__ == '__main__':
    sys.exit(main())
