import codecs
import os
from x84.bbs import getterminal, ScrollingEditor, getsession
from x84.bbs import getch, echo, Lightbar, Ansi


CMDS_BASIC = (('esc', 'toggle editmode'),
              ('e', 'dit'),
              ('s', 'ave'),
              ('a', 'bort'),
              ('/', 'advanced'), )
CMDS_ADVANCED = (('c', 'opy'),
                 ('p', 'aste'),
                 ('k', 'kill'),
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


def statusline(lightbar, edit=True, msg=None, cmds=None):
    term = getterminal()
    if msg is None:
        if edit:
            msg = term.bold_green(u'-- Edit --')
        else:
            msg = term.bold_blue(u'-- line %d/%d %d%% --' % (
                lightbar.index, len(lightbar.content),
                int(float(lightbar.index)
                    / ((max(1, len(lightbar.content))) * 100)), ))
    output = lightbar.border()
    output += lightbar.pos(lightbar.height, lightbar.xpadding)
    output += msg
    if cmds is None:
        if edit:
            cmds = fancy_green('esc', 'toggle editmode')
        else:
            cmds = term.blue('.').join(
                (fancy_blue(key, msg) for (key, msg) in CMDS_BASIC))
    xloc = max(0, lightbar.width - Ansi(cmds).__len__() - 1)
    output += lightbar.pos(lightbar.height, xloc)
    output += cmds
    return output


def redraw_lightbar(lightbar, edit=False, cmds=None):
    return lightbar.refresh() + statusline(lightbar, edit, cmds)


def get_lightbar(ucs, pos=None):
    # width 40 <=> 80 wide only
    term = getterminal()
    width = min(80, max(term.width, 40))
    yloc = 0
    height = term.height - yloc
    xloc = max(0, (term.width / 2) - (width / 2))
    lightbar = Lightbar(height, width, yloc, xloc)
    lightbar.glyphs['left-vert'] = lightbar.glyphs['right-vert'] = u''
    lightbar.colors['border'] = term.bold_blue
    lightbar.update(((row, line) for (row, line) in
                    enumerate(Ansi(ucs).wrap(lightbar.visible_width)
                              .split('\r\n'))))
    if pos is not None:
        lightbar.position = pos
    return lightbar


def get_lneditor(lightbar):
    # width 40 <=> 80 wide only
    # side effect: draws on get() !!
    term = getterminal()
    width = min(80, max(term.width, 40))
    yloc = (lightbar.yloc + lightbar.ypadding + lightbar.position[0])
    xloc = max(0, (term.width / 2) - (width / 2))
    lneditor = ScrollingEditor(width, yloc, xloc)
    lneditor.enable_scrolling = True
    lneditor.glyphs['bot-horiz'] = u''
    lneditor.glyphs['top-horiz'] = u''
    lneditor.colors['border'] = term.bold_green
    (key, ucs) = lightbar.selection
    echo(lneditor.update(ucs))
    return lneditor


def get_ui(ucs):
    lightbar = get_lightbar(ucs)
    lneditor = get_lneditor(lightbar)
    return lightbar, lneditor


def redraw_lneditor(lightbar, lneditor):
    return ''.join((lneditor.border(),
                    statusline(lightbar, edit=True),
                    lneditor.refresh()))


def redraw(lightbar, lneditor, edit=False):
    output = redraw_lightbar(lightbar)
    if edit:
        output += redraw_lneditor(lightbar, lneditor)
    return output


def process_keystroke(inp):
    pass


def main(uattr=u'draft'):
    session, term = getsession(), getterminal()
    assert term.width >= 40, ('editor requires width >= 40')
    assert term.height >= 4, ('editor requires width >= 4')

    fp = codecs.open(os.path.join(
        os.path.dirname(__file__), 'art', 'news.txt'), 'rb', 'utf8')
    test = fp.read().strip()

    lightbar, lneditor = get_ui(test)

    def merge():
        swp = lightbar.selection
        lightbar.content[lightbar.index] = (swp[0], lneditor.content)
        lightbar.update((key, ucs) for (key, ucs) in Ansi(
            '\n'.join((ucs for (key, ucs) in lightbar.content))).wrap(
                lightbar.visible_width).split('\r\n'))

    edit = False
    dirty = True
    while not lightbar.quit:
        if session.poll_event('refresh'):
            dirty = True
        if dirty:
            echo(banner())
            echo(redraw(lightbar, lneditor, edit))
            dirty = False
        inp = getch(1)
        if inp in (unichr(27), term.KEY_ESCAPE) or (not edit and inp == u'e'):
            edit = not edit
            if not edit:
                merge()
            else:
                lneditor = get_lneditor(lightbar)
            dirty = True
        elif not edit:
            if inp == u'/':
                # advanced cmds, (secondary key)
                echo(redraw_lightbar(lightbar, False, CMDS_ADVANCED))
                inp2 = getch()
                if type(inp2) is not int:
                    # pressing anything but unicode cancels
                    dirty = process_keystroke(inp + inp2)
            elif inp is not None:
                # basic cmds,
                echo(lightbar.process_keystroke(inp))
                if not lightbar.moved:
                    if inp in (u'a', u'A'):
                        return
                    if inp in (u's', u'S'):
                        # save
                        return
                else:
                    # update status bar
                    echo(statusline(lightbar, edit))
        else:
            # edit mode
            if inp in (term.KEY_UP, term.KEY_DOWN, term.KEY_NPAGE,
                       term.KEY_PPAGE, term.KEY_HOME, term.KEY_END,
                       u'\r', term.KEY_ENTER):
                # mixed-movement command mode, emacs-like
                echo(lightbar.process_keystroke(inp))
                if lightbar.moved:
                    merge()
            if inp is not None:
                echo(lneditor.process_keystroke(inp))
                if lneditor.moved:
                    echo(statusline(lightbar, edit))
