""" common interface module for x/84, https://github.com/jquast/x84 """
from __future__ import division

from x84.bbs import echo, showart
from x84.bbs import getterminal, LineEditor


def waitprompt():
    # Displays a simple "press enter to continue prompt". Very handy!
    from x84.bbs import echo, getch, getterminal
    term = getterminal()

    echo (term.normal+'\n\r'+term.magenta+'('+term.green+'..'+term.white+
          ' press any key to continue '+term.green+'..'+term.magenta+')')
    getch()
    echo(term.normal_cursor)
    return


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
                            center=True)
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


def coerce_terminal_encoding(term, encoding):
    # attempt to coerce encoding of terminal to match session.
    # NOTE: duplicated in top.py
    echo(u'\r\n')
    echo({
        # ESC %G activates UTF-8 with an unspecified implementation
        # level from ISO 2022 in a way that allows to go back to
        # ISO 2022 again.
        'utf8': u'\x1b%G',
        # ESC %@ returns to ISO 2022 in case UTF-8 had been entered.
        # ESC (U Sets character set G0 to codepage 437, such as on
        # Linux vga console.
        'cp437': u'\x1b%@\x1b(U',
    }.get(encoding, u''))
    # remove possible artifacts, at least, %G may print a raw G
    echo(term.move_x(0) + term.clear_eol)


def show_description(description, color='white', width=80):
    term = getterminal()
    wide = min(width, term.width)
    line_no = 0
    for line_no, txt in enumerate(term.wrap(description, width=wide)):
        echo(term.move_x(max(0, (term.width // 2) - (width // 2))))
        if color is not None:
            echo(getattr(term, color))
        echo(txt.rstrip())
        echo(u'\r\n')
    return line_no


def filesize(filename):
    """ display a file's size in human-readable format """

    from os import stat
    stat = stat(filename)
    filesize = None
    # file is > 400 megabytes; display in gigabytes
    if stat.st_size > 1024000 * 400:
        filesize = '%.2fG' % (stat.st_size / 1024000000)
    # file is > 400 kilobytes; display in megabytes
    if stat.st_size > 1024 * 400:
        filesize = '%.2fM' % (stat.st_size / 1024000)
    # file is at least 1 kilobyte; display in kilobytes
    elif stat.st_size >= 1024:
        filesize = '%.2fK' % (stat.st_size / 1024)
    # display in bytes
    else:
        filesize = '%dB' % stat.st_size
    return filesize
