"""
IRC client for X/84 BBS, http://1984.ws
$Id: irc.py,v 1.7 2009/05/31 16:14:07 dingo Exp $

This is a basic IRC client implementation, currently limited to
a single channel on a single server.
"""
__author__ = 'Wijnand Modderman-Lenstra <maze@pyth0n.org>'
__copyright__ = ['Copyright (c) 2008, 2009 Jeffrey Quast',
                 'Copyright (c) 2009 Wijnand Modderman']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
import os

MAX_INPUT = 200 # character limit for input
HISTORY = 200   # limit history in buffer

class Client(irc.IRCClient):
    # no http:// here, servers could se us as spambot
    userinfo = 'X/84 BBS, 1984.ws'
    realname = userinfo
    versionName = 'X/84 BBS'
    versionNum = 'CVS'
    versionEnv = ' '.join([os.uname()[0], os.uname()[-1]])
    sourceURL = 'http://1984.ws'

    def connectionMade(self):
        self.session = self.factory.session
        self.session.irc = self # how ugly is this?! :-)
        self.nickname = self.session.handle
        self.session.event_push('irc', ['connect'])
        irc.IRCClient.connectionMade(self)

    def connectionLost(self, reason):
        self.session.event_push('irc', ['disconnect', reason])
        irc.IRCClient.connectionLost(self, reason)

    def signedOn(self):
        self.join(self.factory.channel)

    def nickChanged(self, nick):
        self.nickname = nick
        self.session.event_push('irc', ['nick', 'you', nick])

    def userRenamed(self, old, nick):
        self.session.event_push('irc', ['nick', old, nick])

    def joined(self, channel):
        self.session.event_push('irc', ['join', self.nickname, channel.lower()])

    def userJoined(self, user, channel):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['join', nick, channel.lower()])

    def left(self, channel):
        self.session.event_push('irc', ['part', self.nickname, channel.lower()])

    def userLeft(self, user, channel):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['part', nick, channel.lower()])

    def userQuit(self, user, reason):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['quit', nick, reason])

    def privmsg(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['message', nick, channel, msg])

    def action(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['action', nick, channel, msg])

    def noticed(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['notice', nick, channel, msg])

    def topicUpdated(self, user, channel, newTopic):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ['topic', nick, channel, newTopic])

class ClientFactory(protocol.ClientFactory):
    protocol = Client

    def __init__(self, session, channel):
        self.session = session
        self.channel = channel

    def clientConnectionLost(self, connector, reason):
        self.session.event_push('irc', ['quit', self.session.irc.nickname,
            reason])

    def clientConnectionFailed(self, connector, reason):
        self.session.event_push('irc', ['failed', reason])

def main():
    session = getsession()
    getsession().activity = 'irc'
    factory = ClientFactory(session, ini.cfg.get('irc','channel'))
    connect = reactor.connectTCP \
        (ini.cfg.get('irc', 'server'), int(ini.cfg.get('irc','port')),
          factory)

    # colors and formatting
    fx = {
        'system': '-%s!%s-' \
          % (color(*LIGHTRED), color()),
        'join':   '%s>%s>%s>%s' \
          % (color(NORMAL, GREEN), color(*LIGHTGREEN), color(*WHITE), color()),
        'part':   '%s<%s<%s<%s' \
          % (color(*WHITE), color(*LIGHTRED), color(NORMAL, RED), color()),
        'quit':   '%s<%s<%s<%s' \
          % (color(*WHITE), color(GREY), color(*DARKGREY), color()),
        'nick':   '-%s!%s-' % (color(*LIGHTGREEN), color()),
    }

    # read-only pager for buffer history
    buffer = ParaClass \
      (h=session.height-6, w=session.width-2, y=6, x=6, xpad=0, ypad=1)
    buffer.add('%s connecting to %s:%d' % (fx['system'],
      ini.cfg.get('irc','server'), int(ini.cfg.get('irc','port'))))

    # editable pager for input
    inputbar = HorizEditor \
      (w=session.width-2, y=session.height-1, x=5, xpad=1, max=MAX_INPUT)
    inputbar.partial = inputbar.edit = inputbar.interactive = True

    def refresh ():
      echo (cls() + color())
      buffer.refresh (); buffer.border ()
      inputbar.clear (); inputbar.border ()
      inputbar.fixate ()
      art = fopen('art/irc.asc', 'r').readlines()
      for y, data in enumerate(art):
        echo (pos(10, y) + data)
      echo (cursor_show())

    refresh ()

    def handle_command(text):
        if ' ' in text:
            command, args = text.split(' ', 1)
        else:
            command = text
            args = ''

        if command == 'help':
            # make this a nice overlay some day
            buffer.add('%s available commands:' % (fx['system'],))
            for item in ['/help', '/me <text>', '/msg <where> <text>',
                '/notice <where> <text>', '/nick <nick>', '/topic [<topic>]',
                '/quit']:
                buffer.add('%s %s' % (fx['system'], item))
        elif command == 'me':
            if args:
                session.irc.me(factory.channel.split()[0], args)
                buffer.add('* %s%s%s %s' % (color(*WHITE),
                    session.irc.nickname, color(), text))
            else:
                buffer.add('%s /me <text>' % (fx['system'],))
        elif command == 'msg':
            args = args.split(' ', 1)
            if len(args) == 2:
                session.irc.msg(args[0], args[1])
                buffer.add('<%s%s%s -> %s> %s' % (color(*WHITE),
                    session.irc.nickname, color(), args[0], text))
            else:
                buffer.add('%s /msg <where> <text>' % (fx['system'],))
        elif command == 'notice':
            args = args.split(' ', 1)
            if len(args) == 2:
                session.irc.notice(args[0], args[1])
                buffer.add('*%s%s%s -> %s* %s' % (color(*WHITE),
                    session.irc.nickname, color(), args[0], text))
            else:
                buffer.add('%s /notice <where> <text>' % (fx['system'],))
        elif command == 'nick':
            if args:
                nick = args.split()[0]
                session.irc.setNick(nick)
            else:
                buffer.add('%s /nick <nick>' % (fx['system'],))
        elif command == 'topic':
            if args:
                session.irc.topic(factory.channel.split()[0], args)
            else:
                session.irc.topic(factory.channel.split()[0])
        elif command == 'quit':
            return False
        else:
            buffer.add('%s dude(tte), you srsly need /help' % (fx['system'],))
        return True

    while True:
        event, data = readevent(['input', 'irc'])
        if event == 'irc':
            if type(data) == list:
                kind = data[0]
                if kind == 'connect':
                    buffer.add('%s connected to server' % (fx['system'],))
                elif kind == 'disconnect':
                    buffer.add('%s connection lost: %s' % (fx['system'], data))
                elif kind == 'failed':
                    buffer.add('%s connection failed: %s' % (fx['system'], data))
                    break
                elif kind == 'join':
                    if data[1] == session.irc.nickname:
                        data[1] = 'you'
                    buffer.add('%s %s joined %s' % (fx['join'], data[1], data[2]))
                elif kind == 'part':
                    if data[1] == session.irc.nickname:
                        data[1] = 'you'
                    buffer.add('%s %s parted %s' % (fx['part'], data[1], data[2]))
                elif kind == 'quit':
                    if data[1] == session.irc.nickname:
                        data[1] = 'you'
                    buffer.add('%s %s quit [%s]' % (fx['quit'], data[1], data[2]))
                elif kind == 'message':
                    # hilight
                    if session.irc.nickname.lower() in data[3].lower():
                        data[1] = '%s%s%s' % (color(*YELLOW), data[1], color())
                    if data[2][0] in '#&+!':
                        buffer.add('<%s> %s' % (data[1], data[3]))
                    else:
                        buffer.add('<%s <- %s> %s' % (session.irc.nickname, data[1], data[3]))
                elif kind == 'nick':
                    buffer.add('%s %s changed nick to %s' % (fx['nick'],
                        data[1], data[2]))
                elif kind == 'notice':
                    if data[2][0] in '#&+!':
                        buffer.add('*%s* %s' % (data[1], data[3]))
                    else:
                        buffer.add('*%s <- %s* %s' % (session.irc.nickname, data[1], data[3]))
                elif kind == 'topic':
                    buffer.add('%s %s changed %s topic to: %s' %
                        (fx['system'], data[1], data[2], data[3]))

        elif event == 'input':
            inputbar.run(key=data)
            # @todo: tab completion
            # @todo: ^B -> bold, ^I -> inverse, etc.
            # @todo: ^CX,Y -> ANSI color
            if inputbar.enter:
                text = inputbar.data().strip()
                inputbar.update('')
                inputbar.clear()
                if not text:
                    continue

                if text[0] == '/':
                    if not handle_command(text[1:]):
                        break
                else:
                    buffer.add('<%s%s%s> %s' % (color(*WHITE),
                        session.irc.nickname, color(), text))
                    session.irc.say(factory.channel.split()[0], text)

    session.irc.quit('X/84 BBS, http://1984.ws')

    # Make sure the socket is dead before we return to the BBS
    try:
        connect.disconnect()
    except:
        pass
