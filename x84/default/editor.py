""" Editor script for x/84 """
# std
import os

# local
from x84.bbs import getsession, getterminal, encode_pipe, echo
from x84.bbs import Lightbar, Selector, ScrollingEditor, showart
from x84.bbs import syncterm_setfont

# This is probably the fourth or more ansi multi-line editor
# I've written for python. I did the least-effort this time.
# There isn't any actual multi-line editor, just this script
# that drives a LineEditor and a Lightbar.

# TODO: use a timer to save the draft -- every 60 seconds or
# so, instead of on every line change.  This should
# significantly improve performance, especially on Raspberry Pi.

WHITESPACE = u' '
SOFTWRAP = u'\n'
HARDWRAP = u'\r\n'
UNDO = list()
UNDOLEVELS = 9

here = os.path.dirname(__file__)

#: preferred fontset for SyncTerm emulator
syncterm_font = 'cp437'


def save_draft(key, ucs):
    """ Persist draft to database and stack changes to UNDO buffer. """
    if key is not None:
        save(key, ucs)

    # pylint: disable=W0602
    #         Using global for 'UNDO' but no assignment is done
    global UNDO
    UNDO.append(ucs)
    if len(UNDO) > UNDOLEVELS:
        del UNDO[0]


def get_contents(lightbar):
    """ Return well-formatted document given the lightbar. """
    return HARDWRAP.join([softwrap_join(_ucs)
                          for _ucs in get_lbcontent(lightbar).split(HARDWRAP)])


def save(key, content):
    """ Persist message to user attrs database. """
    getsession().user[key] = content


def show_help(term):
    """ Returns help text. """
    # clear screen
    echo(term.normal + ('\r\n' * (term.height + 1)) + term.home)

    map(echo, showart(os.path.join(here, 'art', 'po-help.ans')))


def wrap_rstrip(value):
    r""" Remove hardwrap ``u'\r\n'`` and softwrap ``u'\n'`` from value """
    if value[-len(HARDWRAP):] == HARDWRAP:
        value = value[:-len(HARDWRAP)]
    if value[-len(SOFTWRAP):] == SOFTWRAP:
        value = value[:-len(SOFTWRAP)]
    return value


def softwrap_join(value):
    r""" Return whitespace-joined string from value split by softwrap ``'\n'``. """
    return WHITESPACE.join(value.split(SOFTWRAP))


def is_hardwrapped(ucs):
    r""" Returns true if string is hardwrapped with ``'\r\n'``. """
    return ucs[-(len(HARDWRAP)):] == HARDWRAP


def is_softwrapped(ucs):
    r""" Returns true if string is softwrapped with ``'\n'``. """
    return ucs[-(len(SOFTWRAP)):] == SOFTWRAP


def get_lbcontent(lightbar):
    """ Returns ucs string for content of Lightbar instance, ``lightbar``. """
    # a custom 'soft newline' versus 'hard newline' is implemented,
    # '\n' == 'soft', '\r\n' == 'hard'
    lines = list()
    for lno, (_, ucs) in enumerate(lightbar.content):
        # first line always appends as-is, otherwise if the previous line
        # matched a hardwrap, or did not match softwrap, then append as-is.
        # (a simple .endswith() can't wll work with a scheme of '\n' vs.
        # '\r\n')
        if lno == 0 or (
                is_hardwrapped(lines[-1]) or not is_softwrapped(lines[-1])):
            lines.append(ucs)
        else:
            # otherwise the most recently appended line must end with
            # SOFTWRAP, strip that softwrap and re-assign value to a
            # whitespace-joined value by current line value.
            lines[-1] = WHITESPACE.join((lines[-1].rstrip(), ucs.lstrip(),))
    retval = encode_pipe(u''.join(lines))
    return retval


def set_lbcontent(lightbar, ucs):
    """ Sets content for given Unicode string, ``ucs``. """
    # a custom 'soft newline' versus 'hard newline' is implemented,
    # '\n' == 'soft', '\r\n' == 'hard'
    term = getterminal()
    content = dict()
    lno = 0
    lines = ucs.split(HARDWRAP)
    for idx, ucs_line in enumerate(lines):
        if idx == len(lines) - 1 and 0 == len(ucs_line):
            continue
        ucs_joined = WHITESPACE.join(ucs_line.split(SOFTWRAP))
        ucs_wrapped = term.wrap(text=ucs_joined, width=lightbar.visible_width)
        for inner_lno, inner_line in enumerate(ucs_wrapped):
            softwrap = SOFTWRAP if inner_lno != len(ucs_wrapped) - 1 else u''
            content[lno] = u''.join((inner_line, softwrap))
            lno += 1
        if 0 == len(ucs_wrapped):
            content[lno] = HARDWRAP
            lno += 1
        else:
            content[lno - 1] += HARDWRAP
    if 0 == len(content):
        content[0] = HARDWRAP
    lightbar.update(sorted(content.items()))


def yes_no(lightbar, msg, prompt_msg='are you sure? ', attr=None):
    """ Prompt user for yes/no, returns True for yes, False for no. """
    term = getterminal()
    keyset = {
        'yes': (u'y', u'Y'),
        'no': (u'n', u'N'),
    }
    echo(u''.join((
        lightbar.border(),
        lightbar.pos(lightbar.yloc + lightbar.height - 1, lightbar.xpadding),
        msg, u' ', prompt_msg,)))
    sel = Selector(yloc=lightbar.yloc + lightbar.height - 1,
                   xloc=term.width - 25, width=18,
                   left='Yes', right=' No ')
    sel.colors['selected'] = term.reverse_red if attr is None else attr
    sel.keyset['left'].extend(keyset['yes'])
    sel.keyset['right'].extend(keyset['no'])
    echo(sel.refresh())
    term = getterminal()
    while True:
        inp = term.inkey()
        echo(sel.process_keystroke(inp))
        if((sel.selected and sel.selection == sel.left)
                or inp in keyset['yes']):
            # selected 'yes',
            return True
        elif((sel.selected or sel.quit)
                or inp in keyset['no']):
            # selected 'no'
            return False


def get_lightbar(ucs):
    """ Returns lightbar with content of given Unicode string, ``ucs``. """
    term = getterminal()
    width = min(80, max(term.width, 40))
    yloc = 0
    height = term.height - yloc - 1
    xloc = max(0, (term.width / 2) - (width / 2))
    lightbar = Lightbar(height, width, yloc, xloc)
    lightbar.glyphs['left-vert'] = lightbar.glyphs['right-vert'] = u''
    lightbar.colors['highlight'] = term.yellow_reverse
    set_lbcontent(lightbar, ucs)
    return lightbar


def get_lneditor(lightbar):
    """ Returns editor positioned at location of current selection. """
    term = getterminal()
    width = min(80, max(term.width, 40))
    yloc = (lightbar.yloc + lightbar.ypadding + lightbar.position[0] - 1)
    xloc = max(0, (term.width / 2) - (width / 2))
    lneditor = ScrollingEditor(width=width, yloc=yloc, xloc=xloc)
    lneditor.enable_scrolling = True
    lneditor.max_length = 65534
    lneditor.glyphs['bot-horiz'] = u''
    lneditor.glyphs['top-horiz'] = u''
    lneditor.colors['highlight'] = term.red_reverse
    lneditor.colors['border'] = term.bold_red
    # converts u'xxxxxx\r\n' to 'xxxxxx',
    # or 'zzzz\nxxxxxx\n' to u'zzzz xxxxxx',
    lneditor.update(softwrap_join(wrap_rstrip(lightbar.selection[1])))
    return lneditor


def main(save_key=None, continue_draft=False):
    """
    Main Editor procedure.

    When argument ``save_key`` is non-None, the result is saved
    to the user attribute of the same name.  When unset, the
    contents are returned to the caller.

    When argument ``continue_draft`` is non-None, the editor
    continues a previously saved draft, whose contents is its
    value.
    """
    # pylint: disable=R0914,R0912,R0915
    #         Too many local variables
    #         Too many branches
    #         Too many statements
    session, term = getsession(), getterminal()

    # set syncterm font, if any
    if term.kind.startswith('ansi'):
        echo(syncterm_setfont(syncterm_font))

    movement = (term.KEY_UP, term.KEY_DOWN, term.KEY_NPAGE,
                term.KEY_PPAGE, term.KEY_HOME, term.KEY_END,
                u'\r', term.KEY_ENTER)
    keyset = {'edit': (term.KEY_ENTER,),
              'command': (unichr(27), term.KEY_ESCAPE),
              'kill': (u'K',),
              'undo': (u'u', 'U',),
              'goto': (u'G',),
              'insert': (u'I',),
              'insert-before': (u'O',),
              'insert-after': (u'o',),
              'join': (u'J',),
              'rubout': (unichr(8), unichr(127),
                         unichr(23), term.KEY_BACKSPACE,),
              }

    def merge():
        """
        Merges line editor content as a replacement for the currently
        selected lightbar row. Returns True if text inserted caused
        additional rows to be appended, which is meaningful in a window
        refresh context.
        """
        lightbar.content[lightbar.index] = [
            lightbar.selection[0],
            softwrap_join(wrap_rstrip(lneditor.content))
            + HARDWRAP]
        prior_length = len(lightbar.content)
        prior_position = lightbar.position
        set_lbcontent(lightbar, get_lbcontent(lightbar))
        if len(lightbar.content) - prior_length == 0:
            echo(lightbar.refresh_row(prior_position[0]))
            return False
        while len(lightbar.content) - prior_length > 0:
            # hidden move-down for each appended line
            lightbar.move_down()
            prior_length += 1
        return True

    def statusline(lightbar):
        """
        Display status line and command help on ``lightbar`` borders
        """
        lightbar.colors['border'] = term.red if edit else term.yellow
        keyset_cmd = u''
        if not edit:
            keyset_cmd = u''.join((
                term.yellow(u'-( '),
                term.yellow_underline(u'S'), u':', term.bold(u'ave'),
                u' ',
                term.yellow_underline(u'A'), u':', term.bold(u'bort'),
                u' ',
                term.yellow_underline(u'?'), u':', term.bold(u'help'),
                term.yellow(u' )-'),))
            keyset_xpos = max(0, lightbar.width -
                              (term.length(keyset_cmd) + 3))
            keyset_cmd = lightbar.pos(lightbar.yloc + lightbar.height - 1,
                                      keyset_xpos
                                      ) + keyset_cmd
        return u''.join((
            lightbar.border(),
            keyset_cmd,
            lightbar.pos(lightbar.yloc + lightbar.height - 1,
                         lightbar.xpadding),
            u''.join((
                term.red(u'-[ '),
                u'EditiNG liNE ',
                term.reverse_red('%d' % (lightbar.index + 1,)),
                term.red(u' ]-'),)) if edit else u''.join((
                    term.yellow(u'-( '),
                    u'liNE ',
                    term.yellow('%d/%d ' % (
                        lightbar.index + 1,
                        len(lightbar.content),)),
                    '%3d%% ' % (
                        int((float(lightbar.index + 1)
                             / max(1, len(lightbar.content))) * 100)),
                    term.yellow(u' )-'),)),
            lightbar.title(u''.join((
                term.red('-] '),
                term.bold(u'Escape'),
                u':', term.bold_red(u'command mode'),
                term.red(' [-'),)
            ) if edit else u''.join((
                term.yellow('-( '),
                term.bold(u'Enter'),
                u':', term.bold_yellow(u'edit mode'),
                term.yellow(' )-'),))),
            lightbar.fixate(),
        ))

    def redraw_lneditor(lightbar, lneditor):
        """
        Return ucs suitable for refreshing line editor.
        """
        return ''.join((
            term.normal,
            statusline(lightbar),
            lneditor.border(),
            lneditor.refresh()))

    def get_ui(ucs, lightbar=None):
        """
        Returns Lightbar and ScrollingEditor instance.
        """
        lbr = get_lightbar(ucs)
        lbr.position = (lightbar.position
                        if lightbar is not None else (0, 0))
        lne = get_lneditor(lbr)
        return lbr, lne

    def banner():
        """
        Returns string suitable clearing screen
        """
        return u''.join((
            term.move(0, 0),
            term.normal,
            term.clear))

    def redraw(lightbar, lneditor):
        """
        Returns ucs suitable for redrawing Lightbar
        and ScrollingEditor UI elements.
        """
        return u''.join((
            term.normal,
            redraw_lightbar(lightbar),
            redraw_lneditor(lightbar, lneditor) if edit else u'',
        ))

    def redraw_lightbar(lightbar):
        """ Returns ucs suitable for redrawing Lightbar. """
        return u''.join((
            statusline(lightbar),
            lightbar.refresh(),))

    def resize(lightbar):
        """ Resize Lightbar. """
        if edit:
            # always re-merge current line on resize,
            merge()
        lbr, lne = get_ui(get_lbcontent(lightbar), lightbar)
        echo(redraw(lbr, lne))
        return lbr, lne

    if continue_draft:
        ucs = continue_draft
    else:
        ucs = u''
    lightbar, lneditor = get_ui(ucs, None)
    echo(banner())
    dirty = True
    edit = False
    digbuf, num_repeat = u'', -1
    count_repeat = lambda: range(max(num_repeat, 1))
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
        inp = term.inkey(1)

        # buffer keystrokes for repeat
        if (not edit and inp is not None
                and not isinstance(inp, int)
                and inp.isdigit()):
            digbuf += inp
            if len(digbuf) > 10:
                # overflow,
                echo(u'\a')
                digbuf = inp
            try:
                num_repeat = int(digbuf)
            except ValueError:
                try:
                    num_repeat = int(inp)
                except ValueError:
                    pass
            continue
        else:
            digbuf = u''

        # toggle edit mode,
        if inp in keyset['command'] or not edit and inp in keyset['edit']:
            edit = not edit  # toggle
            if not edit:
                # switched to command mode, merge our lines

                echo(term.normal + lneditor.erase_border())

                merge()
                lightbar.colors['highlight'] = term.yellow_reverse
            else:
                # switched to edit mode, save draft,
                # instantiate new line editor
                save_draft(save_key, get_lbcontent(lightbar))
                lneditor = get_lneditor(lightbar)
                lightbar.colors['highlight'] = term.red_reverse
            dirty = True

        # command mode, kill line
        elif not edit and inp in keyset['kill']:
            # when 'killing' a line, make accomidations to clear
            # bottom-most row, otherwise a ghosting effect occurs
            for _ in count_repeat():
                del lightbar.content[lightbar.index]
                set_lbcontent(lightbar, get_lbcontent(lightbar))
            if lightbar.visible_bottom > len(lightbar.content):
                echo(lightbar.refresh_row(lightbar.visible_bottom + 1))
            else:
                dirty = True
            save_draft(save_key, get_lbcontent(lightbar))

        # command mode, insert line
        elif not edit and inp in keyset['insert']:
            for _ in count_repeat():
                lightbar.content.insert(lightbar.index,
                                        (lightbar.index, HARDWRAP,))
                set_lbcontent(lightbar, get_lbcontent(lightbar))
            save_draft(save_key, get_lbcontent(lightbar))
            dirty = True

        # command mode; goto line
        elif not edit and inp in keyset['goto']:
            if num_repeat == -1:
                # 'G' alone goes to end of file,
                num_repeat = len(lightbar.content)
            echo(lightbar.goto((num_repeat or 1) - 1))
            echo(statusline(lightbar))

        # command mode; insert-before (switch to edit mode)
        elif not edit and inp in keyset['insert-before']:
            lightbar.content.insert(lightbar.index,
                                    (lightbar.index, HARDWRAP,))
            set_lbcontent(lightbar, get_lbcontent(lightbar))
            edit = dirty = True
            # switched to edit mode, save draft,
            # instantiate new line editor
            lightbar.colors['highlight'] = term.red_reverse
            lneditor = get_lneditor(lightbar)
            save_draft(save_key, get_lbcontent(lightbar))

        # command mode; insert-after (switch to edit mode)
        elif not edit and inp in keyset['insert-after']:
            lightbar.content.insert(lightbar.index + 1,
                                    (lightbar.index + 1, HARDWRAP,))
            set_lbcontent(lightbar, get_lbcontent(lightbar))
            edit = dirty = True
            # switched to edit mode, save draft,
            # instantiate new line editor
            lightbar.colors['highlight'] = term.red_reverse
            lightbar.move_down()
            lneditor = get_lneditor(lightbar)
            save_draft(save_key, get_lbcontent(lightbar))

        # command mode, undo
        elif not edit and inp in keyset['undo']:
            for _ in count_repeat():
                if len(UNDO):
                    set_lbcontent(lightbar, UNDO.pop())
                    dirty = True
                else:
                    echo(u'\a')
                    break

        # command mode, join line
        elif not edit and inp in keyset['join']:
            for _ in count_repeat():
                if lightbar.index + 1 < len(lightbar.content):
                    idx = lightbar.index
                    lightbar.content[idx] = (idx,
                                             WHITESPACE.join((
                                                 lightbar.content[
                                                     idx][1].rstrip(),
                                                 lightbar.content[idx + 1][1].lstrip(),)))
                    del lightbar.content[idx + 1]
                    prior_length = len(lightbar.content)
                    set_lbcontent(lightbar, get_lbcontent(lightbar))
                    if len(lightbar.content) - prior_length > 0:
                        lightbar.move_down()
                    dirty = True
                else:
                    echo(u'\a')
                    break
            if dirty:
                save_draft(save_key, get_lbcontent(lightbar))

        # command mode, basic cmds & movement
        elif not edit and inp is not None:
            if inp in (u'a', u'A',):
                if yes_no(lightbar, term.yellow(u'- ')
                          + term.bold_red(u'AbORt')
                          + term.yellow(u' -')):
                    return False
                dirty = True
            elif inp in (u's', u'S',):
                if yes_no(lightbar, term.yellow(u'- ')
                          + term.bold_green(u'SAVE')
                          + term.yellow(u' -'), term.reverse_green):
                    # save contents to user attribtue
                    content = get_contents(lightbar)
                    if not save_key:
                        # return entire message body as return value
                        return content
                    save(save_key, content)
                    return True
                dirty = True
            elif inp in (u'?',):
                show_help(term)
                term.inkey()
                # pager = Pager(lightbar.height, lightbar.width,
                #              lightbar.yloc, lightbar.xloc)
                # pager.update(get_help())
                #pager.colors['border'] = term.bold_blue
                # echo(pager.border() + pager.title(u''.join((
                #    term.bold_blue(u'-( '),
                #    term.white_on_blue(u'r'), u':', term.bold(u'eturn'),
                #    u' ',
                #    term.bold_blue(u' )-'),))))
                #pager.keyset['exit'].extend([u'r', u'R'])
                # pager.read()
                # echo(pager.erase_border())
                dirty = True
            else:
                moved = False
                for _ in count_repeat():
                    echo(lightbar.process_keystroke(inp))
                    moved = lightbar.moved or moved
                if moved:
                    echo(statusline(lightbar))

        # edit mode; movement
        elif edit and inp in movement:
            dirty = merge()
            if inp in (u'\r', term.KEY_ENTER,):
                lightbar.content.insert(lightbar.index + 1,
                                        [lightbar.selection[0] + 1, u''])
                inp = term.KEY_DOWN
                dirty = True
            ucs = lightbar.process_keystroke(inp)
            if lightbar.moved:
                # XXX optimize redraws
                echo(term.normal + lneditor.erase_border())
                echo(ucs)
                lneditor = get_lneditor(lightbar)
                save_draft(save_key, get_lbcontent(lightbar))
                echo(lneditor.border() + lneditor.refresh())

        # edit mode -- append character / backspace
        elif edit and inp is not None:
            if (inp in keyset['rubout']
                    and len(lneditor.content) == 0
                    and lightbar.index > 0):
                # erase past margin,
                echo(term.normal + lneditor.erase_border())
                del lightbar.content[lightbar.index]
                lightbar.move_up()
                set_lbcontent(lightbar, get_lbcontent(lightbar))
                lneditor = get_lneditor(lightbar)
                dirty = True
            else:
                # edit mode, add/delete ch
                echo(lneditor.process_keystroke(inp))
                if lneditor.moved:
                    echo(statusline(lightbar))

        if inp is not None and not isinstance(inp, int) and not inp.isdigit():
            # commands were processed, reset num_repeat to 1
            num_repeat = -1
