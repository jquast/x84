import logging
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


def get_ui(ucs=u'', ypos=None):
    term = getterminal()
    pager = Pager(term.height - 2, term.width, 1, 0)
    pager.colors['border'] = term.bold_blue
    pager.glyphs['left-vert'] = pager.glyphs['right-vert'] = u'|'
    pager.update(ucs)
    yloc = pager.visible_bottom if ypos is None else ypos
    # actually, should - 1 for border ?!
    le = ScrollingEditor(term.width, yloc, 0)
    le.glyphs['bot-horiz'] = le.glyphs['top-horiz'] = u'-'
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

    test = open(os.path.join(os.path.dirname(__file__),
                             'art', 'news.txt')).read().decode('utf8').strip()
    pager, le = get_ui(test)
    dirty = True
    while True:
        if session.poll_event('refresh'):
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


    #pager, le = get_ui(
    #        DBProxy('userattr')[session.user.handle].get(uattr, u''), 0)
    #xpos = Ansi(pager.content[-1]).__len__()
    #xpos
