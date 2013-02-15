""" msg reader for x/84, https://github.com/jquast/x84 """


def banner():
    from x84.bbs import getterminal
    term = getterminal()
    return u''.join((u'\r\n\r\n',
        u'... MSG REAdER'.center(term.width),))

def main(tags=None):
    from x84.bbs import getsession, getterminal, echo, LineEditor, getch
    from x84.bbs import list_msgs, timeago, DBProxy, Ansi, get_msg, Lightbar
    from x84.bbs import ini, Pager
    import datetime
    session, term = getsession(), getterminal()
    echo(banner())
    if tags is None:
        tags = set('public')
        tags.update(session.user.groups)
    public_idx = list_msgs(tags)

    # this boolean allows sysop to remove filter using /nofilter
    filter_private = True

    tagdb = DBProxy('tags')
    while True:
        # Accept user input for a 'search tag', or /list command
        #
        echo(u"\r\n\r\nENtER SEARCh TAG(s), COMMA-dEliMitEd. ")
        echo(u"OR '/list'\r\n : ")
        sel_tags = ', '.join(tags)
        inp_tags = LineEditor(30, sel_tags).read()
        if inp_tags is None or 0 == len(inp_tags):
            break
        elif inp_tags.strip().lower() == '/list':
            # list all available tags, and number of messages
            echo(u'\r\n\r\nTags: \r\n')
            echo(Ansi(u', '.join(([u'%s(%d)' % (_key, len(_value),)
                for (_key, _value) in sorted(tagdb.items())]))
                ).wrap(term.width))
            continue
        elif (inp_tags.strip().lower() == '/nofilter'
                and 'sysop' in session.user.groups):
            # disable filtering private messages
            filter_private = False
            continue

        # search input as valid tag(s)
        tags = set([inp.strip().lower() for inp in inp_tags.split(',')])
        err = False
        for tag in tags[:]:
            if not tag in tagdb:
                tags.remove(tag)
                echo(u'\r\nTag %s not found.\r\n' % (tag,))
                err = True
        if err:
            # try again
            continue

        msgs_idx = list_msgs(tags)
        echo(u'\r\n\r\n%d messages.' % (len(msgs_idx),))
        if 0 == len(msgs_idx):
            continue

        echo(u' Processing ' + term.reverse_yellow('..'))
        # filter all matching messages, userland implementation
        # of private/public messaging by using the 'tags' database.
        # 'new', or unread messages are marked by idx matching
        # session.user['readmsgs']. Finally, 'group' tagging, so that
        # users of group 'impure' are allowed to read messages tagged
        # by 'impure', regardless of recipient or 'public'.
        addressed_to = 0
        addressed_grp = 0
        filtered = 0
        new = 0
        already_read = session.user.get('readmsgs', set())
        for msg_id in msgs_idx[:]:
            if not msg_id in public_idx:
                msg = get_msg(msg_id)
                if msg.recipient == session.user.handle:
                    addressed_to += 1
                else:
                    # a system of my own, by creating groups with the same
                    # as tagged messages, you create private or intra-group
                    # messages.
                    tag_matches_group = False
                    for tag in msg.tags:
                        if tag in session.user.groups():
                            tag_matches_group = True
                            break
                    if tag_matches_group:
                        addressed_grp += 1
                    else:
                        # denied to read this message
                        if filter_private:
                            msgs_idx.remove(msg_id)
                        filtered +=1
                        continue
                if msg_id not in already_read:
                    new += 1
                msg = get_msg(msg_id)
        if 0 == len(msgs_idx):
            echo(u'\r\n\r\nNo messages (%s filtered).' % (filtered,))
            continue


        echo(u'\r\n\r\n')
        echo(u', '.join((
            ('%s addressed to you' % (
                term.bold_yellow(str(addressed_to))
                if addressed_to else u'',)),
            ('%s addressed by group' % (
                term.bold_yellow(str(addressed_grp))
                if addressed_grp else u'',)),
            ('%s filtered' % (
                term.bold_yellow(str(filtered))
                if filtered else u'',)),
            ('%s new' % (term.bold_yellow(str(new,))
                if new else u'',)),
            )))
        echo(u'  REAd [%s]ll %d messages %s [a%s] ?\b\b' % (
                term.yellow_underline(u'a'), len(msgs_idx),
                (u'or ONlY %d [%s]EW ' % (
                    new, term.yellow_underline(u'n'),) if new else u''),
                u'n' if new else u'',))
        while True:
            inp = getch()
            if inp is None or inp in (u'q', u'Q', unichr(27)):
                return
            elif inp in (u'n', u'N') and new:
                msgs_idx = [idx for idx in msgs_idx if not already_read]
                break
            elif inp in (u'a', u'A'):
                break
        echo(u'\r\n' * term.height)
        msg_selector = Lightbar(
            height=int(term.height * .2),
            width=min(term.width, 130),
            yloc=0,
            xloc=0)
        msg_reader = Pager(
            height=int(term.height * .8),
            width=min(term.width, 130),
            yloc=term.height - int(term.height * .8),
            xloc=0)

        # build header
        len_author = ini.CFG.getint('nua', 'max_user')
        len_subject = ini.CFG.getint('msg', 'max_subject')
        header = list()
        for idx in msgs_idx:
            msg = get_msg(idx)
            author, subj = msg.author, msg.subject
            tm_ago = (datetime.datetime.now() - msg.stime).total_seconds()
            header.append((idx, u'%s %s %s' % (
                author.rjust(len_author),
                timeago(tm_ago).rjust(5),
                subj.ljust(len_subject),)))
        echo(u'\r\n'.join([u': '.join(h) for h in header]))
        echo(u'\r\n\r\n')
        getch()
        return
