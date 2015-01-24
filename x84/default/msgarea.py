"""
Message area for x/84.

This script provides an interface to check for new
messages, subscribe to and browse tags and networks,
find all, or unread messages, or all messages since
last login.

It determines a set of message-ids that are then
forwarded to the message browser interface.
"""
# std imports
import collections
import datetime
import fnmatch

# local
from x84.bbs import (
    syncterm_setfont,
    ScrollingEditor,
    decode_pipe,
    getterminal,
    getsession,
    LineEditor,
    list_msgs,
    list_tags,
    get_ini,
    get_msg,
    timeago,
    gosub,
    echo,
)

from common import (
    render_menu_entries,
    show_description,
    display_banner,
    display_prompt,
    prompt_pager,
    waitprompt,
)


TIME_FMT = '%A %b-%d, %Y at %r'

#: banner art displayed in main()
art_file = 'art/hx-msg.ans'

#: character encoding of banner art
art_encoding = 'cp437'

#: preferred fontset for SyncTerm emulator
syncterm_font = 'topaz'

#: When set False, menu items are not colorized and render much
#: faster on slower systems (such as raspberry pi).
colored_menu_items = get_ini(
    section='msgarea', key='colored_menu_items', getter='getboolean'
) or True

#: color used for description text
color_text = get_ini(
    section='msgarea', key='color_text'
) or 'white'

#: color used for menu key entries
color_highlight = get_ini(
    section='msgarea', key='color_highlight'
) or 'bold_magenta'

#: color used for prompt
color_backlight = get_ini(
    section='msgarea', key='color_prompt',
) or 'magenta_reverse'

#: color used for brackets ``[`` and ``]``
color_lowlight = get_ini(
    section='msgarea', key='color_lowlight'
) or 'bold_black'


def get_menu(messages):
    """ Return list of menu items by given dict ``messages``. """
    MenuItem = collections.namedtuple('MenuItem', ['inp_key', 'text'])
    items = []
    if messages['new']:
        items.extend([
            MenuItem(u'n', u'new ({0})'.format(len(messages['new']))),
            MenuItem(u'm', u'mark all read'),
        ])
    if messages['all']:
        items.append(
            MenuItem(u'a', u'all ({0})'.format(len(messages['all']))),
        )
    items.extend([
        MenuItem(u'p', u'post public'),
        MenuItem(u'w', u'write private'),
        MenuItem(u'c', u'change area'),
        MenuItem(u'?', u'help'),
        MenuItem(u'q', u'quit'),
    ])
    return items


def do_mark_as_read(session, message_indicies):
    """ Mark all given messages read. """
    session.user['readmsgs'] = (
        session.user.get('readmsgs', set()) | set(message_indicies)
    )


def get_messages_by_subscription(session, subscription):
    all_tags = list_tags()
    messages = {'all': set(), 'new': set()}
    messages_bytag = {}
    messages_read = session.user.get('readmsgs', set())

    # this looks like perl code
    for tag_pattern in subscription:
        messages_bytag[tag_pattern] = collections.defaultdict(set)
        for tag_match in fnmatch.filter(all_tags, tag_pattern):
            msg_indicies = list_msgs(tags=(tag_match,))
            messages['all'].update(msg_indicies)
            messages_bytag[tag_pattern]['all'].update(msg_indicies)
        messages_bytag[tag_pattern]['new'] = (
            messages_bytag[tag_pattern]['all'] - messages_read)
    messages['new'] = (messages['all'] - messages_read)

    return messages, messages_bytag


def describe_message_area(term, subscription, messages_bytags, colors):
    get_num = lambda lookup, tag_pattern, grp: len(lookup[tag_pattern][grp])
    return u''.join((
        colors['highlight'](u'msgarea: '),
        colors['text'](u', ').join((
            u''.join((
                quote(term, tag_pattern, colors),
                u'({num_new}/{num_all})'.format(
                    num_new=get_num(messages_bytags, tag_pattern, 'new'),
                    num_all=get_num(messages_bytags, tag_pattern, 'all'))
            )) for tag_pattern in subscription)),
        u'\r\n\r\n',
    ))


def validate_tag_patterns(tag_patterns):
    all_tags = list_tags()
    removed = []
    for tag_pattern in set(tag_patterns):
        if not fnmatch.filter(all_tags, tag_pattern):
            removed.append(tag_pattern)
            tag_patterns.remove(tag_pattern)
    return removed, tag_patterns


def quote(term, txt, colors):
    return u''.join(((u'"'), colors['highlight'](txt), (u'"')))


def describe_available_tags(term, colors):
    sorted_tags = sorted([(len(list_msgs(tags=(tag,))), tag)
                          for tag in list_tags()], reverse=True)
    decorated_tags = [
        colors['text'](tag) +
        colors['lowlight']('({0})'.format(num_msgs))
        for num_msgs, tag in sorted_tags]

    description = u''.join((
        colors['highlight'](u'available tags'), ': ',
        colors['text'](u', ').join(decorated_tags),
        colors['text'](u'.'),
        u'\r\n\r\n',
    ))
    return show_description(term, description, color=None)


def describe_message_system(term, colors):
    """ Display help text about message tagging. """

    def describe_network_tags():
        """ Return description text of message networks, if any. """
        server_tags = get_ini('msg', 'server_tags', split=True)
        network_tags = get_ini('msg', 'network_tags', split=True)

        if not (network_tags or server_tags):
            return u''
        return u''.join((
            u'\r\n\r\n',
            colors['text'](u'This board participates in intra-bbs '
                           'messaging, '),
            u''.join((
                colors['text'](u'hosting network messages by tag '),
                u', '.join(quote(term, tag, colors) for tag in server_tags),
            )) if server_tags else u'',
            (colors['text'](
                u' and ') if (server_tags and network_tags) else u''),
            u''.join((
                colors['text'](u'participating in network messages by tag '),
                u', '.join(quote(term, tag, colors) for tag in network_tags),
            )) if network_tags else u'',
            u'.',
        ))

    def describe_group_tags():
        groups = getsession().user.groups
        if not groups:
            return u''

        return u''.join((
            u'\r\n\r\n',
            colors['text'](
                u'Finally, private messages may be shared among groups.  You '
                u'may post messages to any group you are a member of: '),
            colors['text'](
                u', '.join(quote(term, grp, colors) for grp in groups)),
            colors['text'](u'.')
        ))

    description = u''.join((
        u'\r\n',
        colors['text'](
            u'You can think of tags as a system of providing context to any '
            u'message stored on this system.  A tag might provide the '
            u'general label of the topic of conversation, which may be '
            u'subscribed to.  For example, '),
        quote(term, u'python', colors),
        colors['text'](
            u' may be used for topics related to the python programming '
            u'language.  This is similar to flicker or gmail tags, or '
            u'hashtags.'),
        describe_network_tags(),
        u'\r\n\r\n',
        colors['text'](
            u'Furthermore, glob expressions may be used such as '),
        quote(term, u'*', colors),
        u' ',
        colors['text']('for all messages, or expression '),
        quote(term, u'lang-*', colors),
        u' ',
        colors['text']('might subscribe to both '),
        quote(term, u'lang-python', colors),
        colors['text'](u' and '),
        quote(term, u'lang-go', colors),
        colors['text'](u'.'),
        describe_group_tags(),
    ))
    return show_description(term, description, color=None)


def prompt_subscription(session, term, yloc, subscription, colors):
    """
    This function is called to assign a new set of subscription
    tags for a user.  If escape is pressed, the existing value
    is used, or '*' is used if not previously set.

    This should be called for first-time users, and optionally
    at any later time to change a subscription.
    """

    if session.user.get('msg_subscription', None) is None:
        # force-display introductory description for first-time users.
        yloc += describe_message_system(term, colors)
        echo(u'\r\n\r\n')
        yloc += 2

    yloc += describe_available_tags(term, colors) + 1

    # for small screens, scroll and leave room for prompt & errors
    if yloc > term.height + 3:
        echo(u'\r\n' * 3)
        yloc = term.height - 3

    # and prompt for setting of message tags
    xloc = max(0, (term.width // 2) - 40)
    input_prefix = u':: subscription tags:'
    echo(u''.join((term.move(yloc, xloc), input_prefix)))

    xloc += len(input_prefix)
    wide = min(40, (term.width - xloc - 2))

    while True:
        editor = ScrollingEditor(xloc=xloc, yloc=yloc-1, width=wide,
                                 colors={'highlight': colors['backlight']},
                                 content=u', '.join(subscription),
                                 max_length=100)

        # Prompt for and evaluate the given input, splitting by comma,
        # removing any empty items, and defaulting to ['*'] on escape.
        inp = editor.read() or u''
        subscription = filter(None, set(map(unicode.strip, inp.split(',')))
                              ) or set([u'*'])

        # Then, reduce to only validate tag patterns, tracking those
        # that do not match any known tags, and display a warning and
        # re-prompt if any are removed.
        removed, subscription = validate_tag_patterns(subscription)

        # clear existing warning, if any
        echo(u''.join((term.normal, u'\r\n\r\n', term.clear_eos)))
        if removed:
            # and display any unmatched tags as a warning, re-prompt
            txt = ''.join((
                term.bold_red(u"The following patterns are not matched: "),
                u', '.join(removed)))
            show_description(term, txt, color=None)
            continue

        # otherwise everything is fine,
        # return new subscription set
        return subscription


def allow_tag(session, idx):
    """
    Whether user is allowed to tag a message.

    :rtype: bool

    A user can tag a message if the given session's user is:

    * the message author or recipient.
    * a member of sysop or moderator group.
    * a member of any existing tag-matching user group.
    """
    moderated = get_ini('msg', 'moderated_tags', getter='getboolean')
    moderator_groups = get_ini('msg', 'tag_moderators', split=True)
    if not moderated and 'sysop' in session.user.groups:
        return True

    elif moderated and any(grp in session.user.groups
                           for grp in moderator_groups):
        return True

    msg = get_msg(idx)
    if session.user.handle in (msg.recipient, msg.author):
        return True

    for tag in msg.tags:
        if tag in session.user.groups:
            return True
    return False


def display_message(session, term, msg_index, colors):
    """ Format message of index ``idx``. """
    color_handle = lambda handle: (
        colors['highlight'](handle)
        if handle == session.user.handle
        else handle)
    msg = get_msg(msg_index)
    txt_sent = msg.stime.strftime(TIME_FMT)
    txt_sentago = colors['highlight'](
        timeago((datetime.datetime.now() - msg.stime)
                .total_seconds()).strip())
    txt_to = color_handle(msg.recipient)
    txt_from = color_handle(msg.author)
    txt_tags = u', '.join((quote(term, tag, colors)
                           for tag in msg.tags))
    txt_subject = colors['highlight'](msg.subject)
    txt_body = decode_pipe(msg.body)
    txt_breaker = ('-' if session.encoding == 'ansi' else u'\u2500'
                   ) * min(80, term.width)
    msg_txt = (
        u'\r\n{txt_breaker}\r\n'
        u'   from: {txt_from}\r\n'
        u'     to: {txt_to}\r\n'
        u'   sent: {txt_sent} ({txt_sentago} ago)\r\n'
        u'   tags: {txt_tags}\r\n'
        u'subject: {txt_subject}\r\n'
        u'\r\n'
        u'{txt_body}'
        .format(txt_breaker=txt_breaker,
                txt_from=txt_from, txt_to=txt_to,
                txt_sent=txt_sent, txt_sentago=txt_sentago,
                txt_tags=txt_tags, txt_subject=txt_subject,
                txt_body=txt_body))

    do_mark_as_read(session, [msg_index])

    prompt_pager(content=msg_txt.splitlines(), line_no=0,
                 width=min(80, term.width),
                 colors=colors, breaker=u'- ', end_prompt=False,
                 break_long_words=True)


def do_reader_prompt(session, term, index, message_indices, colors):
    xpos = max(0, int((term.width / 2) - (80 / 2)))
    opts = []
    if index:
        opts += (('p', 'rev'),)
    if index < len(message_indices) - 1:
        opts += (('n', 'ext'),)
    if allow_tag(session, message_indices[index]):
        opts += (('e', 'dit tags'),)
    opts += (('r', 'eply'),)
    opts += (('q', 'uit'),)
    opts += (('idx', ''),)
    while True:
        if xpos:
            echo(term.move_x(xpos))
        echo(u''.join((
            colors['lowlight'](u'['),
            colors['highlight'](str(index + 1)),
            u'/{0}'.format(len(message_indices)),
            colors['lowlight'](u']'),
            u' ',
            u', '.join((
                u''.join((colors['lowlight'](u'['),
                          colors['highlight'](key),
                          colors['lowlight'](u']'),
                          value
                          )) for key, value in opts)),
            u': ',
            term.clear_eol,
        )))
        width = max(2, len(str(len(message_indices))))
        inp = LineEditor(width, colors={'highlight': colors['backlight']}).read()
        if inp is None or inp.lower() == u'q':
            return None
        elif inp in (u'n', u''):
            # 'n'ext or return key
            echo(term.move_x(xpos) + term.clear_eol)
            if index == len(message_indices) - 1:
                # no more messages,
                return None
            return index + 1
        elif inp == u'p':
            # prev
            echo(term.move_x(xpos) + term.clear_eol)
            return index - 1
        elif inp == u'e':
            # TODO, edit tags
            pass
        elif inp == u'r':
            # TODO, reply
            pass
        elif inp not in opts:
            # not a valid input option, is it a valid integer? (even '-1'!)
            try:
                val = int(inp)
            except ValueError:
                # some garbage; try again
                term.inkey(0.15)
                continue
            try:
                # allow a message index, (even pythonic '-1' for 'last')
                if val > 0:
                    # 1-based indexing
                    val -= 1
                nxt_idx = message_indices[val]
                if nxt_idx != index:
                    echo(term.move_x(xpos) + term.clear_eol)
                    return nxt_idx
            except IndexError:
                # invalid index; try again
                term.inkey(0.15)
                continue


def read_messages(session, term, message_indices, colors):
    """ Read list of given messages. """
    index = 0
    while True:
        session.activity = ('reading msgs [{0}/{1}]'
                            .format(index + 1, len(message_indices)))
        display_message(session=session, term=term,
                        msg_index=message_indices[index],
                        colors=colors)
        index = do_reader_prompt(session=session, term=term, index=index,
                                 message_indices=message_indices,
                                 colors=colors)
        if index is None:
            break


def main(quick=False):
    """ Main procedure. """

    session, term = getsession(), getterminal()
    session.activity = 'checking for new messages'

    # set syncterm font, if any
    if term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    colors = dict(
        highlight=lambda txt: txt,
        lowlight=lambda txt: txt,
        backlight=lambda txt: txt,
        text=lambda txt: txt
    ) if not colored_menu_items else dict(
        highlight=getattr(term, color_highlight),
        lowlight=getattr(term, color_lowlight),
        backlight=getattr(term, color_backlight),
        text=getattr(term, color_text))

    yloc = top_margin = 0
    subscription = session.user.get('msg_subscription', [])
    dirty = 2

    while True:
        if dirty == 2:
            # display header art,
            yloc = display_banner(art_file, encoding=art_encoding, center=True)
            xloc = max(0, (term.width // 2) - 40)
            echo(u'\r\n')
            top_margin = yloc = (yloc + 1)

        elif dirty:
            echo(term.move(top_margin, 0) + term.normal + term.clear_eos)
            echo(term.move(top_margin, xloc))

        if dirty:

            if not subscription:
                # prompt the user for a tag subscription, and loop
                # back again when completed to re-draw and show new messages.
                subscription = session.user['msg_subscription'] = (
                    prompt_subscription(
                        session=session, term=term, yloc=top_margin,
                        subscription=subscription, colors=colors))
                continue

            messages, messages_bytags = get_messages_by_subscription(
                session, subscription)

            # When quick login ('y') selected in top.py, return immediately
            # when no new messages are matched any longer.
            if quick and not messages['new']:
                echo(term.move_x(xloc) + u'\r\nNo new messages.\r\n')
                return waitprompt(term)

            txt = describe_message_area(
                term=term, subscription=subscription,
                messages_bytags=messages_bytags, colors=colors)

            yloc = top_margin + show_description(
                term=term, description=txt, color=None,
                subsequent_indent=' ' * len('message area: '))

            echo(render_menu_entries(
                term=term, top_margin=yloc,
                menu_items=get_menu(messages),
                colors=colors, max_cols=2))
            echo(display_prompt(term=term, colors=colors))
            dirty = False

        event, data = session.read_events(('refresh', 'newmsg', 'input'))

        if event == 'refresh':
            # screen resized, redraw.
            dirty = 2
            continue

        elif event == 'newmsg':
            # When a new message is sent, 'newmsg' event is broadcasted.
            session.flush_event('newmsg')
            nxt_msgs, nxt_bytags = get_messages_by_subscription(
                session, subscription)
            if nxt_msgs['new'] - messages['new']:
                # beep and re-display when a new message has arrived.
                echo(u'\b')
                messages, messages_bytags = nxt_msgs, nxt_bytags
                dirty = True
                continue

        elif event == 'input':
            session.buffer_input(data, pushback=True)
            inp = term.inkey(0)
            if not inp.is_sequence:
                echo(inp)
            if inp.lower() == u'n' and messages['new']:
                # read new messages
                read_messages(session=session, term=term,
                              message_indices=list(messages['new']),
                              colors=colors)
                dirty = 2
            elif inp.lower() == u'a' and messages['all']:
                # read all messages
                read_messages(session=session, term=term,
                              message_indices=list(messages['all']),
                              colors=colors)
                dirty = 2
            elif inp.lower() == u'm' and messages['new']:
                do_mark_as_read(session, messages['new'])
                # mark all messages as read
                dirty = 1
            # elif inp.lower() == u'p':
            #     # write new public message
            #     dirty = 2
            # elif inp.lower() == u'w':
            #     # write new private message
            #     dirty = 2
            elif inp.lower() == u'c':
                # prompt for new subscription in next loop
                subscription = []
                dirty = 1
            elif inp.lower() == u'?':
                echo(term.move(yloc, 0) + term.clear_eos)
                describe_message_system(term, colors)
                waitprompt(term)
                dirty = 2
            elif inp.lower() == u'q':
                return
            elif not dirty:
                echo(u'\b \b')
