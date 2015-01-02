"""
User profile editor script for x/84, http://github.com/jquast/x84

This script is closely coupled with, and dependent upon nua.py.
"""
# std imports
from __future__ import division
import collections
import time

# bbs
from x84.bbs import getterminal, getsession, echo, timeago

# local
from common import display_banner
import nua

field = collections.namedtuple('input_validation', [
    # field's value
    'value',
    # field format, u'{lb}{key}{rb}mail:    {email}'
    'field_fmt',
    # description y/x loc,
    'disp_yloc', 'disp_xloc',
    # interactive edit field x/y loc, (None=read-only)
    'edit_yloc', 'edit_xloc',
    # edit field key, (None=read-only)
    'key',
    # width of field (None=not justified)
    'width',
])


def get_display_fields(user, yloc, xloc):
    # needs OrderedDict for nua.validation_fields[name]
    # so that we can reference validation functions from `nua'
    _indent = xloc + 4 + nua.username_max_length
    return collections.OrderedDict(
        # user: <name> last called 10m ago
        #              from ssh-127.0.0.1:65534
        #              1 calls, 1 posts
        user=field(value=user.handle,
                   field_fmt=u'{rb}{value}{lb}',
                   disp_yloc=yloc, disp_xloc=xloc,
                   edit_yloc=yloc, edit_xloc=xloc + 1,
                   key=u'c', width=nua.username_max_length),
        ago=field(value=timeago(time.time() - user.lastcall),
                  field_fmt=u'last called {value} ago',
                  disp_yloc=yloc,
                  disp_xloc=_indent,
                  edit_yloc=None, edit_xloc=None, key=None, width=None),
        last_from=field(value=user.get('last_from', 'None'),
                        field_fmt=u'from {value}',
                        disp_yloc=yloc + 1,
                        disp_xloc=_indent,
                        edit_yloc=None, edit_xloc=None, key=None, width=None),
        calls=field(value=str(user.calls),
                    field_fmt=u'{value} calls',
                    disp_yloc=yloc + 2,
                    disp_xloc=_indent,
                    edit_yloc=None, edit_xloc=None, key=None, width=None),
        posts=field(value=str(user.get('msgs_sent', 0)),
                    field_fmt=u'{value} posts',
                    disp_yloc=yloc + 2,
                    disp_xloc=_indent + len('1999 calls') + 1,
                    edit_yloc=None, edit_xloc=None, key=None, width=None),
        # go ahead, show them the salt; it gets trimmed,
        # and its gibberish, maybe it gives them confidence
        # that we don't know their actual password.
        password=field(value=u''.join(user.password),
                       field_fmt=u'{lb}{key}{rb}assword{colon} {value}',
                       disp_yloc=yloc + 5, disp_xloc=xloc,
                       edit_yloc=yloc + 5, edit_xloc=xloc + 12,
                       key=u'p', width=nua.password_max_length),
        origin=field(value=user.location,
                     field_fmt=u'{lb}{key}{rb}rigin{colon}   {value}',
                     disp_yloc=yloc + 7, disp_xloc=xloc,
                     edit_yloc=yloc + 7, edit_xloc=xloc + 12,
                     key=u'o', width=nua.location_max_length),
        email=field(value=user.email,
                    field_fmt=u'{lb}{key}{rb}mail{colon}    {value}',
                    disp_yloc=yloc + 9, disp_xloc=xloc,
                    edit_yloc=yloc + 9, edit_xloc=xloc + 12,
                    key=u'e', width=nua.email_max_length),
        sshkey=field(value=user.get('pubkey') and 'yes' or 'no',
                     field_fmt=u'{lb}{key}{rb}sh-key{colon}  {value}',
                     disp_yloc=yloc + 11, disp_xloc=xloc,
                     edit_yloc=yloc + 11, edit_xloc=xloc + 12,
                     key=u's', width=8),
        idle=field(value=str(user.get('timeout', 'no')),
                   field_fmt=u'{lb}{key}{rb}dle off{colon} {value}',
                   disp_yloc=yloc + 11, disp_xloc=xloc + 21,
                   edit_yloc=yloc + 11, edit_xloc=xloc + 34,
                   key=u'i', width=5),
    )


def display_options(term, session, yloc, xloc, user, fields):
    color_palette1 = ['bright_black', 'bright_black', 'bright_black']
    color_palette2 = ['bright_black', 'red', 'bright_red']
    color_palette3 = ['red', 'bright_red', 'red_reverse']
    palette1 = [getattr(term, _color) for _color in color_palette1]
    palette2 = [getattr(term, _color) for _color in color_palette2]
    palette3 = [getattr(term, _color) for _color in color_palette3]
    delay = 0.01

    # if the screen resizes during animation, return True,
    # forcing another full-screen refresh
    needs_refresh = False

    for count in range(3):
        if count < 2 and not delay:
            # on input, skip animation
            continue
        _color1, _color2, _color3 = (
            palette1[count % len(palette1)],
            palette2[count % len(palette2)],
            palette3[count % len(palette3)])
        lb, rb, colon = _color1('['), _color1(']'), _color1(':')
        for field in fields.values():
            # trim and padd field-value to maximum length,
            _value = (field.value[:field.width]
                      if field.width and term.length(field.value) > field.width
                      else term.ljust(field.value, field.width)
                      if field.width
                      else field.value)
            # backlight editable fields, bold others,
            _value = (_color3(_value) if field.key
                      else _color2(_value))
            # bold keystroke if not None,
            _key = _color2(field.key) if field.key else None
            # and display,
            echo(u'{move_yx}{text}'.format(
                move_yx=term.move(field.disp_yloc, field.disp_xloc),
                text=field.field_fmt.format(
                    rb=rb, lb=lb,
                    colon=colon,
                    value=_value,
                    key=_key)))
            if session.read_event('refresh', delay):
                needs_refresh = True
            elif session.poll_event('input'):
                # on input, skip animation
                delay = 0
    return needs_refresh


def display_prompt(term, session, yloc, xloc):
    # < [q]uit, [f]ind user, [c]hange name, [d]elete > ?
    lb, rb = term.bold_black('['), term.bold_black(']')
    is_sysop = session.user.is_sysop

    echo(term.move(yloc + 14, xloc))
    echo(u'{lt} {lb}{key_q}{rb}uit'.format(
        lt=term.red(u'<'), lb=lb, rb=rb,
        key_q=term.bold_red(u'q')))
    if is_sysop:
        # administrative functions (sysops only)
        echo(u', {lb}{key_f}{rb}ind user, '
             u'{lb}{key_c}{rb}hange name, '
             u'{lb}{key_d}{rb}elete'.format(
                 lb=lb, rb=rb,
                 key_f=term.bold_red(u'f'),
                 key_c=term.bold_red(u'c'),
                 key_d=term.bold_red(u'd')
             ))
    echo(u' {gt} ?\b\b'.format(gt=term.red('>')))


def main():
    """ Main procedure. """
    session, term = getsession(), getterminal()
    yloc = xloc = 0
    dirty = True
    tgt_user = session.user
    while True:
        if dirty or session.poll_event('refresh'):
            if term.height >= 24:
                echo(term.move(term.height - 1, 0))
                yloc = display_banner('art/ue.ans') + 1
            else:
                echo(term.move(term.height - 1, 0))
                # create a new, empty screen
                echo(u'\r\n' * (term.height + 1))
                yloc = 1
            xloc = max(5, (term.width // 2) - 30)
            fields = get_display_fields(tgt_user, yloc, xloc)
            if display_options(term, session, yloc, xloc, tgt_user, fields):
                # screen resized during redraw, draw again
                continue
            display_prompt(term, session, yloc, xloc)
            dirty = 0

        inp = term.inkey(0.1)

        if inp == u'q':
            break
        elif inp == u'\x0c':
            # ^L, refresh
            dirty = True
