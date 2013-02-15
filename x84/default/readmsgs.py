""" msg reader for x/84, https://github.com/jquast/x84 """
# this boolean allows sysop to remove filter using /nofilter
FILTER_PRIVATE = True

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
    already_read = session.user.get('readmsgs', set())
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
        if msg_id not in already_read:
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
            txt_out.append ('%s private' % (
                term.bold_yellow(str(filtered)),))
        if private > 0:
            txt_out.append ('%s private' % (
                term.bold_yellow(str(filtered)),))
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
        u'... MSG REAdER'.center(term.width),))

def get_tags(tags):
    from x84.bbs import DBProxy, echo, getterminal, getsession, Ansi, LineEditor
    session, term = getsession(), getterminal()
    tagdb = DBProxy('tags')
    global FILTER_PRIVATE
    while True:
        # Accept user input for a 'search tag', or /list command
        #
        echo(u"\r\n\r\nENtER SEARCh TAG(s), COMMA-dEliMitEd. ")
        echo(u"OR '/list'\r\n : ")
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

        # search input as valid tag(s)
        tags = set([inp.strip().lower() for inp in inp_tags.split(',')])
        for tag in tags.copy():
            if not tag in tagdb:
                tags.remove(tag)
                echo(u"\r\nNO MESSAGES With tAG '%s' fOUNd." % (
                    tag,))
        return tags


def main(tags=None):
    from x84.bbs import getsession, getterminal, echo, getch
    from x84.bbs import list_msgs, timeago, Lightbar
    session, term = getsession(), getterminal()
    echo(banner())
    if tags is None:
        tags = set(['public'])
        # also throw in user groups
        tags.update(session.user.groups)

    while True:
        # fetch all messages by tag,
        all_msgs = list_msgs(get_tags(tags))
        echo(u'\r\n\r\n%d messages.' % (len(all_msgs),))
        if 0 == len(all_msgs):
            break

        # filter messages public/private/group-tag
        msgs, new = msg_filter(all_msgs)
        if 0 == len(msgs) and 0 == len(new):
            break

        # prompt 'a'll, 'n'ew, or 'q'uit
        echo(u'\r\n  REAd [%s]ll %d%s messages [qa%s] ?\b\b' % (
                term.yellow_underline(u'a'),
                len(msgs), (
                    u' or %d [%s]EW\a ' % (
                        new, term.yellow_underline(u'n'),)
                    if new else u''),
                u'n' if new else u'',))
        while True:
            inp = getch(5)
            if inp in (u'q', 'Q', unichr(27)):
                return
            elif inp in (u'n', u'N') and len(new):
                read_messages(new)
            elif inp in (u'a', u'A'):
                read_messages(msgs)

def read_messages(msgs):
    from x84.bbs import timeago, get_msg, Lightbar, getterminal, echo
    from x84.bbs import ini, Pager
    term = getterminal()
    import datetime

    # build header
    len_idx = max([len('%d' % (_idx,)) for _idx in msgs])
    len_author = ini.CFG.getint('nua', 'max_user')
    len_subject = ini.CFG.getint('msg', 'max_subject')
    len_ago = 6
    len_preview = len(u'%s %s: %s' % (
            u''.ljust(len_author),
            u''.rjust(len_ago),
            u''.ljust(len_subject),))
    msgs = list()
    for idx in msgs:
        msg = get_msg(idx)
        author, subj = msg.author, msg.subject
        tm_ago = (datetime.datetime.now() - msg.stime).total_seconds()
        msgs.append((idx, u'%s %s: %s' % (
            author.ljust(len_author),
            timeago(tm_ago).rjust(len_ago),
            subj[:len_subject],)))
    msgs.sort()

    # going for robocop look ? this matches the style of my wyse
    # 320 amber brown ..
    echo(u'\r\n' + u'// REAdiNG MSGS ..'.center(term.width).rstrip())
    echo(u'\r\n' * (term.height - 1))
    msg_selector = Lightbar(
        height=term.height / 3,
        width=len_preview,
        yloc=2, xloc=1)
    msg_selector.colors['border'] = term.bold_yellow
    msg_selector.glyphs['top-horiz'] = u''
    msg_selector.glyphs['left-vert'] = u''
    msg_selector.colors['highlight'] = term.yellow_reverse
    already_read = session.user.get('readmsgs', set())
    msg_selector.update([(_idx, u'%s %*d %s' % (
        u'U' if not _idx in already_read else u' ',
        len_idx, _idx, _txt,)) for (_idx, _txt) in msgs])
    echo(msg_selector.refresh())
    reader_height = (term.height - msg_selector.height - 2)
    reader_indent = (msg_selector.xloc + 4)
    reader_width = min(term.width - 1, min(term.width - reader_indent, 80))
    msg_reader = Pager(
        height=reader_height,
        width=reader_width,
        yloc=term.height - reader_height,
        xloc=term.width - reader_width)
    msg_reader.colors['border'] = term.yellow
#        msg_reader.glyphs['left-vert'] = u''
#        msg_reader.glyphs['top-horiz'] = u' - '
#        msg_reader.glyphs['right-vert'] = u'|'
#        msg_reader.glyphs['bot-horiz'] = u'-'
    key, asc = msg_selector.selection
    echo(msg_reader.border() + msg_selector.border())
    if key is not None:
        echo(msg_reader.update(get_msg(key).body))
    echo(msg_selector.title(u'- %d MESSAGE%s%s -' % (
        len(msgs), term.bold('s') if 1 != len(msgs) else u'',
        (u', ' + term.bold(u'%d NEW' % (new,))) if new else u'',)))
    getch()
    echo(term.move(term.height, 0))
    return

def read_messages(msgs):
    pass
