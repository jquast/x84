""" msg reader for x/84, https://github.com/jquast/x84 """
# this boolean allows sysop to remove filter using /nofilter
FILTER_PRIVATE = True
ALREADY_READ = set()
READING = False # set true when keystrokes are sent to msg_reader
SEARCH_TAGS = None

def mark_read(idx):
    from x84.bbs import getsession
    session = getsession()
    global ALREADY_READ
    ALREADY_READ = session.user['readmsgs']
    marked = idx not in ALREADY_READ
    ALREADY_READ.add(idx)
    session.user['readmsgs'] = ALREADY_READ
    return marked

def msg_filter(msgs):
    """
        filter all matching messages. userland implementation
        of private/public messaging by using the 'tags' database.
        'new', or unread messages are marked by idx matching
        session.user['readmsgs']. Finally, 'group' tagging, so that
        users of group 'impure' are allowed to read messages tagged
        by 'impure', regardless of recipient or 'public'.

        returns (msgs), (new). new contains redundant msgs
    """
    from x84.bbs import list_msgs, echo, getsession, getterminal, get_msg, Ansi
    session, term = getsession(), getterminal()
    public_msgs = list_msgs()
    addressed_to = 0
    addressed_grp = 0
    filtered = 0
    private = 0
    public = 0
    new = set()
    echo(u' Processing ' + term.reverse_yellow('..'))
    for msg_id in msgs.copy():
        if msg_id in public_msgs:
            # can always ready msgs tagged with 'public'
            public += 1
        else:
            private += 1
        msg = get_msg(msg_id)
        if msg.recipient == session.user.handle:
            addressed_to += 1
        else:
            # a system of my own, by creating groups
            # with the same as tagged messages, you may
            # create private or intra-group messages.
            tag_matches_group = False
            for tag in msg.tags:
                if tag in session.user.groups:
                    tag_matches_group = True
                    break
            if tag_matches_group:
                addressed_grp += 1
            elif msg_id not in public_msgs:
                # denied to read this message
                if FILTER_PRIVATE:
                    msgs.remove(msg_id)
                    filtered +=1
                    continue
        if msg_id not in ALREADY_READ:
            new.add(msg_id)

    if 0 == len(msgs):
        echo(u'\r\n\r\nNo messages (%s filtered).' % (filtered,))
    else:
        txt_out = list()
        if addressed_to > 0:
            txt_out.append ('%s addressed to you' % (
                term.bold_yellow(str(addressed_to)),))
        if addressed_grp > 0:
            txt_out.append ('%s addressed by group' % (
                term.bold_yellow(str(addressed_grp)),))
        if filtered > 0:
            txt_out.append ('%s filtered' % (
                term.bold_yellow(str(filtered)),))
        if public > 0:
            txt_out.append ('%s public' % (
                term.bold_yellow(str(public)),))
        if private > 0:
            txt_out.append ('%s private' % (
                term.bold_yellow(str(private)),))
        if len(new) > 0:
            txt_out.append ('%s new' % (
                term.bold_yellow(str(len(new),)),))
        if 0 != len(txt_out):
            echo(u'\r\n\r\n' + Ansi(
                u', '.join(txt_out) + u'.').wrap(term.width - 2))
    return msgs, new

def banner():
    from x84.bbs import getterminal
    term = getterminal()
    return u''.join((u'\r\n\r\n',
        term.yellow(u'... '.center(term.width).rstrip()),
        term.bold_yellow(' MSG R'),
        term.yellow('EAdER'),))

def prompt_tags(tags):
    from x84.bbs import DBProxy, echo, getterminal, getsession, Ansi, LineEditor
    session, term = getsession(), getterminal()
    tagdb = DBProxy('tags')
    global FILTER_PRIVATE
    while True:
        # Accept user input for a 'search tag', or /list command
        #
        echo(u"\r\n\r\nENtER SEARCh %s, COMMA-dEliMitEd. " % (
            term.bold_red('TAG(s)'),))
        echo(u"OR '/list', %s:quit\r\n : " % (
            term.yellow_underline('Escape'),))
        width = term.width - 6
        sel_tags = u', '.join(tags)
        while len(Ansi(sel_tags)) >= (width - 8):
            tags = tags[:-1]
            sel_tags = u', '.join(tags)
        inp_tags = LineEditor(width, sel_tags).read()
        if (inp_tags is None or 0 == len(inp_tags)
                or inp_tags.strip().lower() == '/quit'):
            return None
        elif inp_tags.strip().lower() == '/list':
            # list all available tags, and number of messages
            echo(u'\r\n\r\nTags: \r\n')
            all_tags = sorted(tagdb.items())
            if 0 == len(all_tags):
                echo(u'None !'.center(term.width / 2))
            else:
                echo(Ansi(u', '.join(([u'%s(%d)' % (_key, len(_value),)
                    for (_key, _value) in all_tags]))
                    ).wrap(term.width - 2))
            continue
        elif (inp_tags.strip().lower() == '/nofilter'
                and 'sysop' in session.user.groups):
            # disable filtering private messages
            FILTER_PRIVATE = False
            continue

        echo(u'\r\n')
        # search input as valid tag(s)
        tags = set([inp.strip().lower() for inp in inp_tags.split(',')])
        for tag in tags.copy():
            if not tag in tagdb:
                tags.remove(tag)
                echo(u"\r\nNO MESSAGES With tAG '%s' fOUNd." % (
                    term.red(tag),))
        return tags


def main(tags=None):
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import list_msgs
    session, term = getsession(), getterminal()
    echo(banner())
    global ALREADY_READ
    global SEARCH_TAGS
    if tags is None:
        tags = set(['public'])
        # also throw in user groups
        tags.update(session.user.groups)

    while True:
        # prompt user for tags
        SEARCH_TAGS = prompt_tags(tags)
        if SEARCH_TAGS is None or 0 == len(SEARCH_TAGS):
            break

        # retrieve all matching messages,
        all_msgs = list_msgs(SEARCH_TAGS)
        echo(u'\r\n\r\n%d messages.' % (len(all_msgs),))
        if 0 == len(all_msgs):
            break

        # filter messages public/private/group-tag/new
        ALREADY_READ = session.user.get('readmsgs', None)
        if ALREADY_READ is None:
            session.user['readmsgs'] = set()
            ALREADY_READ = session.user['readmsgs']
        msgs, new = msg_filter(all_msgs)
        if 0 == len(msgs) and 0 == len(new):
            break

        # prompt read 'a'll, 'n'ew, or 'q'uit
        echo(u'\r\n  REAd [%s]ll %d%s message%s [qa%s] ?\b\b' % (
                term.yellow_underline(u'a'),
                len(msgs), (
                    u' or %d [%s]EW\a ' % (
                        len(new), term.yellow_underline(u'n'),)
                    if new else u''),
                u's' if 1 != len(msgs) else u'',
                u'n' if new else u'',))
        while True:
            inp = getch()
            if inp in (u'q', 'Q', unichr(27)):
                return
            elif inp in (u'n', u'N') and len(new):
                # read only new messages
                msgs = new
                break
            elif inp in (u'a', u'A'):
                break

        # read target messages
        read_messages(msgs, new)


def read_messages(msgs, new):
    from x84.bbs import timeago, get_msg, getterminal, echo
    from x84.bbs import ini, Pager, getsession, getch, Ansi
    session, term = getsession(), getterminal()

    # build header
    len_idx = max([len('%d' % (_idx,)) for _idx in msgs])
    len_author = ini.CFG.getint('nua', 'max_user')
    len_ago = 9
    len_subject = ini.CFG.getint('msg', 'max_subject')
    len_preview = len_idx + len_author + len_ago + len_subject + 4

    def get_header(msgs_idx):
        import datetime
        msg_list = list()
        for idx in msgs_idx:
            msg = get_msg(idx)
            author, subj = msg.author, msg.subject
            tm_ago = (datetime.datetime.now() - msg.stime).total_seconds()
            msg_list.append((idx, u'%s %s %s %s: %s' % (
                u'U' if not idx in ALREADY_READ else u' ',
                str(idx).rjust(len_idx),
                author.ljust(len_author),
                (timeago(tm_ago) + ' ago').rjust(len_ago),
                subj[:len_subject],)))
        msg_list.sort()
        return msg_list

    def get_selector(msgs_idx, prev_sel=None):
        from x84.bbs import Lightbar
        pos = prev_sel.position if prev_sel is not None else (0, 0)
        sel = Lightbar(
            height=(term.height / 3
                if term.width < 140 else term.height - 2),
            width=len_preview,
            yloc=2, xloc=0)
        sel.glyphs['top-horiz'] = u''
        sel.glyphs['left-vert'] = u''
        sel.colors['highlight'] = term.yellow_reverse
        sel.update(msgs_idx)
        sel.position = pos
        return sel

    def get_reader():
        reader_height = (term.height - (term.height / 3) - 2)
        reader_indent = 5
        reader_width = min(term.width - 1, min(term.width - reader_indent, 80))
        reader_ypos = (term.height - reader_height if
                (term.width - reader_width) < len_preview else 2)
        reader_height = term.height - reader_ypos
        msg_reader = Pager(
            height=reader_height,
            width=reader_width,
            yloc=reader_ypos,
            xloc=min(len_preview + 2, term.width - reader_width))
        msg_reader.glyphs['top-horiz'] = u''
        msg_reader.glyphs['right-vert'] = u''
        return msg_reader

    def format_msg(reader, idx):
        msg = get_msg(idx)
        sent = msg.stime.strftime('%A %b-%d %Y %H:%M:%S')
        return u'\r\n'.join((
            (u''.join((
                (u'%s' % (msg.author,)).rjust(len_author),
                u' ' * (reader.visible_width - len_author - len(sent)),
                sent,))),
            (Ansi(
                term.yellow('tAGS: ')
                + (u'%s ' % (term.bold(','),)).join((
                    [term.bold_red(_tag)
                        if _tag in SEARCH_TAGS
                        else term.yellow(_tag)
                        for _tag in msg.tags]))).wrap(
                            reader.visible_width,
                            indent=u'      ')),
            (term.yellow_underline(
                (u'SUbj: %s' % (msg.subject,)).ljust(reader.visible_width)
                )),
            u'', (msg.body),))


    def get_selector_footer(mbox, new):
        newmsg = (term.yellow(u' ]-[ ') +
                term.yellow_reverse(str(len(new))) +
                term.bold_underline(u' NEW')) if len(new) else u''
        return u''.join((term.yellow(u'[ '),
                term.bold_yellow(str(len(mbox))),
                term.bold(u' MSG%s' % (u's' if 1 != len(mbox) else u'',)),
                newmsg, term.yellow(u' ]'),))

    def get_selector_title():
        return u''.join((
            term.yellow(u'- '),
            u' '.join((
                term.yellow_underline(u'>') + u':read',
                term.yellow_underline(u'up')
                + u'/' + term.yellow_underline(u'down')
                + u'/' + term.yellow_underline(u'spacebar'),
                term.yellow_underline(u'q') + u':Uit',)),
            term.yellow(u' -'),))

    def get_reader_footer():
        return u''.join((
            term.yellow(u'- '),
            u' '.join((
                term.yellow_underline(u'<') + u':back',
                term.yellow_underline(u'r') + u':EPlY',
                term.yellow_underline(u'+-') + u':tAG',
                term.yellow_underline(u'q') + u':Uit',)),
            term.yellow(u' -'),))

    def refresh(reader, selector, mbox, new):
        if READING:
            reader.colors['border'] = term.bold_yellow
            selector.colors['border'] = term.bold_black
        else:
            reader.colors['border'] = term.bold_black
            selector.colors['border'] = term.bold_yellow
        title = get_selector_footer(mbox, new)
        padd_attr = term.bold_yellow if not READING else term.bold_black
        sel_padd_right = padd_attr(
                u'-'
                + selector.glyphs['bot-horiz'] * (
                    selector.visible_width - len(Ansi(title)) - 7)
                + u'-\u25a0-')
        sel_padd_left = padd_attr(
                selector.glyphs['bot-horiz'] * 3)
        return u''.join((term.move(0, 0), term.clear, u'\r\n',
            u'// REAdiNG MSGS ..'.center(term.width).rstrip(),
            selector.refresh(),
            reader.border(),
            selector.border(),
            selector.title(sel_padd_left + title + sel_padd_right),
            selector.footer(get_selector_title()) if not READING else u'',
            reader.footer(get_reader_footer()) if READING else u'',
            reader.refresh(),
            ))

    echo ((u'\r\n' + term.clear_eol) * (term.height - 1))
    dirty = 2
    msg_selector = None
    msg_reader = None
    idx = None
    global READING
    while (msg_selector is None and msg_reader is None
            ) or not (msg_selector.quit or msg_reader.quit):
        if session.poll_event('refresh'):
            dirty = dirty or 1
        if dirty:
            if dirty == 2:
                mailbox = get_header(msgs)
            msg_selector = get_selector(mailbox, msg_selector)
            idx = msg_selector.selection[0]
            msg_reader = get_reader()
            msg_reader.update(format_msg(msg_reader, idx))
            echo(refresh(msg_reader, msg_selector, msgs, new))
            dirty = 0
        inp = getch(1)
        if READING:
            echo(msg_reader.process_keystroke(inp))
            # left, <, or backspace moves UI
            if inp in (term.KEY_LEFT, u'<', u'h',
                    '\b', term.KEY_BACKSPACE):
                READING = False
                dirty = 1
        else:
            echo(msg_selector.process_keystroke(inp))
            idx = msg_selector.selection[0]
            # spacebar marks as read, goes to next message
            if inp in (u' ',):
                dirty = 2 if mark_read(idx) else 1
                msg_selector.move_down()
                idx = msg_selector.selection[0]
            # right, >, or enter marks message read, moves UI
            if inp in (u'\r', term.KEY_ENTER, u'>',
                    u'l', 'L', term.KEY_RIGHT):
                dirty = 2 if mark_read(idx) else 1
                READING = True
            elif msg_selector.moved:
                dirty = 1
    echo(term.move(term.height, 0) + u'\r\n')
    return
