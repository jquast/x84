""" IRC chat script for x/84. """
# std imports
import collections
import warnings
import datetime
import logging
import time
import re

# local
from x84.bbs import ScrollingEditor, getsession, echo, getterminal
from x84.bbs import get_ini, syncterm_setfont, LineEditor

# 3rd party
import irc.client

#: how many lines of scrollback to save for redrawing the interface?
MAX_SCROLLBACK = get_ini('irc', 'max_scrollback', getter='getint') or 200

#: how many characters of input to allow?
MAX_INPUT = get_ini('irc', 'max_input', getter='getint') or 200

#: irc server
SERVER = get_ini('irc', 'server') or 'irc.shaw.ca'

#: irc port
PORT = get_ini('irc', 'port', getter='getint') or 6667

#: irc channel
CHANNEL = get_ini('irc', 'channel') or '#1984'

#: maximum length irc nicks
MAX_NICK = get_ini('irc', 'max_nick', getter='getint') or 9

#: whether irc server requires ssl
ENABLE_SSL = get_ini('irc', 'ssl', getter='getboolean')

#: Whether to display PRIVNOTICE messages (such as motd)
ENABLE_PRIVNOTICE = get_ini('irc', 'enable_privnotice', getter='getboolean')

#: color of line editor
COLOR_INPUTBAR = get_ini('irc', 'color_inputbar') or 'reverse'

#: syncterm font to use
SYNCTERM_FONT = get_ini('irc', 'syncterm_font') or 'topaz'


class IRCChat(object):

    """
    IRC client, based on irc.client.SimpleIRCClient

    This is a class instead of a collection of functions at script-level scope
    because this allows us to easily use the _dispatcher trick... this means
    that we don't have to use add_global_handler() for each and every event we
    want to respond to; just add on_<eventname> as a method and you're done!
    """

    # pylint: disable=R0904

    def __init__(self, term, session):
        """ Class initializer. """
        self.log = logging.getLogger(__name__)
        self.reactor = irc.client.Reactor()
        self.connection = self.reactor.server()
        self.connected = False
        self.reactor.add_global_handler('all_events', self._dispatcher, -10)
        self.term = term
        self.session = session
        self.nick = None

    def _mirc_convert(self, text):
        """ Convert mIRC formatting codes into term sequence equivalents. """
        # pylint: disable=R0201

        def color_repl(match):
            """ Regex function for replacing color codes """

            mirc_colors = [
                'bold_white', 'black', 'blue', 'green', 'bold_red', 'red',
                'magenta', 'yellow', 'bold_yellow', 'bold_green', 'cyan',
                'bold_cyan', 'bold_blue', 'bold_magenta', 'bold_black',
                'white',
            ]
            num_colors = len(mirc_colors)
            bgc = None
            fgc = int(match.group(1))
            boldbg = False
            attr = ''
            if match.group(2):
                bgc = int(match.group(2))
                if bgc >= num_colors:
                    bgc = None
                else:
                    attr = 'on_{0}'.format(mirc_colors[bgc])
                    if 'bold_' in attr:
                        attr = attr.replace('bold_', '')
                        boldbg = True
            if fgc >= num_colors:
                fgc = None
            else:
                attr = '{0}{1}{2}'.format(mirc_colors[fgc],
                                          '_' if attr else '', attr)
            if boldbg:
                attr = 'blink_{0}'.format(attr)
            return getattr(self.term, attr)

        def mode_repl(match):
            """ Regex function for replacing 'modes'. """
            translate = {
                '\x0f': self.term.normal,
                '\x02': self.term.bold,
                '\x1f': self.term.underline,
                '\x15': self.term.underline,
                '\x12': self.term.reverse,
                '\x16': self.term.reverse,
            }
            return u'{0}{1}'.format(translate[match.group(1)], match.group(2))

        text = re.sub(r'\x03(\d{1,2})(?:,(\d{1,2}))?', color_repl, text)
        text = text.replace('\x03', self.term.normal)
        text = re.sub('(\x0f|\x02|\x1f|\x15|\x12|\x16)(.*?)', mode_repl, text)
        text = u''.join([text, self.term.normal])
        return text

    def _dispatcher(self, connection, event):
        """ Dispatch IRC events to their handlers (if they exist) """

        do_nothing = lambda c, e: None
        method = getattr(self, "on_" + event.type, do_nothing)
        method(connection, event)

    def queue(self, message):
        """ Queue up a message (with timestamp) to be displayed """
        now = datetime.datetime.now()
        data = u'{0} {1}'.format(
            self.term.bold_black(u'{0}:{1}'.format(
                '%02d' % now.hour, '%02d' % now.minute)),
            self._mirc_convert(message))
        self.session.buffer_event('irc', (data,))

    def _indicator(self, color=None, character=None):
        """ Construct an indicator to be used in output """
        # pylint: disable=R0201
        color = color or self.term.white
        character = character or u'*'
        return (u'{0}{1}{0}'.format(
            self.term.bold_black(u'-'), color(character)))

    def help(self):
        """ Show /HELP text """

        # pylint: disable=W0141
        commands = map(
            self.term.bold, [
                u'/HELP', u'/ME', u'/TOPIC', u'/NAMES'])
        self.queue(u'{0} Use {1} to quit. Other commands: {2}'.format(
            self._indicator(),
            self.term.bold(u'/QUIT'),
            self.term.white(u', ').join(commands),
        ))

    def connect(self, *args, **kwargs):
        """ Try to connect to the server """

        self.connection.connect(*args, **kwargs)

    def on_disconnect(self, connection, event):
        """ Disconnected; send quit event to end the main loop """
        # pylint: disable=R0201,W0613
        why = filter(None, event.arguments + [event.target])
        self.session.buffer_event('irc-quit', ' '.join(why))

    def on_nicknameinuse(self, connection, event):
        """ Nick is being used; pick another one. """
        # pylint: disable=W0613
        self.session.buffer_event('irc-connected')
        self.connected = True
        echo(u''.join([self.term.normal, u'\r\n',
                       u'Your nickname is in use or illegal. Pick a new one '
                       u'(blank to quit):\r\n']))
        led = LineEditor(width=MAX_NICK)
        newnick = led.read()
        echo(u'\r\n')
        if not newnick:
            self.session.buffer_event('irc-quit', 'canceled')
            return
        connection.nick(newnick)

    def on_erroneusnickname(self, connection, event):
        """ Erroneous nickname; pick another one. """
        return self.on_nicknameinuse(connection, event)

    def on_welcome(self, connection, event):
        """ Connected to the server; join the channel """
        # pylint: disable=W0613
        if not self.connected:
            self.session.buffer_event('irc-connected')
        self.nick = connection.get_nickname()
        self.session.buffer_event('irc-welcome')
        self.help()
        self.queue(u'{0} Server: {1}'.format(
            self._indicator(),
            self.term.bold(self.connection.server)
        ))
        if irc.client.is_channel(CHANNEL):
            connection.join(CHANNEL)

    def on_quit(self, _, event):
        """ Someone has /QUIT IRC """
        self.queue(u'{0} {1} has quit ({2})'.format(
            self._indicator(color=self.term.red),
            self.term.bold(event.source.nick),
            self.term.bold(event.arguments[0])
        ))

    def on_namreply(self, _, event):
        """ Reply received from /NAMES command """
        nicks = list()
        for nick in event.arguments[2].split(' '):
            stripped_nick = (nick[1:]
                             if nick[0] in ('@', '+',)
                             else nick)
            if stripped_nick != self.nick:
                nicks.append(nick)
        self.queue(u'{0} Users: {1}'.format(
            self._indicator(),
            self.term.bold(u', '.join(nicks) if nicks else u'<nobody>')
        ))

    def on_currenttopic(self, _, event):
        """ Reply received from /TOPIC command """
        self.queue(u'{0} Topic: {1}'.format(
            self._indicator(),
            self.term.bold(event.arguments[1])
        ))

    def on_topic(self, _, event):
        """ Someone has changed the channel topic """
        self.queue(u'{0} {1} has changed the topic to {2}'.format(
            self._indicator(color=self.term.bold),
            self.term.bold(event.source.nick),
            self.term.bold(event.arguments[0])
        ))

    def on_privnotice(self, _, event):
        """ Received a private notice. """
        if ENABLE_PRIVNOTICE:
            self.queue('{0} {1}'.format(event.target, event.arguments[0]))

    def format_pubmsg(self, source, msg, mode=None):
        """ Helper to format public messages. """
        # pylint: disable=R0201
        color = self.term.bold if mode is None else mode
        nick = color(u'<{0}>'.format(source))
        return u'{0} {1}'.format(nick, msg)

    def on_pubmsg(self, _, event):
        """ Public message has been received. """
        color = None
        if self.nick in event.arguments[0]:
            color = self.term.bold_white_on_magenta
        self.queue(
            self.format_pubmsg(event.source.nick, event.arguments[0], color))

    def on_join(self, connection, event):
        """ Someone has joined the channel """
        # if it's the current user that has joined, display it differently
        if event.source.nick == connection.get_nickname():
            self.queue(u'{0} Channel: {1}'.format(
                self._indicator(),
                self.term.bold(CHANNEL)
            ))
        else:
            self.queue(u'{0} {1} has joined the channel'.format(
                self._indicator(color=self.term.green),
                self.term.bold(event.source.nick)
            ))

    def on_kick(self, connection, event):
        """ Someone has been kicked from the channel """
        self.queue(u'{0} {1} has kicked {2} ({3})'.format(
            self._indicator(color=self.term.red),
            self.term.bold(event.source.nick),
            self.term.bold(event.arguments[0]),
            self.term.bold(event.arguments[1])
        ))

        # if the current user was kicked, rejoin the channel
        if event.arguments[0] == self.nick:
            connection.join(CHANNEL)

    def on_part(self, _, event):
        """ Someone has /PART-ed the channel """
        self.queue(u'{0} {1} has left the channel'.format(
            self._indicator(color=self.term.red),
            self.term.bold(event.source.nick)
        ))

    def format_action(self, source, action, color=None):
        """ Helper for formatting action messages """
        color = self.term.bold_white if color is None else color
        return u'{0} {1} {2}'.format(
            self._indicator(character=u'+', color=self.term.bold_black),
            color(source), action)

    def on_action(self, _, event):
        """ Someone has performed an action in the channel """
        color = None
        if self.nick in event.arguments[0]:
            color = self.term.bold_white_on_magenta
        self.queue(
            self.format_action(event.source.nick, event.arguments[0], color))

    def on_nick(self, _, event):
        """ Someone has changed their nickname """
        self.queue(u'{0} {1} has changed their nickname to {2}'.format(
            self._indicator(),
            self.term.bold(event.source.nick),
            self.term.bold(event.target)
        ))

    def on_mode(self, _, event):
        """ Someone has changed modes on the channel or a user """
        self.queue(u'{0} {1} sets mode {2}'.format(
            self._indicator(color=self.term.bold),
            self.term.bold(event.source.nick),
            self.term.bold(u' '.join(event.arguments))
        ))

    def on_pubnotice(self, _, event):
        """ Public notice has been received """
        self.queue(u'{0} NOTICE ({1}) {2}'.format(
            self._indicator(),
            self.term.bold(event.source.nick),
            self.term.bold(u' '.join(event.arguments))
        ))

    def on_error(self, _, event):
        """ Some error has been received """
        err_desc = (u'error (type={event.type}, source={event.source}, '
                    'target={event.target}, arguments={event.arguments}'
                    .format(event=event))
        self.log.error('error: {0}'.format(err_desc))
        self.queue(u'{0} ERROR: {1} '.format(
            self._indicator(color=self.term.bold_red), err_desc))


def clean_up(term):
    """ Clean up after ourselves """
    echo(term.normal)
    echo(term.clear)


def establish_connection(term, session):
    """
    Establish a connection to the IRC server.

    Returns IRCChat instance or False depending on whether it was successful.
    """
    scrollback = collections.deque(maxlen=MAX_SCROLLBACK)
    kwargs = dict()
    if ENABLE_SSL:
        from ssl import wrap_socket
        from irc.connection import Factory
        kwargs['connect_factory'] = Factory(wrapper=wrap_socket)

    echo(u'Connecting to {server}:{port} for channel {chan}.\r\n\r\n'
         'press [{key_q}] to abort ... '.format(
             server=SERVER, port=PORT, chan=CHANNEL, key_q=term.bold(u'q')))

    client = IRCChat(term, session)
    irc_handle = session.user.handle.replace(' ', '_')
    try:
        # pylint: disable=W0142
        client.connect(SERVER, PORT, irc_handle, **kwargs)
    except irc.client.ServerConnectionError:
        echo(term.bold_red(u'Connection error!'))
        term.inkey(3)
        raise EOFError()

    while True:
        client.reactor.process_once()
        event, data = session.read_events(
            ('irc', 'irc-quit', 'irc-connected', 'input'), timeout=0.02)
        if event == 'irc':
            # show on-connect motd data if any received
            echo(u'\r\n{0}'.format(data[0]))
            scrollback.append(data[0])
        elif event == 'irc-connected':
            break
        elif event == 'input':
            session.buffer_input(data, pushback=True)
            inp = term.inkey(0)
            while inp is not None:
                if inp.lower() == u'q' or inp.code == term.KEY_ESCAPE:
                    echo(u'Canceled!')
                    raise EOFError()
                inp = term.inkey(0)
        elif event == 'irc-quit':
            echo(term.bold_red(u'\r\nConnection failed: {0}!'.format(data)))
            term.inkey(3)
            raise EOFError()

    while True:
        client.reactor.process_once()
        event, data = session.read_events(
            ('irc', 'irc-welcome', 'irc-quit', 'input'), timeout=0.2)
        if event == 'irc':
            # show on-connect motd data if any received
            echo(u'\r\n{0}'.format(data[0]))
            scrollback.append(data[0])
        if event == 'irc-quit':
            echo(term.bold_red(u'\r\nConnection lost: {0}!'.format(data)))
            term.inkey(3)
            raise EOFError()
        elif event == 'input':
            session.buffer_input(data, pushback=True)
            inp = term.inkey(0)
            while inp is not None:
                if inp.lower() == u'q' or inp.code == term.KEY_ESCAPE:
                    echo(u'Canceled!')
                    raise EOFError()
                inp = term.inkey(0)
        elif event == 'irc-welcome':
            return client, scrollback


def refresh_event(term, scrollback, editor):
    """ Screen resized, adjust layout """

    editor.width = term.width + 1
    editor.xloc = -1
    editor.yloc = term.height - 1

    # re-wrap chat log
    numlines = term.height - 2
    sofar = 0
    output = list()
    for line in reversed(scrollback):
        wrapped = term.wrap(line, term.width - 1)
        sofar += len(wrapped)
        output = wrapped + output
        if sofar >= numlines:
            break
    output = output[numlines * -1:]
    echo(u''.join([
        term.normal, term.home, term.clear_eos,
        term.move(editor.yloc + 1, 0),
        u'\r\n'.join(output),
        u'\r\n', editor.refresh()]))


def irc_event(term, data, scrollback, editor):
    """ IRC output has been received """

    data = data[0]
    # add it to our scrollback and trim
    scrollback.append(data)

    # blank out the line with the input bar, wrap output, redraw input bar
    echo(u''.join([
        term.normal,
        term.move(editor.yloc + 1, 0),
        term.clear_eol,
        term.move_x(0),
        u'\r\n'.join(term.wrap(data, term.width - 1,
                               break_long_words=True)),
        term.move(editor.yloc + 1, 0),
        u'\r\n',
        term.move(editor.yloc, 0),
        editor.refresh(),
    ]))


def input_event(term, client, editor):
    """
    React to input event, processing /commands.

    Returns True, unless the caller should exit, then False.
    """
    retval = True
    inp = term.inkey(0)
    while inp:
        if inp.is_sequence:
            echo(editor.process_keystroke(inp.code))
        else:
            echo(editor.process_keystroke(inp))

        if not editor.carriage_returned:
            retval = True
        else:
            # process return key
            line = editor.content.rstrip()

            # clear editor
            editor.update(u'')
            echo(editor.refresh())

            lowered = line.lower()

            # fix mIRC codes that are sent improperly
            line = (line
                    .replace('\x15', '\x1f')   # underline
                    .replace('\x12', '\x16'))  # reverse

            # parse input for potential commands
            if lowered == u'/quit':
                client.connection.quit(
                    u'x/84 bbs https://github.com/jquast/x84')
                retval = False
            elif lowered == u'/topic':
                client.connection.topic(CHANNEL)
            elif lowered in (u'/names', u'/who',):
                client.connection.names(CHANNEL)
            elif lowered.startswith(u'/me ') and len(lowered) > 4:
                client.connection.action(CHANNEL, line[4:])
                client.queue(client.format_action(client.nick, line[4:],
                                                  term.bold_blue))
            elif lowered == u'/help':
                client.help()
            elif line.startswith(u'/'):
                # some other .. unsupported command
                retval = True
            else:
                # no command was received; post pubmsg, instead
                client.connection.privmsg(CHANNEL, line)
                client.queue(client.format_pubmsg(
                    client.nick, line, term.bold_blue))
        inp = term.inkey(0)
    return retval


def main():
    """ x/84 script launch point """

    term, session = getterminal(), getsession()
    session.activity = u'Chatting on IRC'
    session.flush_event('irc')

    # move to bottom of screen, reset attribute
    echo(term.pos(term.height) + term.normal)

    # create a new, empty screen
    echo(u'\r\n' * (term.height + 1))
    echo(term.home + term.clear)

    # set font
    if SYNCTERM_FONT and term.kind.startswith('ansi'):
        echo(syncterm_setfont(SYNCTERM_FONT))

    try:
        client, scrollback = establish_connection(term, session)
    except EOFError:
        # connection failed,
        return clean_up(term)

    # ignore "not in view" warning for AnsiWindow
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        editor = ScrollingEditor(
            width=term.width + 1,
            xloc=-1,
            yloc=term.height,
            colors={'highlight': getattr(term, COLOR_INPUTBAR)},
            max_length=MAX_INPUT
        )

    refresh_event(term, scrollback, editor)

    while True:
        client.reactor.process_once()
        event, data = session.read_events(
            ('irc-quit', 'irc', 'input', 'refresh'), timeout=0.1)
        if event == 'refresh':
            refresh_event(term, scrollback, editor)
            continue
        elif event == 'irc':
            irc_event(term, data, scrollback, editor)
        elif event == 'input':
            session.buffer_input(data, pushback=True)
            if not input_event(term, client, editor):
                break
        elif event == 'irc-quit':
            time.sleep(0.5)
            break
    client.connection.disconnect()
    clean_up(term)
