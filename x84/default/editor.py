import logging
import codecs
import os
from x84.bbs import getterminal, ScrollingEditor, Pager, getsession
from x84.bbs import getch, echo

logger = logging.getLogger()


def banner():
    term = getterminal()
    return term.home + term.normal + term.clear


def redraw(pager, le):
    rstr = u''
    rstr += pager.border()
    rstr += pager.refresh()
    rstr += le.border()
    rstr += le.refresh()
    return rstr


def get_ui(ucs, ypos=None):
    term = getterminal()
    width = max(term.width - 6, 80)
    height = max(term.height - 4, 20)
    pyloc = min(5, (term.height / 2) - (height / 2))
    pxloc = (term.width / 2) - (width / 2)
    pager = Pager(height, width, pyloc, pxloc)
    pager.colors['border'] = term.bold_blue
    pager.glyphs['left-vert'] = pager.glyphs['right-vert'] = u' '
    pager.update(ucs)
    yloc = (pager.yloc + pager.visible_bottom if ypos is None else ypos)
    le = ScrollingEditor(width, yloc, 0)
    le.glyphs['bot-horiz'] = le.glyphs['top-horiz'] = u''
    le.colors['border'] = term.bold_green
    return pager, le


def prompt_commands(pager):
    pager.footer('q-uit, s-save')
    # todo: prompt


def quit():
    # todo: prompt
    pass


def main(uattr=u'draft'):
    """
    Retreive and store unicode bytes to user attribute keyed by 'uattr';
    """
    session, term = getsession(), getterminal()

    fp = codecs.open(os.path.join(
        os.path.dirname(__file__), 'art', 'news.txt'), 'rb', 'utf8')
    test = fp.read().strip()

    pager, le = get_ui(test)
    dirty = True
    while True:
        if session.poll_event('refresh'):
            # user requested refresh ..
            pager, le = get_ui(u'\n'.join(pager.content), le.yloc)
            dirty = True
        if dirty:
            echo(banner())
            echo(redraw(pager, le))
            dirty = False
        inp = getch()
        logger.info(repr(inp) + 'input')
        res = le.process_keystroke(inp)
        if 0 != len(res):
            logger.info(repr(res) + 'echo')
            echo(res)
        elif le.quit:
            logger.info('QUIT')
            break
        elif le.carriage_returned:
            logger.info('RETURN')
            # woak
            break
        else:
            res = pager.process_keystroke(inp)
            echo(res)
            if pager.moved:
                logger.info(repr(res) + 'echo')
                echo(res)
