""" Common interface utility functions for x/84. """
# std imports
from __future__ import division
import os
import math

# local
from x84.bbs import echo, showart, get_ini
from x84.bbs import getterminal, LineEditor


def decorate_menu_item(menu_item, colors):
    """ Return menu item decorated. """
    key_text = (u'{lb}{inp_key}{rb}'.format(
        lb=colors['lowlight'](u'['),
        rb=colors['lowlight'](u']'),
        inp_key=colors['highlight'](menu_item.inp_key)))

    # set the inp_key within the key_text if matching
    if menu_item.text.startswith(menu_item.inp_key):
        return menu_item.text.replace(menu_item.inp_key, key_text, 1)

    # otherwise prefixed with space
    return (u'{key_text} {menu_text}'.format(
        key_text=key_text, menu_text=menu_item.text))


def render_menu_entries(term, top_margin, menu_items,
                        colors=None, max_cols=3, max_rowsp=2):
    """
    Return all menu items rendered in decorated tabular format.

    :param term: terminal instance returned by :func:`getterminal`.
    :param int top_margin: the top-most row location to begin.
    :param menu_items: any object containing attributes ``inp_key``
                       and ``text``.
    :param dict colors: optional terminal attributes, containing
                        keys of ``highlight`` and ``lowlight``.
    :param int max_cols: maximum number of columns rendered.
    :param int max_row_spacing: maximum vertical row spacing.
    :rtype: str
    """
    # we take measured effects to do this operation much quicker when
    # colored_menu_items is set False to accommodate slower systems
    # such as the raspberry pi.
    if colors is not None:
        measure_width = term.length
    else:
        measure_width = str.__len__
        colors = {}
    colors['highlight'] = colors.get('highlight', lambda txt: txt)
    colors['lowlight'] = colors.get('lowlight', lambda txt: txt)

    # render all menu items, highlighting their action 'key'
    rendered_menuitems = [decorate_menu_item(menu_item, colors)
                          for menu_item in menu_items]

    # create a parallel array of their measurable width
    column_widths = map(measure_width, rendered_menuitems)

    # here, we calculate how many vertical sections of menu entries
    # may be displayed in 80 columns or less -- and forat accordingly
    # so that they are left-adjusted in 1 or more tabular columns, with
    # sufficient row spacing to padd out the full vertical height of the
    # window.
    #
    # It's really just a bunch of math to make centered, tabular columns..
    display_width = min(term.width, 80)
    padding = max(column_widths) + 3
    n_columns = min(max(1, int(math.floor(display_width / padding))), max_cols)
    xpos = max(1, int(math.floor((term.width / 2) - (display_width / 2))))
    xpos += int(math.floor((display_width - ((n_columns * padding))) / 2))
    rows = int(math.ceil(len(rendered_menuitems) / n_columns))
    height = int(math.ceil((term.height - 3) - top_margin))
    row_spacing = min(max(1, min(3, int(math.floor(height / rows)))), max_rowsp)

    column = 1
    output = u''
    for idx, item in enumerate(rendered_menuitems):
        padding_left = term.move_x(xpos) if column == 1 and xpos else u''
        padding_right = ' ' * (padding - column_widths[idx])
        if idx == len(rendered_menuitems) - 1:
            # last item, two newlines
            padding_right = u'\r\n' * 2
        elif column == n_columns:
            # newline(s) on last column only
            padding_right = u'\r\n' * row_spacing
        column = 1 if column == n_columns else column + 1
        output = u''.join((output, padding_left, item, padding_right))
    return output


def waitprompt(term):
    """ Display simple "press enter to continue prompt". """
    echo(u''.join((
        term.normal, '\r\n',
        term.move_x(max(0, (term.width // 2) - 40)),
        term.magenta('('), term.green('..'),
        'press any key to continue', term.green('..'), term.magenta(')')
    )))
    term.inkey()
    return


def display_banner(filepattern, vertical_padding=0, **kwargs):
    """
    Start new screen and show artwork, centered.

    :param str filepattern: file to display
    :param int vertical_padding: number of blank lines to prefix art
    :return: number of lines displayed
    :rtype: int

    Remaining parameters are inherited from :func:`showart`, such
    as ``center`` and ``encoding``.  By default, ``center`` is True.
    """
    # This is unfortunate, we should use 'term' as first argument
    term = getterminal()
    kwargs['center'] = kwargs.get('center', True)

    # move to bottom of screen, reset attribute
    echo(term.move(term.height, 0) + term.normal)

    # create a new, empty screen
    echo(u'\r\n' * (term.height + 1))

    # move to home, insert vertical padding
    echo(term.home + (u'\r\n' * vertical_padding))

    art_generator = showart(filepattern, **kwargs)
    line_no = 0
    for line_no, txt in enumerate(art_generator):
        echo(txt)

    # return line number
    return line_no + vertical_padding


def prompt_pager(content, line_no=0, colors=None, width=None,
                 breaker=u'- ', end_prompt=True, **kwargs):
    """ Display text, using a stop/continuous/next-page prompt.

    :param iterable content: iterable of text contents.
    :param int line_no: line number to offset beginning of pager.
    :param dict colors: optional dictionary containing terminal styling
                        attributes, for keys ``'highlight'`` and
                        ``'lowlight'``.  When unset, yellow and green
                        are used.
    :param int width: When set, text is left-justified-centered by width.
    :param str breaker: repeated decoration for page breaks
    :param bool end_prompt: Whether prompt should be displayed at end.
    :param kwargs: additional arguments to :func:`textwrap.wrap`
    :param bool end_prompt: use 'press enter prompt' at end.
    """
    # This is unfortunate, we should use 'term' as first argument
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

    # we must parse the entire tree, so that we can avoid the needless
    # call to show_breaker() on the final line.
    result = []
    for txt in content:
        if txt.rstrip():
            result.extend(term.wrap(txt, width, **kwargs))
        else:
            result.append(u'\r\n')

    xpos = 0
    if term.width:
        xpos = max(0, int((term.width / 2) - width / 2))
    for line_no, txt in enumerate(result):
        if xpos:
            echo(term.move_x(xpos))
        echo(txt.rstrip() + term.normal + term.clear_eol + u'\r\n')
        if (line_no and line_no != len(result) - 1
                and not continuous
                and should_break(line_no, term.height)):
            show_breaker()
            echo(u'\r\n')
            if xpos:
                echo(term.move_x(xpos))
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
            if breaker:
                # and breaker,
                echo(term.move_up() + term.clear_eol)

    if end_prompt:
        show_breaker()
        echo(u'\r\n')
        if term.width > 80:
            echo(term.move_x(max(0, (term.width // 2) - 40)))
        echo(u'Press {enter}.'.format(
            enter=colors['highlight'](u'enter')))
        inp = LineEditor(0, colors=colors).read()


def prompt_input(term, key, sep_ok=u'::', width=None, colors=None):
    """ Prompt for and return input, up to given width and colorscheme. """
    colors = colors or {'highlight': term.yellow}
    sep_ok = colors['highlight'](sep_ok)

    echo(u'{sep} {key:<8}: '.format(sep=sep_ok, key=key))
    return LineEditor(colors=colors, width=width).read() or u''


def coerce_terminal_encoding(term, encoding):
    """ Coerce encoding of terminal to match session by CSI. """
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


def show_description(term, description, color='white', width=80, **kwargs):
    """
    Display text as given ``color``, left-adjusted ``width``.

    :param str description: description text, may contain terminal attributes,
                            in which case ``color`` should be set to None.
    :param str color: terminal color attribute name, may be None.
    :param int width: left-adjusted width, if this is greater than the current
                      terminal's width, the terminal's width is used instead.
    :param kwargs: all remaining keyword arguments are passed to the built-in
                   :class:`textwrap.TextWrapper`.
    :rtype: int
    :returns: number if lines written
    """
    wide = min(width, term.width)
    xpos = max(0, (term.width // 2) - (wide // 2))

    lines = []
    for line in unicode(description).splitlines():
        if line.strip():
            lines.extend(term.wrap(line, wide, **kwargs))
        else:
            lines.append(u'')

    # output as a single string, reducing latency
    outp = u''.join(
        [getattr(term, color) if color else u''] +
        [u''.join((
            term.move_x(xpos) if xpos else u'',
            txt.rstrip(),
            term.clear_eol,
            u'\r\n')) for txt in lines])
    echo(outp)
    return len(outp.splitlines())


def filesize(filename):
    """ display a file's size in human-readable format """
    size = float(os.stat(filename).st_size)
    for scale in u'BKMGT':
        if size < 1000 or scale == u'T':
            if scale in u'BK':
                # no precision for bytees or kilobytes
                return (u'{size:d}{scale}'
                        .format(size=int(size), scale=scale))
            # 2-decimal precision
            return (u'{size:0.2f}{scale}'
                    .format(size=size, scale=scale))
        size /= 1024


def display_prompt(term, colors):
    """ Return string for displaying a system-wide command prompt. """
    colors['lowlight'] = colors.get('lowlight', lambda txt: txt)
    bbsname = get_ini(section='system', key='bbsname') or 'Unnamed'
    xpos = 0
    if term.width > 30:
        xpos = max(5, int((term.width / 2) - (80 / 2)))
    return (u'{xpos}{user}{at}{bbsname}{colon} '.format(
        xpos=term.move_x(xpos),
        user=term.session.user.handle,
        at=colors['lowlight'](u'@'),
        bbsname=bbsname,
        colon=colors['lowlight'](u'::')))
