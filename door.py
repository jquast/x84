
import pty
import sys
import os
import select

import util
import bbs

#def drop (type, node=0):
def drop (type):
 if (type == 'door32') or (type == 'door32.sys'):
  #fopen('drops/' + user['node'] + '/door32.sys', 'w')
  f = open('./door32.sys', 'w')
  # Line 1 : Comm type (0=local, 1=serial, 2=telnet)
  f.write ('2' + '\n')
  # Line 2 : Comm or socket handle
  f.write ('0' + '\n')
  # Line 3 : Baud rate
  f.write ('115200' + '\n')
  # Line 4 : BBSID (software name and version)
  f.write ('lithium v.03' + '\n')
  # Line 5 : User record position (1-based)
  f.write ('0' + '\n')
  # Line 6 : User's real name
  f.write (str(bbs.cli['username']) + '\n')
  # Line 7 : User's handle/alias
  f.write (str(bbs.cli['username']) + '\n')
  # Line 8 : User's security level
  f.write ('0' + '\n')
  # Line 9 : User's time left (in minutes)
  f.write ('999' + '\n')
  # Line 10: Emulation (0=ascii, 1=ansi, 2=avatar, 3=rip, 4=max graphics)
  f.write ('2' + '\n')
  # Line 11: Current node number
  f.write ('0' + '\n')
  f.close ()

def door (filename):
  door2 (filename, [], util.echo)

def fdoor (filename, args):
  door2 (filename, args, util.telnetecho)

def door2(filename, args, sendfunc):
  myfd = bbs.cli['socket'].fileno()
  print (str(myfd) + '\r\n')
  args.insert(0,filename)

  pid,ptyfd = pty.fork()
  if pid == 0:
    os.execv (filename,args)
    sys.exit(0)
  elif pid == -1:
    print 'Error trying pty.fork()'

  #print pid,fd

  def loop (ptyfd, myfd):
    while 1:
      a,b,c = select.select ([ptyfd,myfd],[],[],4)
      for f in a:
        if (f == ptyfd):
          try:
            buffer = os.read (ptyfd,8192)
            if (buffer == ''):
              return
            sendfunc (buffer)
#            os.write (myfd,buffer)
          except OSError:
            return
        if (f == myfd):
          try:
            buffer = os.read (myfd,8192)
            # Client disconnected
            if (buffer == ''):
              return
            os.write (ptyfd,buffer)
          except OSError:
            return
  loop (ptyfd, myfd)
  os.close (ptyfd)
  os.wait()
