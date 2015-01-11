"""
Main menu script for x/84, http://github.com/jquast/x84
"""
# std imports
from __future__ import division
import collections
import math
import os

# local
from x84.bbs import getsession, getterminal, get_ini
from x84.bbs import echo, LineEditor, gosub, syncterm_setfont
from x84.bbs import ini

#: MenuItem is a definition class for display, input, and target script.
MenuItem = collections.namedtuple(
    'MenuItem', ['inp_key', 'text', 'script', 'args', 'kwargs'])

#: When set False, menu items are not colorized and render much
#: faster on slower systems (such as raspberry pi).
colored_menu_items = get_ini(
    section='main', key='colored_menu_items', getter='getboolean'
) or True

#: color used for menu key entries
color_highlight = get_ini(
    section='main', key='color_highlight'
) or 'bold_magenta'

#: color used for prompt
color_prompt = get_ini(
    section='main', key='color_prompt',
) or 'magenta_reverse'

#: color used for brackets ``[`` and ``]``
color_lowlight = get_ini(
    section='main', key='color_lowlight'
) or 'bold_black'

#: filepath to artfile displayed for this script
art_file = get_ini(
    section='main', key='art_file'
) or 'art/main*.asc'

#: encoding used to display artfile
art_encoding = get_ini(
    section='main', key='art_encoding'
) or 'cp437'  # ascii, actually

#: fontset for SyncTerm emulator
syncterm_font = get_ini(
    section='main', key='syncterm_font'
) or 'topaz'

#: system name of bbs
bbsname = get_ini(
    section='system', key='bbsname'
) or 'Unnamed'


def get_menu_items(session):
    """ Returns list of MenuItem entries. """
    #: A declaration of menu items and their acting gosub script
    menu_items = [
        # most 'expressive' scripts,
        MenuItem(inp_key=u'irc',
                 text=u'irc chat',
                 script='ircchat',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'who',
                 text=u"who's online",
                 script='online',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'fb',
                 text=u'file browser',
                 script='fbrowse',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'pe',
                 text=u'profile editor',
                 script='profile',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'weather',
                 text=u'weather forecast',
                 script='weather',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'hn',
                 text=u'hacker news',
                 script='hackernews',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'ol',
                 text=u'one-liners',
                 script='ol',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'tetris',
                 text=u'tetris game',
                 script='tetris',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'vote',
                 text=u'voting booth',
                 script='vote',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'lc',
                 text=u'last callers',
                 script='lc',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'user',
                 text=u'user list',
                 script='userlist',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'news',
                 text=u'news reader',
                 script='news',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'si',
                 text=u'system info',
                 script='si',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'key',
                 text=u'keyboard test',
                 script='extras.test_keyboard_keys',
                 args=(), kwargs={}),
        MenuItem(inp_key=u'ac',
                 text=u'adjust charset',
                 script='charset',
                 args=(), kwargs={}),

        # writemsg.py will be done from the reader (TODO
        MenuItem(inp_key=u'read',
                 text=u'read messages',
                 script='readmsgs',
                 args=(), kwargs={}),

        MenuItem(inp_key=u'g',
                 text=u'logoff system',
                 script='logoff',
                 args=(), kwargs={}),

    ]

    # there doesn't exist any documentation on how this works,
    # only the given examples in the generated default.ini file
    if ini.CFG.has_section('sesame'):
        from ConfigParser import NoOptionError
        for door in ini.CFG.options('sesame'):
            if door.endswith('_key'):
                # skip entries ending by _key.
                continue

            if not os.path.exists(ini.CFG.get('sesame', door)):
                # skip entry if path does not resolve
                continue

            try:
                inp_key = get_ini(section='sesame', key='{0}_key'.format(door))
            except NoOptionError:
                # skip entry if there is no {door}_key option
                continue

            menu_items.append(
                MenuItem(inp_key=inp_key,
                         text=u'play {0}'.format(door),
                         script='sesame',
                         args=(door,),
                         kwargs={}))

    # add sysop menu for sysop users, only.
    if session.user.is_sysop:
        menu_items.append(
            MenuItem(inp_key='sysop',
                     text=u'sysop area',
                     script='sysop',
                     args=(), kwargs={}))

    return menu_items


def decorate_menu_item(menu_item, term, highlight, lowlight):
    """ Return menu item decorated. """
    key_text = (u'{lb}{inp_key}{rb}'.format(
        lb=lowlight(u'['),
        rb=lowlight(u']'),
        inp_key=highlight(menu_item.inp_key)))

    # set the inp_key within the key_text if matching
    if menu_item.inp_key in menu_item.text:
        return menu_item.text.replace(menu_item.inp_key, key_text)

    # otherwise prefixed with space
    return (u'{key_text} {menu_text}'.format(
        key_text=key_text, menu_text=menu_item.text))


def render_menu_entries(term, top_margin, menu_items):
    """ Return all menu items rendered in decorated tabular format. """
    # we take measured effects to do this operation much quicker when
    # colored_menu_items is set False to accommodate slower systems
    # such as the raspberry pi.
    if colored_menu_items:
        highlight = getattr(term, color_highlight)
        lowlight = getattr(term, color_lowlight)
        measure_width = term.length
    else:
        highlight = lambda txt: txt
        lowlight = lambda txt: txt
        measure_width = str.__len__

    # render all menu items, highlighting their action 'key'
    rendered_menuitems = [
        decorate_menu_item(menu_item=menu_item, term=term,
                           highlight=highlight, lowlight=lowlight)
        for menu_item in menu_items
    ]
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
    n_columns = max(1, int(math.floor(display_width / padding)))
    xpos = max(1, int(math.floor((term.width / 2) - (display_width / 2))))
    xpos += int(math.floor((display_width - ((n_columns * padding))) / 2))
    rows = int(math.ceil(len(rendered_menuitems) / n_columns))
    height = int(math.ceil((term.height - 3) - top_margin))
    row_spacing = max(1, min(3, int(math.floor(height / rows))))

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


def get_line_editor(term, menu):
    """ Return a line editor suitable for menu entry prompts. """
    # if inp_key's were CJK characters, you should use term.length to measure
    # printable length of double-wide characters ... this is too costly to
    # enable by default.  Just a note for you east-asian folks.
    max_inp_length = max([len(item.inp_key) for item in menu])
    return LineEditor(width=max_inp_length,
                      colors={'highlight': getattr(term, color_prompt)})


def display_prompt(term):
    """ Return string for displaying command prompt. """
    xpos = 0
    if term.width > 30:
        xpos = max(5, int((term.width / 2) - (80 / 2)))
    return (u'{xpos}{user}{at}{bbsname}{colon} '.format(
        xpos=term.move_x(xpos),
        user=term.session.user.handle,
        at=getattr(term, color_lowlight)(u'@'),
        bbsname=bbsname,
        colon=getattr(term, color_lowlight)(u'::')))


def main():
    """ Main menu entry point. """
    from x84.default.common import display_banner
    session, term = getsession(), getterminal()

    text, width, height, dirty = u'', -1, -1, 2
    menu_items = get_menu_items(session)
    editor = get_line_editor(term, menu_items)
    while True:
        if dirty == 2:
            # set syncterm font, if any
            if syncterm_font and term.kind.startswith('ansi'):
                echo(syncterm_setfont(syncterm_font))
        if dirty:
            session.activity = 'main menu'
            top_margin = display_banner(art_file, encoding=art_encoding) + 1
            echo(u'\r\n')
            if width != term.width or height != term.height:
                width, height = term.width, term.height
                text = render_menu_entries(term, top_margin, menu_items)
            echo(u''.join((text, display_prompt(term), editor.refresh())))
            dirty = 0

        event, data = session.read_events(('input', 'refresh'))

        if event == 'refresh':
            dirty = True
            continue

        elif event == 'input':
            session.buffer_input(data, pushback=True)

            # we must loop over inkey(0), we received a 'data'
            # event, though there may be many keystrokes awaiting for our
            # decoding -- or none at all (multibyte sequence not yet complete).
            inp = term.inkey(0)
            while inp:
                if inp.code == term.KEY_ENTER:
                    # find matching menu item,
                    for item in menu_items:
                        if item.inp_key == editor.content.strip():
                            echo(term.normal + u'\r\n')
                            gosub(item.script, *item.args, **item.kwargs)
                            editor.content = u''
                            dirty = 2
                            break
                    else:
                        if editor.content:
                            # command not found, clear prompt.
                            echo(u''.join((
                                (u'\b' * len(editor.content)),
                                (u' ' * len(editor.content)),
                                (u'\b' * len(editor.content)),)))
                            editor.content = u''
                            echo(editor.refresh())
                elif inp.is_sequence:
                    echo(editor.process_keystroke(inp.code))
                else:
                    echo(editor.process_keystroke(inp))
                inp = term.inkey(0)
