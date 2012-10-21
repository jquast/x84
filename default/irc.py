"""
IRC client for X/84 BBS, http://github.com/jquast/x84/

This is a basic IRC client implementation, currently limited to
a single channel on a single server. Contributed by maze !
"""
__author__ = 'Wijnand Modderman-Lenstra <maze@pyth0n.org>'
__copyright__ = ['Copyright (c) 2008, 2009 Jeffrey Quast',
                 'Copyright (c) 2009 Wijnand Modderman']
__license__ = 'ISC'
__url__ = 'http://github.com/jquast/x84/'

import twisted.words.protocols.irc
import twisted.internet.reactor
import twisted.internet.protocol
import os


class Client(twisted.words.protocols.irc.IRCClient):
    """
    Provice
    """
    userinfo = 'X/84 1984.bbs'
    realname = userinfo
    versionName = 'X/84 BBS'
    versionNum = 'CVS'
    versionEnv = ' '.join([os.uname()[0], os.uname()[-1]])
    sourceURL = 'http://github.com/jquast/x84'

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
        self.session.event_push('irc', ('nick',
            'you', nick,))

    def userRenamed(self, old, nick):
        self.session.event_push('irc', ('nick',
            old, nick,))

    def joined(self, channel):
        self.session.event_push('irc', ('join',
            self.nickname, channel.lower(),))

    def userJoined(self, user, channel):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('join',
            nick, channel.lower(),))

    def left(self, channel):
        self.session.event_push('irc', ('part',
            self.nickname, channel.lower(),))

    def userLeft(self, user, channel):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('part',
            nick, channel.lower(),))

    def userQuit(self, user, reason):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('quit',
            nick, reason,))

    def privmsg(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('message',
            nick, channel, msg,))

    def action(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('action',
            nick, channel, msg))

    def noticed(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('notice',
            nick, channel, msg,))

    def topicUpdated(self, user, channel, newTopic):
        nick = user.split('!', 1)[0]
        self.session.event_push('irc', ('topic',
            nick, channel, newTopic))

class ClientFactory(protocol.ClientFactory):
    protocol = Client

    def __init__(self, session, channel):
        self.session = session
        self.channel = channel

    def clientConnectionLost(self, connector, reason):
        self.session.event_push('irc', ('quit',
            self.session.irc.nickname, reason,))

    def clientConnectionFailed(self, connector, reason):
        self.session.event_push('irc', ('failed',
            reason,))

# read-only pager for buffer history
def get_pager():
    """
    Create and reutrn irc log Pager object
    """
    term = getterminal()
    log_height = term.height - 6
    log_width = term.width - 2
    log_yloc = 6
    log_xloc = 6
    pager = Pager (height=log_height, width=log_width,
            yloc=log_yloc, xloc=log_xloc)
    pager.xpadding = 1
    return pager

def get_inputbar():
    """
    Create and return irc ScrollingEditor object
    """
    term = getterminal()
    inp_width = term.width - 2
    inp_yloc = term.height - 1
    inp_xloc = 5
    term = getterminal()
    inp = ScrollingEditor (width=inp_width, yloc=inp_yloc, xloc=inp_xloc)
    inp.max_length = 200
    inp.xpadding = 0
    inp.ypadding = 1
    return inp

def get_fx():
    """
    Create and return formatters for irc events
    """
    term = getterminal()
    return {'system': '-%s!%s-' % (term.bold_red, term.normal),
            'join': '%s>%s>%s>%s' % (term.normal + term.green, term.bold_green,
                term.bold_white, term.normal),
            'part': '%s<%s<%s<%s' % (term.bold_white, term.bold_red,
                term.normal + term.red, term.normal),
            'quit': '%s<%s<%s<%s' % (term.bold_white, term.white,
                term.bold_black, term.normal),
            'nick': '-%s!%s-' % (term.bold_green, term.normal),
            }

def main():
    session, term = getsession(), getterminal()
    channel = ini.CFG.get('irc','channel')
    server = ini.CFG.get('irc', 'server')
    port = ini.CFG.getint('irc','port')
    session.activity = 'irc %s/%s' % (server, channel)
    factory = ClientFactory(session, channel)
    connect = twisted.internet.reactor.connectTCP (server, port, factory)

    def redraw (content):
        rstr = u''
        buf = get_pager ()
        inp = get_inputbar ()
        rstr += buf.update ('\n'.join(content))
        inputbar.colors['border'] = term.bright_black
        rstr += inputbar.border()
        art = fopen('art/irc-header.asc', 'r').readlines()
        for y, data in enumerate(art):
            echo (term.move(y, 10) + data)
        rstr += term.normal_cursor
        rstr += inputbar.fixate ()

    #def refresh ():
    #    echo (cls() + color())
    #    logbuffer.refresh (); logbuffer.border ()
    #    inputbar.clear (); inputbar.border ()
    #    inputbar.fixate ()
    #refresh ()

    fx = get_fx()
    buf.append ('%s connecting to %s:%d' % (fx['system'], server, port))

    inputbar = get_inputbar ()
    echo redraw (buf.content)


    def handle_command(text):
        if ' ' in text:
            command, args = text.split(' ', 1)
        else:
            command = text
            args = ''

        if command == 'help':
            # make this a nice overlay some day
            buf.add('%s available commands:' % (fx['system'],))
            for item in ['/help', '/me <text>', '/msg <where> <text>',
                '/notice <where> <text>', '/nick <nick>', '/topic [<topic>]',
                '/quit']:
                buf.add('%s %s' % (fx['system'], item))
        elif command == 'me':
            if args:
                session.irc.me(factory.channel.split()[0], args)
                buf.add('* %s%s%s %s' % (color(*WHITE),
                    session.irc.nickname, color(), text))
            else:
                buf.add('%s /me <text>' % (fx['system'],))
        elif command == 'msg':
            args = args.split(' ', 1)
            if len(args) == 2:
                session.irc.msg(args[0], args[1])
                buf.add('<%s%s%s -> %s> %s' % (color(*WHITE),
                    session.irc.nickname, color(), args[0], text))
            else:
                buf.add('%s /msg <where> <text>' % (fx['system'],))
        elif command == 'notice':
            args = args.split(' ', 1)
            if len(args) == 2:
                session.irc.notice(args[0], args[1])
                buf.add('*%s%s%s -> %s* %s' % (color(*WHITE),
                    session.irc.nickname, color(), args[0], text))
            else:
                buf.add('%s /notice <where> <text>' % (fx['system'],))
        elif command == 'nick':
            if args:
                nick = args.split()[0]
                session.irc.setNick(nick)
            else:
                buf.add('%s /nick <nick>' % (fx['system'],))
        elif command == 'topic':
            if args:
                session.irc.topic(factory.channel.split()[0], args)
            else:
                session.irc.topic(factory.channel.split()[0])
        elif command == 'quit':
            return False
        else:
            buf.add('%s dude(tte), you srsly need /help' % (fx['system'],))
        return True

    while True:
        event, data = readevent(['input', 'irc'])
        if event == 'irc':
            if type(data) == list:
                kind = data[0]
                if kind == 'connect':
                    buf.add('%s connected to server' % (fx['system'],))
                elif kind == 'disconnect':
                    buf.add('%s connection lost: %s' % (fx['system'], data))
                elif kind == 'failed':
                    buf.add('%s connection failed: %s' % (fx['system'], data))
                    break
                elif kind == 'join':
                    if data[1] == session.irc.nickname:
                        data[1] = 'you'
                    buf.add('%s %s joined %s' % (fx['join'], data[1], data[2]))
                elif kind == 'part':
                    if data[1] == session.irc.nickname:
                        data[1] = 'you'
                    buf.add('%s %s parted %s' % (fx['part'], data[1], data[2]))
                elif kind == 'quit':
                    if data[1] == session.irc.nickname:
                        data[1] = 'you'
                    buf.add('%s %s quit [%s]' % (fx['quit'], data[1], data[2]))
                elif kind == 'message':
                    # hilight
                    if session.irc.nickname.lower() in data[3].lower():
                        data[1] = '%s%s%s' % (color(*YELLOW), data[1], color())
                    if data[2][0] in '#&+!':
                        buf.add('<%s> %s' % (data[1], data[3]))
                    else:
                        buf.add('<%s <- %s> %s' % (session.irc.nickname, data[1], data[3]))
                elif kind == 'nick':
                    buf.add('%s %s changed nick to %s' % (fx['nick'],
                        data[1], data[2]))
                elif kind == 'notice':
                    if data[2][0] in '#&+!':
                        buf.add('*%s* %s' % (data[1], data[3]))
                    else:
                        buf.add('*%s <- %s* %s' % (session.irc.nickname, data[1], data[3]))
                elif kind == 'topic':
                    buf.add('%s %s changed %s topic to: %s' %
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
                    buf.add('<%s%s%s> %s' % (color(*WHITE),
                        session.irc.nickname, color(), text))
                    session.irc.say(factory.channel.split()[0], text)

    session.irc.quit('X/84 BBS, http://1984.ws')

    # Make sure the socket is dead before we return to the BBS
    try:
        connect.disconnect()
    except:
        pass
