# the ugliest parts of this script should be used
# to identify places where the API should be improved.

from x84.bbs import getterminal, ScrollingEditor, getsession
from x84.bbs import getch, echo, Lightbar, Ansi, Selector


CMDS_BASIC = (('e', 'dit'),
              ('s', 'ave'),
              ('a', 'bort'),
              ('/', 'cmds'), )
CMDS_ADVANCED = (('c', 'opy'),
                 ('p', 'aste'),
                 ('k', 'ill'),
                 ('q', 'uote'),
                 ('x', 'modem'), )


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
            output += u'- editing line %d -' % (lightbar.index, )
        else:
            pct = int((float(lightbar.index + 1)
                      / max(1, len(lightbar.content))) * 100)
            output += u'- line %d/%d %d%% -' % (
                lightbar.index + 1,
                len(lightbar.content),
                pct)
    else:
        output += msg
    xloc = max(0, lightbar.width - Ansi(cmds).__len__() - 1)
    output += lightbar.pos(lightbar.height, xloc)
    if cmds is None:
        if edit:
            cmds = cmdshow((('escape', 'cmd mode'), ))
        else:
            cmds = cmdshow(CMDS_BASIC)
    output += lightbar.pos(lightbar.height,
                           lightbar.width - len(Ansi(cmds)) - 1)
    output += cmds
    return output


def redraw_lightbar(lightbar, edit=False, msg=None, cmds=None):
    return statusline(lightbar, edit, msg, cmds) + lightbar.refresh()


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


def get_ui(ucs):
    lightbar = get_lightbar(ucs)
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


def process_keystroke(inp):
    return True
    pass


def main(uattr=u'draft'):
    session, term = getsession(), getterminal()
    SAVEKEY = '%s.%s' % ('editor', uattr)
    assert term.width >= 40, ('editor requires width >= 40')
    assert term.height >= 4, ('editor requires height >= 4')

    lightbar, lneditor = get_ui(session.user.get(SAVEKEY, u''))

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
        nc = Ansi('\n'.join([ucs for (key, ucs) in lightbar.content]) + '\n')
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
    while True:
        if session.poll_event('refresh'):
            dirty = True
        if dirty:
            echo(redraw(lightbar, lneditor, edit))
            dirty = False
        inp = getch(1)
        if(inp in (unichr(27), term.KEY_ESCAPE) or (
           not edit and inp in (u'e', u'E', term.KEY_ENTER, ))):
            edit = not edit
            if not edit:
                # switched to command mode, merge our lines
                merge()
            else:
                lneditor = get_lneditor(lightbar)
            dirty = True
        elif not edit:
            # command mode,
            if inp == u'/':
                echo(redraw_lightbar(lightbar, False,
                                     cmds=cmdshow(CMDS_ADVANCED)))
                inp2 = getch()
                if type(inp2) is not int:
                    dirty = process_keystroke(inp + inp2)
                else:
                    echo(redraw_lightbar(lightbar, False))
            elif inp is not None:
                # basic cmds,
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
                            inp = getch()
                            echo(yn.process_keystroke(inp))
                            if((yn.selected and yn.selection == yn.left)
                               or inp in (u'y', u'Y')):
                                # selected 'yes', save/abort
                                if inp in (u's', 'S'):
                                    session.user[SAVEKEY] = '\n'.join(
                                        (ucs for (key, ucs)
                                         in lightbar.content))
                                return
                            elif((yn.selected or yn.quit)
                                 or inp in (u'n', u'N')):
                                break
                        # no selected
                        dirty = True
                else:
                    # update status bar
                    echo(statusline(lightbar, edit))
                    # now update lightbar
                    echo(pout)
        else:
            # edit mode
            if inp in (term.KEY_UP, term.KEY_DOWN, term.KEY_NPAGE,
                       term.KEY_PPAGE, term.KEY_HOME, term.KEY_END,
                       u'\r', term.KEY_ENTER):
                if inp in (u'\r', term.KEY_ENTER):
                    # return key simulates downward stroke
                    inp = term.KEY_DOWN
                merge()
                if(inp == term.KEY_DOWN and
                   (lightbar.index == len(lightbar.content) - 1)):
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
            if inp is not None:
                echo(lneditor.process_keystroke(inp))
                if lneditor.moved:
                    echo(statusline(lightbar, edit))
