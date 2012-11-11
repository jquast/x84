import codecs
import os
from x84.bbs import getterminal, ScrollingEditor, getsession
from x84.bbs import getch, echo, Lightbar, Ansi


def banner():
    # could use some art .. !
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


def redraw(lightbar, lneditor, edit):
    term = getterminal()
    output = u''
    output += lightbar.border() + lightbar.refresh()
    if edit:
        output += lneditor.border() + lneditor.refresh()
        output += lightbar.footer(u'- ' + term.bold_blue('EDIT') + u' '
                                  + fancy_blue('esc', 'cmd mode') +
                                  (term.blue('.')
                                   + fancy_blue('/', 'cmd_mode')
                                   if 0 == len(lneditor.content)
                                   else u'')
                                  + u' -')
    else:
        output += lightbar.footer(u'- ' + term.bold_blue('CMD') + u' '
                                  + fancy_blue('e', 'dit') + term.blue('.')
                                  + fancy_blue('s', 'end') + term.blue('.')
                                  + fancy_blue('a', 'bort') + term.blue('.')
                                  + fancy_blue('u', '/l') + term.blue('.')
                                  + fancy_blue('d', '/l')
                                  + u' -')
    return output


def get_lightbar(ucs):
    term = getterminal()
    # height 40 <=> 80 wide only
    width = min(80, max(term.width, 40))
    yloc = 0
    height = term.height - yloc
    xloc = min(0, (term.width / 2) - (width / 2))
    lightbar = Lightbar(height, width, yloc, xloc)
    lightbar.glyphs['left-vert'] = lightbar.glyphs['right-vert'] = u''
    lightbar.colors['border'] = term.bold_blue
    lightbar.update(((row, line) for (row, line) in
                    enumerate(Ansi(ucs).wrap(lightbar.visible_width)
                              .split('\r\n'))))
    return lightbar


def get_lneditor(lightbar):
    term = getterminal()
    width = min(80, term.width - 6)
    yloc = (lightbar.yloc + lightbar.ypadding + lightbar.position[0])
    xloc = max(3, (term.width / 2) - (width / 2))
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


def main(uattr=u'draft'):
    session, term = getsession(), getterminal()
    assert term.width >= 40, ('editor requires width >= 40')
    assert term.height >= 4, ('editor requires width >= 4')

    fp = codecs.open(os.path.join(
        os.path.dirname(__file__), 'art', 'news.txt'), 'rb', 'utf8')
    test = fp.read().strip()

    lightbar, lneditor = get_ui(test)
    dirty = True
    edit = False
    while not lightbar.quit:
        if session.poll_event('refresh'):
            # user requested refresh ..
            lightbar, lneditor = get_ui(u'\n'.join(
                (line for (key, line) in lightbar.content)), lneditor.yloc)
            dirty = True
        if dirty:
            echo(banner())
            echo(redraw(lightbar, lneditor, edit))
            dirty = False
        inp = getch(1)
        if not edit:
            # command mode,
            echo(lightbar.process_keystroke(inp))
            if not lightbar.moved:
                if inp in (u'e', 'E'):
                    edit = True
                    lneditor = get_lneditor(lightbar)
                elif inp in (u's', 'S'):
                    pass  # save
                elif inp in (u'a', 'A'):
                    return  # abort (ays?!)
                elif inp in (u'u', 'U'):
                    pass  # upload
                elif inp in (u'd', 'D'):
                    pass  # download
                else:
                    echo(u'\a')
            continue
        echo(lneditor.process_keystroke(inp))
