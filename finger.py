"""
Finger protocol support for X/84 BBS, http://1984.ws
$Id: finger.py,v 1.3 2010/01/02 00:54:00 dingo Exp $
#"""
__license__ = 'ISC'
__author__ = 'Wijnand Modderman <python@tehmaze.com>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast <dingo@1984.ws>',
                 'Copyright (c) 2005 Johannes Lundberg <johannes.lundberg@gmail.com>']

import sys, time, socket
from twisted.internet.protocol import ServerFactory
from twisted.protocols import basic

import log
import msgbase
import userbase

CRLF = '\r\n'

class FingerProtocol(basic.LineReceiver):
  # Implementing http://tools.ietf.org/html/rfc1288
  def __init__(self, sessionlist):
    self.sessionlist = sessionlist

  def findUser(self, u):
    return 'Login name: %-8s%s' \
           'Office: %s%s' \
           'Directory: /home/%-8s' \
            % (u.handle, CRLF, u.location, CRLF, u.handle,)

  def findOnline(self, u):
    l= []
    for sid, s in self.sessionlist.items():
      if u.handle == s.handle:
        for t in s.terminals:
          # return only the oldest attached terminal
          t_attach=time.strftime('%b %d %H:%M:%S',time.localtime(t.attachtime))
          l.append('On since %s on %s from %s' \
                % (t_attach, t.type, t.info.split(':')[0]))
    if not len(l):
      # XXX 'last login: xxx 'on %s from %s' not implemented
      l.append ('Last login: %s' \
        % (time.strftime('%a %b %d %H:%M', time.localtime(u.lastcall)),))
    return CRLF.join(l)

  def findMail(self, u):
    l=[]
    privmsgs = msgbase.listprivatemsgs(recipient=u.handle)
    newmsgs = sorted([msg for msg in privmsgs if not msgbase.getmsg(msg).read])
    if newmsgs:
      newest_mail=msgbase.getmsg(newmsgs[-1])
      l.append('New mail received %s;' \
        % (time.strftime('%a %b %d %H:%M',
           time.localtime(newest_mail.sendtime)),))
      l_last= sorted([( \
        msgbase.getmsg(msg).read, msg) \
        for msg in privmsgs if msgbase.getmsg(msg).read])
      if len(l_last):
        m_last= msgbase.getmsg(l_last[-1][1])
        l.append('  unread since %s' \
          % (time.strftime('%a %b %d %H:%M',
             time.localtime(m_last.read)),))
    else:
      l.append('No unread mail')
    return CRLF.join(l)

  def findPlan(self, u):
    if hasattr(u, 'plan') and u.plan:
      return 'Plan:%s%s' % (CRLF,u.plan)
    else:
      return 'No Plan.'

  def lineReceived(self, line):
    query = line.strip()
    response = 'Site: %s%sCommand line: %s<CRLF>%s%s' \
        % (socket.getfqdn(), CRLF, query, CRLF, CRLF)
    address = self.transport.getPeer()
    if not query:
      log.write ('finger', '%s:%s null query' % (address.host, address.port,))
      # finger @domain, list all terminal sessions
      response += 'Login    From         TTY Idle      When  Office%s' % (CRLF,)
      for sid, session in self.sessionlist.items():
        user = userbase.getuser(session.handle)
        handle = user and user.handle or '?'
        ttys = []
        if not len(session.terminals):
          ttys.append ('%-8s %-12s    ' % (handle, 'detached',))
        else:
          for t in session.terminals:
            if t.type == 'local':
              ttys.append ('%-8s %-8s %7s' % (handle, t.type, t.info.split(':')[0],))
            else:
              # dont reveal remote ip address, only the tty
              ttys.append ('%-8s %-8s %7s' % (handle, t.type, t.tty))
        for tty in ttys:
          response += '%s %s %s  %s%s' \
            % (tty, self.humantime(session.idle()),
               time.strftime('%a %H:%M', time.localtime(session.logintime)),
               user and user.location or '-', CRLF)
    else:
      user= userbase.getuser(query)
      if not user:
        # XXX support ambigous lookup
        response += 'Not found.%s' % (CRLF,)
        log.write ('finger', '%s:%s query FAILED: %s' \
          % (address.host, address.port, query))
      else:
        response += self.findUser(user) + CRLF
        response += self.findOnline(user) + CRLF
        response += self.findMail(user) + CRLF
        response += self.findPlan(user)
        log.write ('finger', '%s:%s query OK: %s' \
          % (address.host, address.port, query))
    self.transport.write(response + CRLF)
    self.transport.loseConnection()

  def humantime(s):
    s = int(s)
    if s <= 60:
      return '%3ss' % (str(s),)
    elif s <= 3600:
      h, s = divmod(s, 3600)
      return '%d:%02d' % (h, s//60)
    elif s <= 36000:
      return '%3sh' % (str(s // 3600),)
    elif s <= 86400:
      return '%3sd' % (str(s // 86400),)
    else:
      return 'INF.'

  humantime = staticmethod(humantime)

class FingerFactory(ServerFactory):
  def __init__(self, sessionlist):
    self.sessionlist = sessionlist

  def buildProtocol(self, addr):
    return FingerProtocol(self.sessionlist)
