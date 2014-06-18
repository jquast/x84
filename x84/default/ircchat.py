"""
IRC script for x/84, https://github.com/jquast/x84

By default this connects to #1984 on EFNet, if you want to customise where
your clients are going, add this to your default configuration:

    [irc]
    server  = irc.efnet.org
    port    = 6667
    channel = #1984

If the server is using SSL, the block may look like this:

    [irc]
    server  = irc.smurfnet.ch
    port    = 6697
    ssl     = yes
    channel = #1984


"""

# unfortunately the hardlinemode stuff that irssi and such uses
# is not used, so each line causes a full screen fresh ..

import irc.client
import irc.connection
import time
import select
POLL_KEY = 0.15  # blocking ;; how often to poll keyboard
POLL_OUT = 0.25  # seconds elapsed before screen update, prevents flood
POLL_IRC = 0.05  # seconds to spend on processing IRC messages


def get_inputbar(pager):
    """ Return ScrollingEditor for use as inputbar. """
    from x84.bbs import getterminal, ScrollingEditor
    term = getterminal()
    width = pager.visible_width - 2
    yloc = (pager.yloc + pager.height) - 2
    xloc = pager.xloc + 2
    ibar = ScrollingEditor(width, yloc, xloc)
    ibar.enable_scrolling = True
    ibar.max_length = 512
    ibar.colors['highlight'] = term.white_on_blue
    return ibar


def get_pager(pager=None):
    """ Return Pager for use as chat window. """
    from x84.bbs import getterminal, Pager
    term = getterminal()
    height = (term.height - 4)
    width = int(term.width * .9)
    yloc = term.height - height - 1
    xloc = int(term.width / 2) - (width / 2)
    new_pager = Pager(height, width, yloc, xloc)
    if pager is not None:
        content = pager.content
        # little hack to keep empty lines from re-importing
        for row in range(len(content)):
            ucs = content[row]
            if ucs.startswith(u'\x1b(B'):
                ucs = ucs[len(u'\x1b(B'):]
            if ucs.endswith(u'\x1b[m'):
                ucs = ucs[len(u'\x1b[m'):]
            content[row] = ucs
        new_pager.update('\r\n'.join(content))
    new_pager.enable_scrolling = True
    new_pager.colors['border'] = term.blue
    new_pager.glyphs['right-vert'] = u'|'
    new_pager.glyphs['left-vert'] = u'|'
    new_pager.glyphs['bot-horiz'] = u''
    return new_pager


def main(channel=None, caller=None):
    """ Main procedure. """
    # pylint: disable=R0914,R0912,W0603
    #         Too many local variables
    #         Too many branches
    #         Using the global statement
    from x84.bbs import getsession, getterminal, getch, echo, ini
    import irc.client
    import irc.logging

    session, term = getsession(), getterminal()
    EXIT = False

    if channel is None:
        try:
            channel = ini.CFG.get('irc', 'channel')
        except:
            channel = '#1984'

    if not channel[0] in '#!':
        channel = '#' + channel
    try:
        host = ini.CFG.get('irc', 'server')
    except:
        host = 'irc.efnet.org'
    try:
        port = ini.CFG.getint('irc', 'port')
    except:
        port = 6667
    try:
        host_ssl = ini.CFG.getboolean('irc', 'ssl')
    except:
        host_ssl = False
    try:
        swag = ini.CFG.get('irc', 'swag')
    except:
        swag = 'x/84 BBS %s' % ini.CFG.get('system', 'bbsname')

    def refresh(pager, ipb, init=False):
        """ Returns terminal sequence suitable for refreshing screen. """
        session.activity = 'Chatting in %s' % channel
        pager.move_end()
        return u''.join((
            u''.join((u'\r\n', term.clear_eol,
                      u'\r\n', term.clear_eol,
                      term.bright_blue(u' mULTi USER nOTEPAD!'.center(term.width).rstrip()),
                      term.clear_eol,
                       (u'\r\n' + term.clear_eol) * (pager.height + 2),
                      pager.border())) if init else u'',
            pager.title(u''.join((
                term.reset,
                term.blue(u'-[ '),
                term.bold_blue(channel),
                term.blue(u' ]-'),))),
            pager.refresh(),
            ipb.refresh(),))

    def format_server(mesg):
        return u''.join((
            term.green('-'),
            term.bold_green('!'),
            term.green('- '),
            term.white(mesg),
        ))

    def format_chat(nick, target, mesg):
        return u''.join((
            term.bold_blue('<'),
            term.bold_white(nick),
            term.bold_blue('> '),
            term.white(mesg),
        ))

    def format_join(nick, chan):
        return u''.join((
            term.green('>'),
            term.bold_green('>'),
            term.green('> '),
            term.bold_white(nick),
            term.white(' joined '),
            term.bold_white(chan),
        ))

    def format_me(nick, target, mesg):
        return u''.join((
            term.bold_blue('* '),
            term.bold_white(nick),
            ' ',
            term.white(mesg),
        ))

    def format_quit(nick, mesg):
        return u''.join((
            term.green('<'),
            term.bold_green('<'),
            term.green('< '),
            term.bold_white(nick),
            term.white(' quit '),
            term.bold_black('['),
            term.white(mesg or 'bye'),
            term.bold_black(']'),
        ))

    def show_help():
        return u'\r\n'.join((
            term.bold_yellow('/help  ') + term.white('shows this help'),
            term.bold_yellow('/me    ') + term.white('to send an action'),
            term.bold_yellow('/topic ') + term.white('to see/set the topic'),
            term.bold_yellow('/quit  ') + term.white('to quit the chat'),
        ))

    pager = get_pager(None)  # output window
    readline = get_inputbar(pager)  # input bar
    echo(refresh(pager, readline, init=True))
    echo(pager.append(format_server(u''.join((
        term.white('use '),
        term.bold_white('/quit'),
        term.white(' to exit'),
    )))))
    dirty = time.time()

    def on_ctcp(c, event):
        if event.arguments[0] == 'ACTION':
            pager.append(format_me(
                event.source.nick,
                event.target,
                event.arguments[1],
            ))
            c.dirty = time.time()

    def on_connect(sock):
        pager.append(format_server('connected'))
        server.privmsg('maze', 'hi mom')
        dirty = time.time()

    def on_currenttopic(c, event):
        nick = event.source.nick
        chan, topic = event.arguments
        pager.append(format_server(u''.join((
            term.bold_white(nick),
            term.white(' set '),
            term.bold_white(chan),
            term.white(' topic to: '),
            term.bold_white(topic),
        ))))
        c.dirty = time.time()

    def on_erroneusnickname(c, event):
        pager.append(format_server('dude, that nick is not valid'))

    def on_error(c, event):
        pager.append(format_server('error: %s' % event.target))
        c.dirty = time.time()
        c.available = False

    def on_welcome(c, event):
        pager.append(format_server(u''.join((
            term.white('ready, logged in as '),
            term.bold_yellow(c.get_nickname()),
            term.white(' (use '),
            term.bold_white('/nick'),
            term.white(' to change)'),
        ))))
        pager.append(format_server('joining %s' % channel))
        c.join(channel)
        c.dirty = time.time()

    def on_disconnect(c, event=None):
        global dirty
        pager.append(format_server('disconnected'))
        c.dirty = time.time()
        c.available = False

    def on_endofnames(c, event):
        pager.append(format_server('%s end of names list' % event.arguments[0]))
        c.dirty = time.time()

    def on_join(c, event):
        global dirty
        chan = event.target
        nick = event.source.nick
        pager.append(format_join(nick, chan))
        c.dirty = time.time()

    def on_namreply(c, event):
        nicks = []
        for nick in event.arguments[2].split():
            if nick[0] in '@+%!':
                nicks.append(term.bold_red(nick[0]) + term.bold_white('%-9s' % nick[1:]))
            else:
                nicks.append(term.bold_white('%-9s' % nick))
        pager.append(format_server('%s %s' % (event.arguments[1], u' '.join(nicks))))
        c.dirty = time.time()

    def on_nick(c, event):
        pager.append(format_server(u''.join((
            term.bold_white(event.source.nick),
            term.white(' is now known as '),
            term.bold_white(event.target),
        ))))
        c.dirty = time.time()

    def on_nicknameinuse(c, event):
        server.nickname += '_'
        pager.append(format_server(u''.join((
            term.white('handle in use, trying '),
            term.bold_yellow(server.nickname),
        ))))
        server.nick(server.nickname)
        c.dirty = time.time()

    def on_topic(c, event):
        nick = event.source.nick
        chan = event.target
        topic = event.arguments[0]
        pager.append(format_server(u''.join((
            term.bold_white(nick),
            term.white(' set '),
            term.bold_white(chan),
            term.white(' topic to: '),
            term.bold_white(topic),
        ))))
        c.dirty = time.time()

    def on_pubmsg(c, event):
        global dirty
        pager.append(format_chat(
            event.source.nick,
            event.target,
            ' '.join(event.arguments)
        ))
        c.dirty = time.time()

    def on_part(c, event):
        pager.append(format_quit(event.source.nick, event.arguments[0]))
        c.dirty = time.time()

    def on_quit(c, event):
        pager.append(format_quit(event.source.nick, event.arguments[0]))
        c.dirty = time.time()

    if host_ssl:
        import ssl
        factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
    else:
        factory = irc.connection.Factory()

    client = irc.client.IRC(
        on_connect=on_connect,
        on_disconnect=on_disconnect,
    )
    server = client.server()
    server.dirty = None
    server.available = True
    server.add_global_handler('ctcp', on_ctcp)
    server.add_global_handler('currenttopic', on_currenttopic)
    server.add_global_handler('endofnames', on_endofnames)
    server.add_global_handler('erroneusnickname', on_erroneusnickname)
    server.add_global_handler('error', on_error)
    server.add_global_handler('join', on_join)
    server.add_global_handler('namreply', on_namreply)
    server.add_global_handler('nicknameinuse', on_nicknameinuse)
    server.add_global_handler('nick', on_nick)
    server.add_global_handler('part', on_part)
    server.add_global_handler('pubmsg', on_pubmsg)
    server.add_global_handler('quit', on_quit)
    server.add_global_handler('topic', on_topic)
    server.add_global_handler('welcome', on_welcome)
    echo(pager.append(format_server(u''.join((
        term.white('connecting to '),
        term.bold_white(host),
    )))))
    server.connect(
        host,
        port,
        session.handle.replace(' ', '_'),
        ircname=swag,
        connect_factory=factory,
    )

    def process_cmd(pager, msg):
        """ Process command recieved and display result in chat window. """
        cmd, args = msg.split()[0], msg.split()[1:]
        # pylint: disable=W0603
        #         Using the global statement
        global CHANNEL, NICKS, EXIT
        if cmd.lower() == '/help':
            pager.append(show_help())
            return True
        elif cmd.lower() in ('/act', '/me',):
            server.ctcp('action', channel, ' '.join(args))
            pager.append(format_me(server.nickname, channel, ' '.join(args)))
            server.dirty = time.time()
        elif cmd.lower() in ('/names', '/users', '/who'):
            server.names(channel)
        elif cmd.lower() == '/nick':
            if args:
                server.nickname = ' '.join(args)
                server.nick(server.nickname)
        elif cmd.lower() == '/say':
            server.privmsg(channel, ' '.join(args))
            pager.append(format_chat(server.nickname, channel, ' '.join(args)))
            server.dirty = time.time()
        elif cmd.lower() == '/topic':
            if args:
                server.topic(channel, ' '.join(args))
            else:
                server.topic(channel)
        elif cmd.lower() == '/quit':
            EXIT = True
            server.quit(' '.join(args))
        elif cmd.lower() == '/users':
            queue.put('NAMES %s' % CHANNEL)
            return True
        else:
            pager.append(format_server(u''.join((
                term.bold_red('syntax error '),
                term.white('do you need /help ?'),
            ))))
        return False

    while not EXIT and server.available:
        inp = getch(POLL_KEY)

        # poll for and process screen resize
        if session.poll_event('refresh') or (
                inp in (term.KEY_REFRESH, unichr(12))):
            pager = get_pager(pager)
            saved_inp = readline.content
            readline = get_inputbar(pager)
            readline.content = saved_inp
            echo(refresh(pager, readline, init=True))
            dirty = None

        # process keystroke as input, or, failing that,
        # as a command key to the pager. refresh portions of
        # input bar or act on cariage return, accordingly.
        elif inp is not None:
            otxt = readline.process_keystroke(inp)
            if readline.carriage_returned:
                if readline.content.startswith('/'):
                    if process_cmd(pager, readline.content):
                        pager = get_pager(pager)
                        echo(refresh(pager, readline, init=True))
                elif (0 != len(readline.content.strip())):
                    say(channel, readline.content)
                    dirty = time.time()
                readline = get_inputbar(pager)
                echo(readline.refresh())
            elif 0 == len(otxt):
                if type(inp) is int:
                    echo(pager.process_keystroke(inp))
            else:
                echo(u''.join((
                    readline.fixate(-1),
                    readline.colors.get('highlight', u''),
                    otxt, term.normal)))

        # update pager contents. Its a lot for 9600bps ..
        if server.dirty is not None:
            dirty = dirty or server.dirty

        if dirty is not None and time.time() - dirty > POLL_OUT:
            echo(refresh(pager, readline))
            dirty = None
            server.dirty = None

        # poll irc client stuff
        client.process_once(POLL_IRC)

    echo(u''.join((term.move(term.height, 0), term.normal)))
    server.quit()
    return True
