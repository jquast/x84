import logging
import codecs
import os
from x84.bbs import getterminal, ScrollingEditor, getsession
from x84.bbs import getch, echo, Lightbar, Ansi

logger = logging.getLogger()


def banner():
    # could use some art .. !
    session, term = getsession(), getterminal()
    return term.home + term.normal + term.clear


def redraw(lightbar, lneditor):
    return (lightbar.border() + lightbar.refresh() +
            lneditor.border() + lneditor.refresh())


def get_ui(ucs, ypos=None):
    term = getterminal()
    width = min(80, term.width - 6)
    height = min(20, term.height - 4)
    yloc = min(5, max(0, (term.height / 2) - (height / 2)))
    xloc = max(0, (term.width / 2) - (width / 2))
    lightbar = Lightbar(height, width, yloc, xloc)
    lightbar.glyphs['left-vert'] = u'X'
    lightbar.glyphs['right-vert'] = u'X'
    lightbar.colors['border'] = term.bold_blue
    lightbar.update(((row, line) for (row, line) in
                    enumerate(Ansi(ucs).wrap(lightbar.width).split('\r\n'))))
    yloc = (lightbar.yloc + lightbar.visible_bottom if ypos is None else ypos)
    lneditor = ScrollingEditor(width, yloc, xloc)
    lneditor.glyphs['bot-horiz'] = u'Z'
    lneditor.glyphs['top-horiz'] = u'Z'
    lneditor.colors['border'] = term.bold_green
    return lightbar, lneditor


def main(uattr=u'draft'):
    session, term = getsession(), getterminal()

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
            echo(redraw(lightbar, lneditor))
            dirty = False
        inp = getch(1)
        if inp in (unichr(27), term.KEY_EXIT):
            # pick option; ..
            return
        if edit:
            echo(lneditor.process_keystroke(inp))
            if inp in (u'\r', term.KEY_ENTER, term.KEY_UP, term.KEY_DOWN):
                # save line; re-merge;
                #edit = False
                # (caveat; move up if term.KEY_UP, !)
                # (move to end of line; remain in edit mode!)
                None
            elif inp in (unichr(27), term.KEY_ESCAPE, u'/'):
                # just like oldschool bbs, / on new line only returns
                # to command mode, typically /s:end, /q:uit /..uhh
                edit = False
        else:
            echo(lightbar.process_keystroke(inp))
