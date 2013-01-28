"""
editor script for X/84, https://github.com/jquast/x84
"""
from x84.bbs import getterminal, ScrollingEditor, getsession
from x84.bbs import getch, echo, Lightbar, Ansi, Selector

import StringIO
import xmodem
import time

SAVEKEY = None
CLIPBOARD = None
CMDS_BASIC = (('e', 'dit'),
              ('s', 'AVE'),
              ('a', 'bORt'),
              ('/', 'CMdS'), )
CMDS_ADVANCED = (('c', 'OPY'),
                 ('p', 'AStE'),
                 ('k', 'ill'),
                 ('q', 'UOtE'),
                 ('x', 'MOdEM'), )
# x-modem send/recv untested. seems xmodem over telnet clients are far and few
# between for non-windows users.


def fancy_blue(char, blurb=u''):
    term = getterminal()
    return (term.bold_blue('(') + term.blue_reverse(char)
            + term.bold_blue + ')' + term.bold_white(blurb))


def cmdshow(cmds):
    term = getterminal()
    return u'- ' + term.blue('.').join(
        (fancy_blue(key, msg) for (key, msg) in cmds)) + u' -'


def get_lbcontent(lightbar):
    # pylint: disable=W0612: Unused variable 'key'
    return '\n'.join([ucs for (key, ucs) in lightbar.content])


def statusline(lightbar, edit=True, msg=None, cmds=None):
    output = u''
    output += lightbar.border()
    output += lightbar.pos(lightbar.height, lightbar.xpadding)
    if msg is None:
        if edit:
            output += u'- EditiNG liNE %d -' % (lightbar.index, )
        else:
            pct = int((float(lightbar.index + 1)
                      / max(1, len(lightbar.content))) * 100)
            output += u'- liNE %d/%d %d%% -' % (
                lightbar.index + 1,
                len(lightbar.content),
                pct)
    else:
        output += msg
    xloc = max(0, lightbar.width - Ansi(cmds).__len__() - 1)
    output += lightbar.pos(lightbar.height, xloc)
    if cmds is None:
        if edit:
            cmds = cmdshow((('escape', 'CMd MOdE'), ))
        else:
            cmds = cmdshow(CMDS_BASIC)
    output += lightbar.pos(lightbar.height,
                           lightbar.width - len(Ansi(cmds)) - 1)
    output += cmds
    return output


def process_keystroke(inp, lightbar):
    """
    Process editor command, like 's'ave or '/c'opy ..
    """
    def xgetch(size, timeout=1):
        """
        Retrieve next character from xmodem
        """
        nrecv = 0
        buf = list()
        st_time = time.time()
        while size > nrecv:
            timeleft = timeout - (time.time() - st_time)
            inp = getch(timeleft)
            if inp is None:
                break
            buf.append(inp)
            size += len(inp)
            assert 1 == len(inp)

    def xputch(data, timeout=1):
        """
        Put next character to xmodem
        """
        echo(data)
        return len(data)

    # return True if full screen refresh needed
    session, term = getsession(), getterminal()
    keys = {
        'abort': (u'a', u'A', u'q', u'Q'),
        'save': (u's', u'S'),
        'copy': (u'/c', u'/C'),
        'paste': (u'/p', u'/P'),
        'kill': (u'/k', u'/K'),
        'quote': (u'/q', u'/Q'),
        'xmodem': (u'/x', u'/X'),
        'yes': (u'y', u'Y'),
        'no': (u'n', u'N'),
    }
    if inp in keys['copy']:
        global CLIPBOARD
        CLIPBOARD = lightbar.selection[1]
        return False
    if inp in keys['paste']:
        swp = lightbar.selection
        lightbar.content.insert(lightbar.index, (swp[0], CLIPBOARD))
        nc = Ansi(get_lbcontent(lightbar) + u'\n')
        wrapped = nc.wrap(lightbar.visible_width).split(u'\r\n')
        prior_length = len(lightbar.content)
        lightbar.update([(key, ucs) for (key, ucs) in enumerate(wrapped)])
        while len(lightbar.content) - prior_length > 0:
            echo(lightbar.move_down())
            prior_length += 1
        return True
    if inp in keys['kill'] and len(lightbar.content):
        # when 'killing' a line, we must make accomidations to refresh
        # the bottom-most row (clear it), otherwise a ghosting effect
        # occurs ..
        del lightbar.content[lightbar.index]
        nc = Ansi(get_lbcontent(lightbar) + u'\n')
        wrapped = nc.wrap(lightbar.visible_width).split(u'\r\n')
        lightbar.update([(key, ucs) for (key, ucs) in enumerate(wrapped)])
        if lightbar.visible_bottom > len(lightbar.content):
            lightbar.refresh_row(lightbar.visible_bottom + 1)
        return True
    if inp in keys['xmodem']:
        echo(statusline(
            lightbar, edit=False, msg='- X/MOdEM -',
            cmds=term.yellow('  SENd OR RECEiVE?')))
        sr = Selector(yloc=lightbar.yloc + lightbar.height - 1,
                      xloc=term.width - 38, width=12,
                      left=' UPlOad ', right=' dOWNlOAd ')
        sr.colors['selected'] = term.reverse_blue
        sr.keyset['left'].extend((u's', u'S', u'u', u'U'))
        sr.keyset['right'].extend((u'r', u'R', u'd', u'D'))
        echo(sr.refresh())
        while True:
            inp2 = getch()
            echo(sr.process_keystroke(inp2))
            if sr.selected and sr.selection == sr.left:
                buf = StringIO.StringIO()
                modem = xmodem.XMODEM(xgetch, xputch)
                echo('\r\ngo ahead?')
                session.enable_keycodes = False
                modem.recv(buf, timeout=10)
                session.enable_keycodes = True
                echo('i got this...\r\n')
                echo(buf.getvalue())
                echo('\r\n')
                getch()
                break
            if sr.selected and sr.selection == sr.right:
                buf = StringIO.StringIO(get_lbcontent(lightbar))
                modem = xmodem.XMODEM(xgetch, xputch)
                session.enable_keycodes = False
                modem.send(buf, timeout=10)
                session.enable_keycodes = True
                echo('\r\ndid it work? lol..')
                getch()
                break
        return True

    # abort / save.. confirm !
    if inp in keys['abort'] or inp in keys['save']:
        echo(statusline(
            lightbar, edit=False, msg='- AbORt -'
            if inp in keys['abort'] else '- SAVE -',
            cmds=term.yellow('  ARE YOU SURE?')))
        yn = Selector(yloc=lightbar.yloc + lightbar.height - 1,
                      xloc=term.width - 28, width=12,
                      left='Yes', right='No')
        yn.colors['selected'] = term.reverse_red
        yn.keyset['left'].extend((u'y', u'Y',))
        yn.keyset['right'].extend((u'n', u'N',))
        echo(yn.refresh())
        while True:
            inp2 = getch()
            echo(yn.process_keystroke(inp2))
            if((yn.selected and yn.selection == yn.left)
               or inp2 in keys['yes']):
                # selected 'yes',
                if inp in keys['save']:
                    # save to session's user attribute
                    session.user[SAVEKEY] = get_lbcontent(lightbar)
                global EXIT
                EXIT = True
                break
            elif((yn.selected or yn.quit)
                    or inp2 in keys['no']):
                # selected 'no'
                break
        return True
    return False


def main(uattr=u'draft'):
    session, term = getsession(), getterminal()
    movement = (term.KEY_UP, term.KEY_DOWN, term.KEY_NPAGE,
                term.KEY_PPAGE, term.KEY_HOME, term.KEY_END,
                u'\r', term.KEY_ENTER)
    edit = False
    dirty = True
    global SAVEKEY, EXIT
    SAVEKEY = uattr
    EXIT = False
    input_buffer = session.user.get(SAVEKEY, u'')

    def get_lightbar(ucs, pos=None):
        # width 40 <=> 80 wide only
        term = getterminal()
        width = min(80, max(term.width, 40))
        yloc = 0
        height = term.height - yloc
        xloc = max(0, (term.width / 2) - (width / 2))
        lightbar = Lightbar(height, width, yloc, xloc)
        lightbar.glyphs['left-vert'] = lightbar.glyphs['right-vert'] = u''
        lightbar.colors['border'] = term.blue
        lightbar.colors['highlight'] = term.blue_reverse
        lightbar.update([(row, line) for (row, line) in
                         enumerate(Ansi(ucs).wrap(
                             lightbar.visible_width).split('\r\n'))])
        if pos is not None:
            lightbar.position = pos
        return lightbar

    def get_lneditor(lightbar):
        # width 40 <=> 80 wide only
        term = getterminal()
        width = min(80, max(term.width, 40))
        yloc = (lightbar.yloc + lightbar.ypadding + lightbar.position[0] - 1)
        xloc = max(0, (term.width / 2) - (width / 2))
        lneditor = ScrollingEditor(width, yloc, xloc)
        lneditor.enable_scrolling = True
        lneditor.glyphs['bot-horiz'] = u''
        lneditor.glyphs['top-horiz'] = u''
        lneditor.colors['highlight'] = term.green_reverse
        lneditor.colors['border'] = term.bold_green
        (key, ucs) = lightbar.selection
        lneditor.update(ucs)
        return lneditor

    def redraw_lneditor(lightbar, lneditor):
        return ''.join((
            statusline(lightbar, edit=True),
            lneditor.border(),
            lneditor.refresh()))

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
        nc = Ansi(get_lbcontent(lightbar) + u'\n')
        wrapped = nc.wrap(lightbar.visible_width).split(u'\r\n')
        prior_length = len(lightbar.content)
        lightbar.update([(key, ucs) for (key, ucs) in enumerate(wrapped)])
        if len(lightbar.content) - prior_length == 0:
            return False
        while len(lightbar.content) - prior_length > 0:
            # hidden move-down for each appended line
            lightbar.move_down()
            prior_length += 1
        return True

    def get_ui(ucs, old_lightbar=None):
        lightbar = get_lightbar(ucs)
        if old_lightbar is not None:
            lightbar.position = old_lightbar.position
        lneditor = get_lneditor(lightbar)
        return lightbar, lneditor

    def banner():
        session, term = getsession(), getterminal()
        return term.home + term.normal + term.clear

    def redraw():
        return redraw_lightbar(lightbar) + (
            redraw_lneditor(lightbar, lneditor) if edit else u'')

    def redraw_lightbar(lightbar, edit=False, msg=None, cmds=None):
        return statusline(lightbar, edit, msg, cmds) + lightbar.refresh()

    def resize():
        assert term.width >= 40, ('editor requires width >= 40')
        assert term.height >= 5, ('editor requires height >= 5')
        if edit:
            # always re-merge current line on resize,
            merge()
        input_buffer = get_lbcontent(lightbar)
        lb, le = get_ui(input_buffer, lightbar)
        echo(redraw())
        return lb, le

    lightbar, lneditor = get_ui(input_buffer, None)
    session.buffer_event(event='refresh', data=__file__)
    while not EXIT:
        # poll for refresh
        if session.poll_event('refresh'):
            echo(banner())
            lightbar, lneditor = resize()
            dirty = True
        if dirty:
            echo(redraw())
            dirty = False
        # poll for input
        inp = getch(1)
        # toggle edit mode,
        if(inp in (unichr(27), term.KEY_ESCAPE)
           or (not edit and inp in (u'e', u'E', term.KEY_ENTER, ))):
            edit = not edit  # toggle
            if not edit:
                # switched to command mode, merge our lines
                echo(lneditor.erase_border())
                merge()
                dirty = True
            else:
                # switched to edit mode, instantiate new line editor
                lneditor = get_lneditor(lightbar)
                dirty = True

        elif inp == u'/' and (not edit or lneditor.content == u''):
            # advanced commands,
            echo(redraw_lightbar(lightbar, edit,
                                 cmds=cmdshow(CMDS_ADVANCED)))
            inp2 = getch()
            if inp2 is not None and type(inp2) is not int:
                dirty = process_keystroke(inp + inp2, lightbar)
            dirty = True

        # basic cmds / movement
        elif not edit and inp is not None:
            # first, try as a movement command
            pout = lightbar.process_keystroke(inp)
            if not lightbar.moved:
                # no movement; try basic keystroke
                dirty = process_keystroke(inp, lightbar)
            else:
                # otherwise update status and movement
                echo(statusline(lightbar, edit))
                echo(pout)

        # edit mode, movement
        elif edit and inp in movement:
            if merge():
                # insertion occured, refresh
                echo(lightbar.refresh())
            if inp in (u'\r', term.KEY_ENTER):
                inp = term.KEY_DOWN
            if inp == term.KEY_DOWN and lightbar.at_bottom:
                # insert new line
                nxt = max([key for (key, ucs) in lightbar.content])
                lightbar.content.append((nxt + 1, u''))
            lightbar.process_keystroke(inp)
            if lightbar.moved:
                # refresh last selected lightbar row (our newly
                # realized input, correctly aligned), and erase
                # line editor border. Then, instantiate and
                # refresh a new line editor
                if (lightbar._vitem_lastshift != lightbar.vitem_shift):
                    # redraw full pager first, because we shifted pages,
                    echo(lightbar.refresh())
                else:
                    # just redraw last selection
                    echo(lightbar.refresh_row(lightbar._vitem_lastidx))
                # erase old line editor border and instatiate another
                echo(lneditor.erase_border())
                lneditor = get_lneditor(lightbar)
                echo(redraw_lneditor(lightbar, lneditor))
        # edit mode, append chr/backspace
        elif edit and inp is not None:
            # edit mode, addch
            echo(lneditor.process_keystroke(inp))
            if lneditor.moved:
                echo(statusline(lightbar, edit))
