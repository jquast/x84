""" common interface module for x/84, https://github.com/jquast/x84 """
from __future__ import division

from x84.bbs import echo, showart
from x84.bbs import getterminal, LineEditor


def display_banner(filepattern, encoding=None, vertical_padding=0):
    """ Start new screen and show artwork, centered.

    :param filepattern: file to display
    :type filepattern: str
    :param encoding: encoding of art file(s).
    :type encoding: str or None
    :param vertical_padding: number of blank lines to prefix art
    :type vertical_padding: int
    :returns: number of lines displayed
    :rtype: int
    """
    term = getterminal()

    # move to bottom of screen, reset attribute
    echo(term.pos(term.height) + term.normal)

    # create a new, empty screen
    echo(u'\r\n' * (term.height + 1))

    # move to home, insert vertical padding
    echo(term.home + (u'\r\n' * vertical_padding))

    # show art
    art_generator = showart(filepattern, encoding=encoding,
                            auto_mode=False, center=True)
    line_no = 0
    for line_no, txt in enumerate(art_generator):
        echo(txt)

    # return line number
    return line_no + vertical_padding


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
    show_breaker = lambda breaker, width: colors['highlight'](
        breaker * ((width // len(breaker)) - 1)) if breaker else u''
    continuous = False
    for txt in content:
        lines = term.wrap(txt, width) or [txt]
        for txt in lines:
            if width:
                txt = term.center(term.ljust(txt, max(0, width)))
            echo(txt.rstrip() + term.normal + term.clear_eol + u'\r\n')
            line_no += 1
            if not continuous and should_break(line_no, term.height):
                echo(show_breaker(breaker, term.width))
                echo(u'\r\n')
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

    echo(show_breaker(breaker, term.width))
    echo(u'\r\nPress {enter}.'.format(
        enter=colors['highlight'](u'return')))
    inp = LineEditor(0, colors=colors).read()
