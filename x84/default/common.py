""" common interface module for x/84, https://github.com/jquast/x84 """
from __future__ import division
import math

from x84.bbs import echo, showart
from x84.bbs import getterminal, LineEditor


def display_banner(filepattern, encoding=None):
    """ Start new screen and show artwork, centered.

    :param filepattern: file to display
    :type filepattern: str
    :param encoding: encoding of art file(s).
    :type encoding: str or None
    :returns: number of lines displayed
    :rtype: int
    """
    term = getterminal()

    # move to bottom of screen, reset attribute
    echo(term.pos(term.height) + term.normal)

    # create a new, empty screen
    echo(u'\r\n' * (term.height + 1))

    # move to home
    echo(term.home)

    # show art
    art_generator = showart(filepattern, encoding=encoding,
                            auto_mode=False, center=True)
    line_no = 0
    for line_no, txt in enumerate(art_generator):
        echo(txt)

    # return line number
    return line_no


def prompt_pager(content, line_no=0, colors=None, width=None, breaker=u'- '):
    """ Display text, using a command-prompt pager.

    :param content: iterable of text contents.
    :param line_no: line number to offset beginning of pager.
    :param colors: optional dictionary containing terminal styling
                   attributes, for keys 'highlight' and 'lowlight'.
                   When unset, yellow and green are used.
    """
    term = getterminal()
    colors = colors or {
        'highlight': term.yellow,
        'lowlight': term.green
    }
    pager_prompt = (u'{bl}{s}{br}top, {bl}{c}{br}ontinuous, or '
                    u'{bl}{enter}{br} for next page {br} {bl}\b\b'
                    .format(bl=colors['lowlight'](u'['),
                            br=colors['lowlight'](u']'),
                            s=colors['highlight'](u's'),
                            c=colors['highlight'](u'c'),
                            enter=colors['highlight'](u'return')))

    should_break = lambda line_no, height: line_no % (height - 3) == 0

    def show_breaker():
        if not breaker:
            return u''
        attr = colors['highlight']
        breaker_bar = breaker * (min(80, term.width - 1) // len(breaker))
        echo(attr(term.center(breaker_bar).rstrip()))

    continuous = False
    for txt in content:
        lines = term.wrap(txt, width) or [txt]
        for txt in lines:
            if width:
                txt = term.center(term.ljust(txt, max(0, width)))
            echo(txt.rstrip() + term.normal + term.clear_eol + u'\r\n')
            line_no += 1
            if not continuous and should_break(line_no, term.height):
                show_breaker()
                echo(u'\r\n')
                if term.width > 80:
                    echo(term.move_x((term.width // 2) - 40))
                echo(pager_prompt)
                while True:
                    inp = LineEditor(1, colors=colors).read()
                    if inp is None or inp and inp.lower() in u'sqx':
                        # s/q/x/escape: quit
                        echo(u'\r\n')
                        return
                    if len(inp) == 1:
                        echo(u'\b')
                    if inp.lower() == 'c':
                        # c: enable continuous
                        continuous = True
                        break
                    elif inp == u'':
                        # return: next page
                        break
                # remove pager
                echo(term.move_x(0) + term.clear_eol)
                echo(term.move_up() + term.clear_eol)

    show_breaker()
    echo(u'\r\n')
    if term.width > 80:
        echo(term.move_x((term.width // 2) - 40))
    echo(u'Press {enter}.'.format(
        enter=colors['highlight'](u'return')))
    inp = LineEditor(0, colors=colors).read()


def prompt_input(term, key, content=u'',
                 sep_ok=u'::', sep_bad=u'::',
                 width=None, colors=None):
    """ Prompt for and return input, up to given width and colorscheme.
    """
    from x84.bbs import getterminal
    term = getterminal()
    colors = colors or {
        'highlight': term.yellow,
    }
    sep_ok = colors['highlight'](sep_ok)

    echo(u'{sep} {key:<8}: '.format(sep=sep_ok, key=key))
    return LineEditor(colors=colors, width=width).read() or u''
