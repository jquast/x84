""" Chat script for x/84, https://github.com/jquast/x84 """

# unfortunately the hardlinemode stuff that irssi and such uses
# is not used, so each line causes a full screen fresh ..

import time
POLL_KEY = 0.15  # blocking ;; how often to poll keyboard
POLL_OUT = 0.25  # seconds elapsed before screen update, prevents flood

CHANNEL = None
NICKS = dict()
EXIT = False


def show_help():
    """ return string suitable for response to /help. """
    return u'\n'.join((
        u'   /join #channel',
        u'   /act mesg',
        u'   /part [reason]',
        u'   /quit [reason]',
        u'   /users',
        u'   /whois handle',))


def process(mesg):
    """
    Process a command recieved by event system. and return string
    suitable for displaying in chat window.
    """
    from x84.bbs import getsession
    session = getsession()
    sid, tgt_channel, (handle, cmd, args) = mesg
    ucs = u''
    # pylint: disable=W0602
    # Using global for 'NICKS' but no assignment is done
    global NICKS
    if (CHANNEL != tgt_channel and 'sysop' not in session.user.groups):
        ucs = u''
    elif cmd == 'join':
        if handle not in NICKS:
            NICKS[handle] = sid
            ucs = show_join(handle, sid, tgt_channel)
    elif handle not in NICKS:
        NICKS[handle] = sid
    elif cmd == 'part':
        if handle in NICKS:
            del NICKS[handle]
        ucs = show_part(handle, sid, tgt_channel, args)
    elif cmd == 'say':
        ucs = show_say(handle, tgt_channel, args)
    elif cmd == 'act':
        ucs = show_act(handle, tgt_channel, args)
    else:
        ucs = u'unhandled: %r' % (mesg,)
    return ucs


def show_act(handle, tgt_channel, mesg):
    """ return terminal sequence for /act performed by handle. """
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' * ',
        (term.bold_green(handle) if handle != session.handle
            else term.green(handle)),
        (u':%s' % (tgt_channel,)
            if 'sysop' in session.user.groups
            else u''), u' ',
        mesg,))


def show_join(handle, sid, chan):
    """ return terminal sequence for /join performed by handle. """
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' ',
        term.blue('-'), u'!', term.blue('-'),
        u' ', term.bold_cyan(handle), u' ',
        (u''.join((term.bold_black('['),
                   term.cyan(sid), term.bold_black(']'), u' ',))
            if 'sysop' in session.user.groups else u''),
        'has joined ',
        term.bold(chan),))


def show_part(handle, sid, chan, reason):
    """ return terminal sequence for /part performed by handle. """
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' ',
        term.blue('-'), u'!', term.blue('-'),
        u' ', term.bold_cyan(handle), u' ',
        (u''.join((term.bold_black('['),
                   term.cyan(sid), term.bold_black(']'), u' ',))
            if 'sysop' in session.user.groups else u''),
        'has left ',
        term.bold(chan),
        u' (%s)' % (reason,) if reason and 0 != len(reason) else u'',))


def show_whois(attrs):
    """ return terminal sequence for /whois result. """
    from x84.bbs import getsession, getterminal, timeago
    session, term = getsession(), getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' ',
        term.blue('-'), u'!', term.blue('-'),
        u' ', term.bold(attrs['handle']), u' ',
        (u''.join((term.bold_black('['),
                   term.cyan(attrs['sid']), term.bold_black(']'), u' ',))
            if 'sysop' in session.user.groups else u''), u'\n',
        time.strftime('%H:%M'), u' ',
        term.blue('-'), u'!', term.blue('-'),
        u' ', u'CONNECtED ',
        term.bold_cyan(timeago(time.time() - attrs['connect_time'])),
        ' AGO.', u'\n',
        time.strftime('%H:%M'), u' ',
        term.blue('-'), u'!', term.blue('-'),
        u' ', term.bold(u'idlE: '),
        term.bold_cyan(timeago(time.time() - attrs['idle'])), u'\n',
    ))


def show_nicks(handles):
    """ return terminal sequence for /users result. """
    from x84.bbs import getterminal
    term = getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' ',
        term.blue('-'), u'!', term.blue('-'),
        u' ', term.bold_cyan('%d' % (len(handles))), u' ',
        u'user%s: ' % (u's' if len(handles) > 1 else u''),
        u', '.join(handles) + u'\n',))


def show_say(handle, tgt_channel, mesg):
    """ return terminal sequence for /say performed by handle. """
    from x84.bbs import getsession, getterminal, get_user
    session, term = getsession(), getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' ',
        term.bold_black(u'<'),
        (term.bold_red(u'@') if handle != 'anonymous'
            and 'sysop' in get_user(handle).groups
            else u''),
        (handle if handle != session.handle
            else term.bold(handle)),
        (u':%s' % (tgt_channel,)
            if 'sysop' in session.user.groups
            else u''),
        term.bold_black(u'>'), u' ',
        mesg,))


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
    ibar.colors['highlight'] = term.cyan_reverse
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
    new_pager.colors['border'] = term.cyan
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
    from x84.bbs import getsession, getterminal, getch, echo
    session, term = getsession(), getterminal()
    global CHANNEL, NICKS
    CHANNEL = '#partyline' if channel is None else channel
    NICKS = dict()

    # sysop repy_to is -1 to force user, otherwise prompt
    if channel == session.sid and caller not in (-1, None):
        echo(u''.join((
            term.normal, u'\a',
            u'\r\n', term.clear_eol,
            u'\r\n', term.clear_eol,
            term.bold_green(u' ** '),
            caller,
            u' would like to chat, accept? ',
            term.bold(u'['),
            term.bold_green_underline(u'yn'),
            term.bold(u']'),
        )))
        while True:
            inp = getch()
            if inp in (u'y', u'Y'):
                break
            elif inp in (u'n', u'N'):
                return False

    def refresh(pager, ipb, init=False):
        """ Returns terminal sequence suitable for refreshing screen. """
        session.activity = 'Chatting in %s' % (
            CHANNEL if not CHANNEL.startswith('#')
            and not 'sysop' in session.user.groups
            else u'PRiVAtE ChANNEl',) if CHANNEL is not None else (
                u'WAitiNG fOR ChAt')
        pager.move_end()
        return u''.join((
            u''.join((u'\r\n', term.clear_eol,
                      u'\r\n', term.clear_eol,
                      term.bold_cyan(u'//'),
                      u' CitZENS bANd'.center(term.width).rstrip(),
                      term.clear_eol,
                       (u'\r\n' + term.clear_eol) * (pager.height + 2),
                      pager.border())) if init else u'',
            pager.title(u''.join((
                term.bold_cyan(u']- '),
                CHANNEL if CHANNEL is not None else u'',
                term.bold_cyan(u' -['),))),
            pager.refresh(),
            ipb.refresh(),))

    def process_cmd(pager, msg):
        """ Process command recieved and display result in chat window. """
        cmd, args = msg.split()[0], msg.split()[1:]
        # pylint: disable=W0603
        #         Using the global statement
        global CHANNEL, NICKS, EXIT
        if cmd.lower() == '/help':
            pager.append(show_help())
            return True
        elif cmd.lower() == '/join' and len(args) == 1:
            part_chan('lEAViNG fOR ANOthER ChANNEl')
            CHANNEL = args[0]
            NICKS = dict()
            join_chan()
            return True
        elif cmd.lower() in ('/act', '/me',):
            act(u' '.join(args))
        elif cmd.lower() == '/say':
            say(u' '.join(args))
        elif cmd.lower() == '/part':
            part_chan(u' '.join(args))
            CHANNEL = None
            NICKS = dict()
            return True
        elif cmd.lower() == '/quit':
            part_chan('quit')
            EXIT = True
        elif cmd.lower() == '/users':
            pager.append(show_nicks(NICKS.keys()))
            return True
        elif cmd.lower() == '/whois' and len(args) == 1:
            whois(args[0])
        return False

    def broadcast_cc(payload):
        """ Broadcast chat even, carbon copy ourselves. """
        session.send_event('global', ('chat', payload))
        session.buffer_event('global', ('chat', payload))

    def join_chan():
        """ Bradcast chat even for /join. """
        payload = (session.sid, CHANNEL, (session.user.handle, 'join', None))
        broadcast_cc(payload)

    def say(mesg):
        """ Signal chat event for /say. """
        payload = (session.sid, CHANNEL, (session.user.handle, 'say', mesg))
        broadcast_cc(payload)

    def act(mesg):
        """ Signal chat event for /act. """
        payload = (session.sid, CHANNEL, (session.user.handle, 'act', mesg))
        broadcast_cc(payload)

    def part_chan(reason):
        """ Signal chat event for /part. """
        payload = (session.sid, CHANNEL, (session.user.handle, 'part', reason))
        broadcast_cc(payload)

    def whois(handle):
        """ Perform /whois request for ``handle``. """
        if not handle in NICKS:
            return
        session.send_event('route', (NICKS[handle], 'info-req', session.sid,))

    def whois_response(attrs):
        """ Display /whois response for given ``attrs``. """
        return show_whois(attrs)

    pager = get_pager(None)  # output window
    readline = get_inputbar(pager)  # input bar
    echo(refresh(pager, readline, init=True))
    echo(pager.append("tYPE '/quit' tO EXit."))
    dirty = time.time()
    join_chan()
    while not EXIT:
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

        # poll for and process chat events,
        mesg = session.poll_event('global')
        if mesg is not None:
            otxt = process(mesg[1])
            if 0 != len(otxt):
                echo(pager.append(otxt))
                dirty = None if dirty is None else time.time()

        # poll for whois response
        data = session.poll_event('info-ack')
        if data is not None:
            # session id, attributes = data
            echo(pager.append(whois_response(data[1])))
            dirty = None if dirty is None else time.time()

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
                elif (0 != len(readline.content.strip())
                        and CHANNEL is not None):
                    say(readline.content)
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
        if dirty is not None and time.time() - dirty > POLL_OUT:
            echo(refresh(pager, readline))
            dirty = None
    echo(u''.join((term.move(term.height, 0), term.normal)))
    return True
