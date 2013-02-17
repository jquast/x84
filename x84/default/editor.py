"""
editor script for X/84, https://github.com/jquast/x84
"""
# This is probably the fourth or more ansi multi-line editor
# I've written for python. I did the least-effort this time.
# There isn't any actual multi-line editor, just this script
# that drives a LineEditor and a Lightbar.


def get_lbcontent(lightbar):
    from x84.bbs import Ansi
    # a custom 'soft newline' versus 'hard newline' is implemented,
    # '\n' == 'soft', '\r\n' == 'hard'
    lines = list()
    for lno, (key, ucs) in enumerate(lightbar.content):
        if lno == 0 or (
                lines[-1][-2:] == u'\r\n' or
                lines[-1][-1:] != u'\n'):
            lines.append(ucs)
        else:
            lines[-1] = lines[-1].rstrip() + ucs
    for lno, ucs in enumerate(lines):
        wrapped = u'\n'.join(Ansi(ucs)
                .wrap(lightbar.visible_width).splitlines())
        lines[lno] = wrapped
    return u'\r\n'.join(lines)


def set_lbcontent(lightbar, ucs):
    from x84.bbs import Ansi
    # a custom 'soft newline' versus 'hard newline' is implemented,
    # '\n' == 'soft', '\r\n' == 'hard'
    lines = list()
    while ucs.startswith(u'\r\n'):
        lines.append(u'')
        ucs = ucs[len(u'\r\n'):]
    lines.extend(ucs.split(u'\r\n'))
    #while ucs.endswith(u'\r\n'):
    #    lines.append(u'')
    #    ucs = ucs[:-len(u'\r\n')]
    width = lightbar.visible_width
    content = list()
    row = 0
    for lno, line in enumerate(lines):
        joined = u' '.join(line.split('\n'))
        wrapped = Ansi(joined).wrap(width).splitlines()
        for linewrap in wrapped:
            content.append((row, linewrap))
            row += 1
        if 0 == len(wrapped):
            content.append((row, u''))
            row += 1
    if 0 == len(content):
        content.append((0, u''))
    lightbar.update(content)


def yes_no(lightbar, msg, prompt_msg='are you sure?'):
    from x84.bbs import Selector, echo, getch, getterminal
    term = getterminal()
    keyset = {
        'yes': (u'y', u'Y'),
        'no': (u'n', u'N'),
    }
    echo(u''.join((
        lightbar.border(),
        lightbar.pos(lightbar.height, lightbar.xpadding),
        msg, u' ', prompt_msg,)))
    yn = Selector(yloc=lightbar.yloc + lightbar.height - 1,
                  xloc=term.width - 28, width=12,
                  left='Yes', right='No')
    yn.colors['selected'] = term.reverse_red
    yn.keyset['left'].extend(keyset['yes'])
    yn.keyset['right'].extend(keyset['no'])
    echo(yn.refresh())
    while True:
        inp = getch()
        echo(yn.process_keystroke(inp))
        if((yn.selected and yn.selection == yn.left)
                or inp in keyset['yes']):
            # selected 'yes',
            return True
        elif((yn.selected or yn.quit)
                or inp in keyset['no']):
            # selected 'no'
            return False

def get_lightbar(ucs):
    from x84.bbs import getterminal, Lightbar
    term = getterminal()
    width = min(80, max(term.width, 40))
    yloc = 0
    height = term.height - yloc
    xloc = max(0, (term.width / 2) - (width / 2))
    lightbar = Lightbar(height, width, yloc, xloc)
    lightbar.glyphs['left-vert'] = lightbar.glyphs['right-vert'] = u''
    lightbar.colors['highlight'] = term.yellow_reverse
    set_lbcontent(lightbar, ucs)
    return lightbar

def get_lneditor(lightbar):
    from x84.bbs import getterminal, ScrollingEditor
    term = getterminal()
    width = min(80, max(term.width, 40))
    yloc = (lightbar.yloc + lightbar.ypadding + lightbar.position[0] - 1)
    xloc = max(0, (term.width / 2) - (width / 2))
    lneditor = ScrollingEditor(width, yloc, xloc)
    lneditor.enable_scrolling = True
    lneditor.max_length = 65534
    lneditor.glyphs['bot-horiz'] = u''
    lneditor.glyphs['top-horiz'] = u''
    lneditor.colors['highlight'] = term.red_reverse
    lneditor.colors['border'] = term.bold_red
    (key, ucs) = lightbar.selection
    lneditor.update(ucs)
    return lneditor


def main(save_key=u'draft'):
    from x84.bbs import getsession, getterminal, echo, getch
    session, term = getsession(), getterminal()

    movement = (term.KEY_UP, term.KEY_DOWN, term.KEY_NPAGE,
                term.KEY_PPAGE, term.KEY_HOME, term.KEY_END,
                u'\r', term.KEY_ENTER)
    keyset = {'edit': (term.KEY_ENTER,),
              'command': (unichr(27), term.KEY_ESCAPE),
              'kill': (u'K',),
              'join': (u'J',),
            }

    def merge():
        """
        Merges line editor content as a replacement for the currently
        selected lightbar row. Returns True if text inserted caused
        additional rows to be appended, which is meaningful in a window
        refresh context.
        """
        # merge line editor with pager window content
        swp = lightbar.selection
        lightbar.content[lightbar.index] = (swp[0], lneditor.content)
        set_lbcontent(lightbar, get_lbcontent(lightbar))
        return True
        prior_length = len(lightbar.content)
        prior_position = lightbar.position
        if len(lightbar.content) - prior_length == 0:
            echo(lightbar.refresh_row(prior_position[0]))
            return False
        #    print 'eq'
        #print 'go', len(lightbar.content) - prior_length
        while len(lightbar.content) - prior_length > 0:
            # hidden move-down for each appended line
            lightbar.move_down()
            prior_length += 1
        #    print 'down'

    def statusline(lightbar):
        lightbar.colors['border'] = term.red if edit else term.yellow
        return u''.join((
            lightbar.border(),
            lightbar.pos(lightbar.height, lightbar.xpadding),
            (u'-[ EditiNG liNE %d ]-' % (lightbar.index + 1,) if edit else
                u'- liNE %d/%d %d%% -' % (
                    lightbar.index + 1,
                    len(lightbar.content), int((float(lightbar.index + 1)
                      / max(1, len(lightbar.content))) * 100))),
            lightbar.pos(0, lightbar.xpadding),
            lightbar.title(u''.join((
                    term.red('-[ '),
                    term.red_underline(u'Escape'),
                    u':', term.red(u'command mode'),
                    term.red(' ]-'),)
                    ) if edit else u''.join((
                        term.yellow('-[ '),
                        term.yellow_underline(u'Enter'),
                        u':', term.bold(u'edit mode'), u' ',
                        term.yellow_underline(u'K'),
                        u':', term.bold(u'ill'), u' ',
                        term.yellow_underline(u'J'),
                        u':', term.bold(u'oin'), u' ',
                        term.yellow_underline(u'S'),
                        u':', term.bold(u'ave'), u' ',
                        term.yellow_underline(u'A'),
                        u':', term.bold(u'bort'),
                        term.yellow(' ]-'),))),))


    def redraw_lneditor(lightbar, lneditor):
        return ''.join((
            term.normal,
            statusline(lightbar),
            lneditor.border(),
            lneditor.refresh()))


    def get_ui(ucs, lightbar=None):
        lb = get_lightbar(ucs)
        lb.position = lightbar.position if lightbar is not None else (0, 0)
        le = get_lneditor(lb)
        return lb, le

    def banner():
        return u''.join((
            term.move(0, 0),
            term.normal,
            term.clear))

    def redraw(lightbar, lneditor):
        return u''.join((
            term.normal,
            redraw_lightbar(lightbar),
            redraw_lneditor(lightbar, lneditor) if edit else u'',
            ))

    def redraw_lightbar(lightbar):
        return u''.join((
            statusline(lightbar),
            lightbar.refresh(),))

    def resize(lightbar):
        if edit:
            # always re-merge current line on resize,
            merge()
        lb, le = get_ui(get_lbcontent(lightbar), lightbar)
        echo(redraw(lb, le))
        return lb, le

    ucs = session.user.get(save_key, u'')
    lightbar, lneditor = get_ui(ucs, None)
    echo(banner())
    dirty = True
    edit = False
    while True:
        # poll for refresh
        if session.poll_event('refresh'):
            echo(banner())
            lightbar, lneditor = resize(lightbar)
            dirty = True
        if dirty:
            session.activity = 'editing %s' % (save_key,)
            echo(redraw(lightbar, lneditor))
            dirty = False
        # poll for input
        inp = getch(1)

        # toggle edit mode,
        if inp in keyset['command'] or not edit and inp in keyset['edit']:
            edit = not edit  # toggle
            if not edit:
                # switched to command mode, merge our lines
                echo(term.normal + lneditor.erase_border())
                merge()
            else:
                # switched to edit mode, instantiate new line editor
                lneditor = get_lneditor(lightbar)
            dirty = True

        # edit mode, kill line
        elif not edit and inp in keyset['kill']:
            # when 'killing' a line, make accomidations to clear
            # bottom-most row, otherwise a ghosting effect occurs
            print lightbar.content, lightbar.index
            del lightbar.content[lightbar.index]
            set_lbcontent(lightbar, get_lbcontent(lightbar))
            if lightbar.visible_bottom > len(lightbar.content):
                echo(lightbar.refresh_row(lightbar.visible_bottom + 1))
            else:
                dirty = True

        # edit mode, join line
        elif (not edit and inp in keyset['join']
                and lightbar.index + 1 < len(lightbar.content)):
            idx = lightbar.index
            lightbar.content[idx] = (idx,
                    ' '.join((
                        lightbar.content[idx][1],
                        lightbar.content[idx + 1][1],)))
            del lightbar.content[idx + 1]
            set_lbcontent(lightbar, get_lbcontent(lightbar))
            dirty = True


        # command mode, basic cmds & movement
        elif not edit and inp is not None:
            if inp in (u'a', u'A'):
                if yes_no(lightbar, u'- AbORt -'):
                    return False
                dirty = True
            elif inp in (u's', u'S'):
                if yes_no(lightbar, u'- SAVE -'):
                    session.user[save_key] = get_lbcontent(lightbar)
                    return True
                dirty = True
            else:
                echo(lightbar.process_keystroke(inp))

        # edit mode
        elif edit and inp in movement:
            dirty = merge()
            if inp in (u'\r', term.KEY_ENTER):
                if lightbar.at_bottom:
                    idx = max([_key for (_key, _ucs) in lightbar.content])
                    lightbar.content.append((idx + 1, u''))
                inp = term.KEY_DOWN
            lightbar.process_keystroke(inp)
            if lightbar.moved:
                echo(term.normal + lneditor.erase_border())
                # erase old line editor border and instatiate another
                if (lightbar._vitem_lastshift != lightbar.vitem_shift):
                    dirty = True
                else:
                    # just redraw row of last selection
                    echo(lightbar.refresh_row(lightbar._vitem_lastidx))
                lneditor = get_lneditor(lightbar)
                if not dirty:
                    echo(redraw_lneditor(lightbar, lneditor))

        # edit mode -- append character / backspace
        elif edit and inp is not None:
            # edit mode, addch
            echo(lneditor.process_keystroke(inp))
            if lneditor.moved:
                echo(statusline(lightbar))
