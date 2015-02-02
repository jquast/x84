""" Chat script for x/84. """
# std imports
from __future__ import division
import collections
import logging
import math

# local
from x84.bbs import echo, getsession, getterminal, syncterm_setfont, showart
from x84.bbs import ScrollingEditor, get_ini
from x84.bbs.session import Script

ChatEvent = collections.namedtuple('ChatEvent', [
    'session_id', 'channel', 'handle', 'command', 'cmd_args'])

WindowDimension = collections.namedtuple(
    'WindowDimension', ['yloc', 'xloc', 'height', 'width'])

#: for ytalk-like version of split-screen of small windows, show user@bbs
system_bbsname = get_ini(section='system', key='bbsname')

ANSWER, HANGUP, REJECTED = 1, 2, 3

art_encoding = 'cp437'

#: filepath to artfile displayed for this script
art_file = get_ini(
    section='chat', key='art_file'
) or 'art/chat.ans'

#: encoding used to display artfile
art_encoding = get_ini(
    section='chat', key='art_encoding'
) or 'cp437'

#: fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='chat', key='syncterm_font'
) or 'cp437'


def prompt_chat_request(term, pos, call_from):
    chat_prompt = (
        u'{marker}{nick} would like to chat, accept? {lb}{yn}{rb}'
        .format(marker=term.bold(u' ** '),
                nick=term.bold(call_from),
                lb=term.bold_black(u'['),
                rb=term.bold_black(u']'),
                yn=term.bold(u'yn')))
    echo(term.normal + u'\a')
    echo(term.move(pos.yloc, pos.xloc))
    echo(chat_prompt.center(pos.width, ' '))
    while True:
        inp = term.inkey()
        if inp.lower() == u'y':
            return True
        elif inp.lower() == u'n':
            return False


def refresh_screen(term, who):
    # create a new, empty screen
    echo(term.normal)
    echo(term.move(term.height - 1, 0))
    echo(u'\r\n' * (term.height + 1))

    ans_height, ans_width = 24, 80
    if term.width < ans_width or term.height < ans_height:
        # screen is too small for ansi file, use ytalk-like format
        center_line = term.height // 2
        echo(term.move(center_line, 0))
        echo(term.center(u'= {0}@{1} ='.format(who, system_bbsname),
                         term.width, '-'))
        top_window = WindowDimension(
            yloc=-1, xloc=-1,
            height=center_line + 2,
            width=term.width + 2)
        bot_window = WindowDimension(
            yloc=center_line,
            xloc=-1,
            height=term.height - (center_line - 1),
            width=term.width + 2)
    else:
        # center ansi file
        center_y = (math.floor(term.height / 2 - (ans_height / 2)))
        center_x = math.floor(term.width / 2 - (ans_width / 2))
        ypos, xpos = max(0, int(center_y)), max(0, int(center_x))
        art_generator = showart(art_file, encoding=art_encoding)
        for y_offset, line in enumerate(art_generator):
            _ypos = ypos + y_offset
            if _ypos <= term.height:
                echo(term.move(_ypos, xpos))
                echo(line.rstrip())
        top_window = WindowDimension(
            yloc=ypos,
            xloc=xpos + 1,
            height=9, width=78)
        bot_window = WindowDimension(
            yloc=ypos + 14,
            xloc=xpos + 1,
            height=10, width=78)
    return top_window, bot_window


def make_editor_series(winsize, editors):
    colors = {'highlight': u''}
    # prevent horizontal scrolling prior to final column
    margin_pct = 100 - (100 / (winsize.width - 3))
    # scroll at final column
    scroll_pct = 100 / (winsize.width - 3)
    return [
        ScrollingEditor(
            yloc=_yloc, xloc=winsize.xloc, width=winsize.width,
            colors=colors, margin_pct=margin_pct, scroll_pct=scroll_pct,
            content=(u'' if not editors or _idx >= len(editors)
                     else editors[_idx].content),
            max_length=winsize.width
        ) for _idx, _yloc in enumerate(range(
            winsize.yloc, winsize.yloc + winsize.height + -2))]


def get_editors(top_winsize, bot_winsize, top_editors, bot_editors):
    return (make_editor_series(top_winsize, top_editors),
            make_editor_series(bot_winsize, bot_editors))


def do_chat(session, term, log, other_sid, dial=None, call_from=None):
    """ Main procedure. """
    editor = None
    dirty = True
    top_idx = bot_idx = 0
    dialing = bool(dial)
    answering = bool(call_from)

    data = session.flush_event('chat')
    if data:
        log.debug('Flushed chat data: %r', data)

    session.activity = (u'{doing} {call_from}'.format(
        doing=('answering call from' if answering else
               'requesting chat with'),
        call_from=call_from))

    # send chat request
    if dial:
        # force other user to gosub this script, with 'other_sid' as ours.
        script = Script(name='chat', args=(),
                        kwargs={'call_from': session.user.handle,
                                'other_sid': session.sid})
        event, data = 'gosub', script
        route_data = (other_sid, event) + tuple(data)
        session.send_event('route', route_data)

    top_editors, bot_editors = [], []
    while True:
        if dirty:
            who = dial if dialing else call_from
            top_winsize, bot_winsize = refresh_screen(term, who)
            top_editors, bot_editors = get_editors(top_winsize, bot_winsize,
                                                   top_editors, bot_editors)

            # when a screen is resized, we must adjust our editor indicies to
            # ensure they are within range
            top_idx = min(top_idx, len(top_editors) - 1)
            bot_idx = min(bot_idx, len(bot_editors) - 1)

            for editor in top_editors + bot_editors:
                echo(editor.clear())
                echo(editor.refresh())

            echo(top_editors[top_idx].fixate())
            if dialing:
                display_dialing(term, pos=bot_winsize, who=who)
            if answering:
                display_answering(term, pos=bot_winsize, who=who)
            dirty = False

        event, data = session.read_events(
            events=('chat', 'input', 'refresh', 'chat'))

        if event == 'refresh':
            dirty = True
        elif event == 'input':
            session.buffer_input(data, pushback=True)
            if answering:
                if do_answer(term, session, other_sid) is False:
                    # 'n', hangup
                    break
                answering = False
                dirty = True
            elif dialing:
                inp = term.inkey(0)
                if inp.lower() == u'q' or inp.code == term.KEY_ESCAPE:
                    break
            else:
                # process keystroke and send to other party
                top_editors, top_idx = do_input(
                    term, session, editors=top_editors, edit_idx=top_idx,
                    other_sid=other_sid)
                if top_editors is None and top_idx is None:
                    # do_input() returns (None, None) on exit
                    break

        elif event == 'chat':
            if data == (HANGUP,):
                display_hangup(term, pos=top_winsize, who=call_from or dial)
                term.inkey()
                break
            elif data == (REJECTED,):
                display_rejected(term, pos=bot_winsize, who=dial)
                term.inkey()
                break
            elif dialing and data == (ANSWER,):
                dialing = False
                dirty = True
                continue
            elif isinstance(data[0], basestring):
                bot_editors, bot_idx = recv_input(editors=bot_editors,
                                                  edit_idx=bot_idx,
                                                  inp=data[0])
            else:
                log.error("Unexpected data for event 'chat': {0!r}", data)


def display_dialing(term, pos, who):
    echo(term.move(pos.yloc + (pos.height // 2), pos.xloc))
    echo(u'dialing {0}, [q]uit ...'.format(who).center(pos.width).rstrip())


def display_answering(term, pos, who):
    echo(term.move(pos.yloc + (pos.height // 2), pos.xloc))
    echo(u'accept chat from {0} [yn] ?'.format(who).center(pos.width).rstrip())
    echo(u'\b\b')


def display_hangup(term, pos, who):
    echo(term.move(pos.yloc + (pos.height // 2), pos.xloc))
    echo(u'{0} hung up.'.format(who).center(pos.width).rstrip())


def display_rejected(term, pos, who):
    echo(term.move(pos.yloc + (pos.height // 2), pos.xloc))
    echo(u'{0} is rejecting chat requests.'.format(who).center(pos.width).rstrip())


def do_answer(term, session, other_sid):
    while True:
        inp = term.inkey()
        if inp.lower() == u'y':
            route_data = (other_sid, 'chat') + (ANSWER,)
            session.send_event('route', route_data)
            return True
        elif inp.lower() == u'n':
            return False


def clear_editor(editor):
    """ Clear content and refresh line editor ``editor``. """
    editor.update(u'')
    echo(editor.refresh())


def recv_input(editors, edit_idx, inp):
    nextline = False
    editor = editors[edit_idx]

    # position cursor
    echo(editor.fixate())

    if inp.is_sequence:
        if ((inp.code in editor.keyset['backspace'] or
             inp in editor.keyset['backspace']
             ) and editor.content == u''):
            # editor is empty, and we've backspaced, allow
            # backspacing into previous line
            edit_idx = (len(editors) - 1 if edit_idx == 0
                        else edit_idx - 1)
            editor = editors[edit_idx]
            editor.update(editor.content)
            echo(editor.refresh() + editor.fixate())
        echo(editor.process_keystroke(inp.code))
    else:
        echo(editor.process_keystroke(inp))

    # return pressed or at margin (bell)
    nextline = (editor.carriage_returned or
                editor.bell)

    if nextline:
        edit_idx = (0 if edit_idx == len(editors) - 1
                    else edit_idx + 1)

        # clear new editor-line
        clear_editor(editors[edit_idx])
        if edit_idx + 1 < len(editors):
            # as well as the next
            clear_editor(editors[edit_idx + 1])
        echo(editors[edit_idx].fixate())

    return editors, edit_idx


def do_input(term, session, editors, edit_idx, other_sid):
    inp = term.inkey(0)
    while inp:
        if inp.is_sequence and inp.code == term.KEY_ESCAPE:
            # escape was pressed, exit
            return (None, None)
        editors, edit_idx = recv_input(editors, edit_idx, inp)

        route_data = (other_sid, 'chat') + (inp,)
        session.send_event('route', route_data)

        inp = term.inkey(0)
    return editors, edit_idx


def do_hangup(session, other_sid):
    route_data = (other_sid, 'chat') + (HANGUP,)
    session.send_event('route', route_data)


def main(*args, **kwargs):
    session, term = getsession(), getterminal()
    log = logging.getLogger(__name__)

    if kwargs.get('call_from') and session.kind not in ('telnet', 'ssh'):
        # reject chat requests unless we are a tty terminal of telnet or ssh.
        route_data = (kwargs['other_sid'], 'chat') + (REJECTED,)
        session.send_event('route', route_data)
        log.debug("Rejected chat request; session.kind=%s", session.kind)
        return True

    # set syncterm font, if any
    if syncterm_font and term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    with term.fullscreen():
        try:
            return do_chat(session, term, log=log, *args, **kwargs)
        finally:
            do_hangup(session, other_sid=kwargs['other_sid'])
