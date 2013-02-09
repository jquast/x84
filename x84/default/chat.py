""" Chat script for x/84, https://github.com/jquast/x84 """

# unfortunately the hardlinemode stuff that irssi and such uses
# is not used, so each line causes a full screen fresh ..

import time
POLL_KEY = 0.25 # blocking ;; how often to poll keyboard
POLL_OUT = 1.50 # seconds elapsed before screen update, prevents flood

def show_act(handle, mesg):
    from x84.bbs import getsession, getterminal
    session, term = getsession(), getterminal()
    return u''.join((
        time.strftime('%H:%M'), u' * ',
        (term.bold_green(handle) if handle != session.handle
            else term.green(handle)), u' ',
        mesg,))


def show_join(handle, sid, chan):
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
        term.bold(chan),))


def show_say(handle, mesg):
    from x84.bbs import getsession, getterminal, get_user
    session, term = getsession, getterminal
    return u''.join((
        time.strftime('%H:%M'), u' ',
        term.bold_black('<'),
        (term.bold_red(u'@') if 'sysop' in get_user(handle).groups
            else u''),
        (handle if handle != session.handle
            else term.bold(handle)),
        term.bold_black('>'), u' ',
        mesg,))

def get_inputbar():
    from x84.bbs import ScrollingEditor
    term = getterminal()
    width = term.width - 4
    yloc = term.height - 3
    xloc = 3
    ibar = ScrollingEditor(width, yloc, xloc)
    ibar.enable_scrolling = True
    ibar.max_length = 512
    return ibar

def get_pager(buf):
    from x84.bbs import Pager, getterminal
    term = getterminal()
    height = (term.height - 6)
    width = int(term.width * .9)
    yloc = term.height - height - 3
    xloc = (term.width / 2) - (width / 2)
    pager = Pager(height, width, yloc, xloc)
    pager.enable_scrolling = True
    pager.colors['border'] = term.cyan
    pager.glyphs['right-vert'] = u''
    pager.glyphs['bot-horiz'] = u''
    pager.update(buf)
    return pager


def main(channel=None):
    from x84.bbs import getsession, getterminal, getch, echo
    session, term = getsession(), getterminal()
    channel = '#partyline' if channel is None else channel
    EXIT=False
    nicks = dict()


    def refresh(pager, init=False):
        return u''.join((
            u''.join((u'\r\n\r\n',
                term.bold_cyan(u'//'),
                u' CitZENS bANd'.center(term.width).rstrip(),
                u'\r\n\r\n',
                u'\r\n' * pager.height,
                pager.border())) if init else u'',
            pager.title(channel),
            pager.move_end(),))


    def cmd(msg):
        global EXIT, channel
        cmd, args = msg.split()[0], msg.split()[1:]
        if cmd == '/help':
            echo(u"\r\nDon't panic.")
        if cmd == '/join' and len(args) == 1:
            join(channel)
            channel = args[0]
        elif cmd == '/quit':
            EXIT=True
        else:
            return False
        return True

    def broadcast_cc(payload):
        session.send_event('global', ('chat', payload))
        session.buffer_event('global', ('chat', payload))

    def join():
        payload = (session.sid, channel, (session.user.handle, 'join', None))
        broadcast_cc(payload)

    def say(mesg):
        payload = (session.sid, channel, (session.user.handle, 'say', mesg))
        broadcast_cc(payload)

    def act(mesg):
        payload = (session.sid, channel, (session.user.handle, 'act', mesg))
        broadcast_cc(payload)

    def part(reason):
        payload = (session.sid, channel, (session.user.handle, 'part', reason))
        broadcast_cc(payload)


    def process(buf, mesg):
        global nicks
        sid, tgt_channel, (handle, cmd, args) = mesg
        if (channel != tgt_channel and 'sysop' not in session.user.groups):
            # not for us!
            return
        if cmd == 'join' or handle not in nicks:
            buf.append(show_join(handle, sid, tgt_channel))
            nicks[handle] = sid
        if cmd == 'say':
            buf.append(show_say(handle, args))
        elif cmd == 'act':
            buf.append(show_act(handle, args))
        elif cmd == 'part':
            buf.append(show_part(handle, sid, tgt_channel, args))
        return buf

    # input bar
    readline = get_inputbar()
    echo(readline.refresh())

    # output window
    pager = get_pager()
    echo(refresh(pager, init=True))
    dirty = time.time()
    while not EXIT:
        inp = getch(POLL_KEY)

        # poll for and process screen resize
        if session.poll_event('refresh') or (
                inp in (u' ', term.KEY_REFRESH, unichr(12))):
            pager = get_pager(buf)
            echo(refresh(pager, init=True))
            dirty = None

        # poll for and process chat events,
        mesg = session.poll_event('global')
        if mesg is not None and mesg[0] == 'chat':
            n_buf = process(buf, mesg[1])
            if len(buf) > pager.height * 16:
                buf = buf[:pager.height * 16]
                pager.update(buf)
                dirty = time.time()
            elif len(n_buf) != len(buf):
                pager.update(buf)
                dirty = time.time()
            buf = n_buf

        # process keystroke as input, or, failing that,
        # as a command key to the pager. refresh portions of
        # input bar or act on cariage return, accordingly.
        if inp in (u'q', 'Q', term.KEY_EXIT, unichr(27)):
            return
        elif inp is not None:
            echo(readline.fixate())
            otxt = readline.process_keystroke(inp)
            if 0 == len(otxt) and type(inp) is int:
                echo(pager.process_keystroke(inp)
            elif(readline.carriage_returned and len(readline.content)):
                if readline.content.startswith('/'):
                    cmd(readline.content)
                elif 0 != len(readline.content.strip()):
                    say(readline.content)
                    readline = get_inputbar()
                    echo(readline.refresh())
                else:
                    echo(otxt)

        # update pager contents. Its a lot for 9600bps ..
        if dirty is not None and time.time() - dirty > POLL_OUT:
            echo(refresh(pager))
