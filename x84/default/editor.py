# the ugliest parts of this script should be used
# to identify places where the 'bbs' package could be improved.

from x84.bbs import getterminal, ScrollingEditor, getsession
from x84.bbs import getch, echo, Lightbar, Ansi, Selector

import StringIO
import xmodem
import time


def xgetch(size, timeout=1):
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
    echo(data)
    return len(data)


SAVEKEY = None
CLIPBOARD = None
EXIT = False
CMDS_BASIC = (('e', 'dit'),
              ('s', 'AVE'),
              ('a', 'bORt'),
              ('/', 'CMdS'), )
CMDS_ADVANCED = (('c', 'OPY'),
                 ('p', 'AStE'),
                 ('k', 'ill'),
                 ('q', 'UOtE'),
                 ('x', 'MOdEM'), )


def banner():
    session, term = getsession(), getterminal()
    return term.home + term.normal + term.clear


def fancy_blue(char, blurb=u''):
    term = getterminal()
    return (term.bold_blue('(') + term.blue_reverse(char)
            + term.bold_blue + ')' + term.bold_white(blurb))


def fancy_green(char, blurb=u''):
    term = getterminal()
    return (term.bold_green('(') + term.green_reverse(char)
            + term.bold_green + ')' + term.bold_white(blurb))


def cmdshow(cmds):
    term = getterminal()
    return u'- ' + term.blue('.').join(
        (fancy_blue(key, msg) for (key, msg) in cmds)) + u' -'


def statusline(lightbar, edit=True, msg=None, cmds=None):
    output = lightbar.border()
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


def redraw_lightbar(lightbar, edit=False, msg=None, cmds=None):
    return statusline(lightbar, edit, msg, cmds) + lightbar.refresh()


def get_lbcontent(lightbar):
    return '\n'.join([ucs for (key, ucs) in lightbar.content])


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
    lightbar.update([(row, line) for (row, line) in
                    enumerate(Ansi(ucs).wrap(lightbar.visible_width)
                              .split('\r\n'))])
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
    lneditor.colors['border'] = term.bold_green
    (key, ucs) = lightbar.selection
    lneditor.update(ucs)
    return lneditor


def get_ui(ucs, old_lightbar=None):
    lightbar = get_lightbar(ucs)
    if old_lightbar is not None:
        lightbar.pos = old_lightbar.pos
    lneditor = get_lneditor(lightbar)
    return lightbar, lneditor


def redraw_lneditor(lightbar, lneditor):
    return ''.join((
        statusline(lightbar, edit=True),
        lneditor.border(),
        lneditor.refresh()))


def redraw(lightbar, lneditor, edit=False):
    output = redraw_lightbar(lightbar)
    if edit:
        output += redraw_lneditor(lightbar, lneditor)
    return output


def process_keystroke(inp, lightbar):
    # return True if full screen refresh needed
    session, term = getsession(), getterminal()
    keys = {
        'abort': (u'a', u'A'),
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
        lightbar.content[lightbar.index] = (swp[0], CLIPBOARD)
        nc = Ansi(get_lbcontent(lightbar) + '\n')
        wrapped = nc.wrap(lightbar.visible_width).split('\r\n')
        prior_length = len(lightbar.content)
        lightbar.update([(key, ucs) for (key, ucs) in enumerate(wrapped)])
        while len(lightbar.content) - prior_length > 0:
            lightbar.move_down()
            prior_length += 1
        return True
    if inp in keys['kill']:
        del lightbar.content[lightbar.index]
        # this strange sequence forces a _chk_bounds .. !
        lightbar.position = lightbar.position
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
                    session[SAVEKEY] = get_lbcontent(lightbar)
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
    global SAVEKEY
    SAVEKEY = '%s.%s' % ('editor', uattr)
    input_buffer = session.user.get(SAVEKEY, u'')
    assert term.width >= 40, ('editor requires width >= 40')
    assert term.height >= 4, ('editor requires height >= 4')

    lightbar, lneditor = get_ui(input_buffer, None)
    movement = (term.KEY_UP, term.KEY_DOWN, term.KEY_NPAGE,
                term.KEY_PPAGE, term.KEY_HOME, term.KEY_END,
                u'\r', term.KEY_ENTER)

    def merge():
        """
        Merges line editor content as a replacement for the currently
        selected lightbar row. Returns True if text inserted caused
        additional rows to be appended, which is meaningful in refresh
        context.
        """
        # merge line editor with pager window content
        swp = lightbar.selection
        lightbar.content[lightbar.index] = (swp[0], lneditor.content)
        nc = Ansi(get_lbcontent(lightbar) + '\n')
        wrapped = nc.wrap(lightbar.visible_width).split('\r\n')
        prior_length = len(lightbar.content)
        lightbar.update([(key, ucs) for (key, ucs) in enumerate(wrapped)])
        if len(lightbar.content) - prior_length == 0:
            return False
        while len(lightbar.content) - prior_length > 0:
            lightbar.move_down()
            prior_length += 1
        return True

    edit = False
    dirty = True
    echo(banner())
    while not EXIT:
        if session.poll_event('refresh'):
            dirty = True
        if dirty:
            if edit:
                merge()
                edit = False
            lightbar, lneditor = get_ui(get_lbcontent(lightbar), lightbar)
            echo(redraw(lightbar, lneditor, edit))
            dirty = False
        inp = getch(1)

        # toggle edit mode,
        if(inp in (unichr(27), term.KEY_ESCAPE) or (
           not edit and inp in (u'e', u'E', term.KEY_ENTER, ))):
            print 'X'
            edit = not edit  # toggle
            if not edit:
                echo(lneditor.erase_border())
                # switched to command mode, merge our lines
                merge()
            else:
                lneditor = get_lneditor(lightbar)
            dirty = True
            continue

        if not edit:
            # advanced commands,
            if inp == u'/':
                echo(redraw_lightbar(lightbar, edit,
                                     cmds=cmdshow(CMDS_ADVANCED)))
                inp2 = getch()
                if type(inp2) is not int:
                    dirty = process_keystroke(inp + inp2, lightbar)
                else:
                    echo(redraw_lightbar(lightbar, edit))

            # basic cmds / movement
            elif inp is not None:
                pout = lightbar.process_keystroke(inp)
                if not lightbar.moved:
                    # abort / save: confirm
                    if inp in (u'a', u'A', u's', u'S'):
                        if inp in (u'a', 'A'):
                            echo(statusline(
                                lightbar, edit=False, msg='- abort -',
                                cmds=term.yellow('  Are you sure?')))
                        else:
                            echo(statusline(
                                lightbar, edit=False, msg='- save -',
                                cmds=term.yellow('  Are you sure?')))
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
                               or inp2 in (u'y', u'Y')):
                                # selected 'yes', save/abort
                                if inp in (u's', 'S'):
                                    session.user[SAVEKEY] = '\n'.join(
                                        [ucs for (key, ucs)
                                         in lightbar.content])
                                return
                            elif((yn.selected or yn.quit)
                                 or inp2 in (u'n', u'N')):
                                break
                        # no selected
                        dirty = True
                    # no movement; process basic keystroke
                    dirty = process_keystroke(inp, lightbar)
                else:
                    # movement; update status & lightbar
                    echo(statusline(lightbar, edit))
                    echo(pout)
            continue

        # edit mode, movement
        if inp in movement:
            if inp in (u'\r', term.KEY_ENTER):
                inp = term.KEY_DOWN
            if merge():
                # insertion occured, refresh
                echo(lightbar.refresh())
            if inp == term.KEY_DOWN and lightbar.at_bottom:
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
            continue

        # edit mode, addch
        if inp is not None:
            echo(lneditor.process_keystroke(inp))
            if lneditor.moved:
                echo(statusline(lightbar, edit))
