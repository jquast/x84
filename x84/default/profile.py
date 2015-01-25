"""
User profile editor script for x/84.

This script is closely coupled with, and dependent upon nua.py.
"""
# std imports
from __future__ import division
import collections
import fnmatch
import string
import time

# bbs
from x84.bbs import getterminal, getsession, echo, timeago, get_ini, goto
from x84.bbs import list_users, find_user, get_user
from x84.bbs import LineEditor, ScrollingEditor

# local
from common import display_banner
import nua

#: lowlight color -- brackets ``[]``, and colon, ``:``
color_lowlight = get_ini(
    section='profile', key='color_lowlight'
) or 'bright_black'

#: highlight color -- read-only field values and hotkeys
color_highlight = get_ini(
    section='profile', key='color_highlight'
) or 'bright_magenta'

#: field display color -- read-only field values and hotkeys
color_field_display = get_ini(
    section='profile', key='color_field_display'
) or 'reverse_magenta'

#: field display color -- read-only field values and hotkeys
color_field_edit = get_ini(
    section='profile', key='color_field_edit'
) or 'reverse'

Point = collections.namedtuple('Point', ['y', 'x'])

field = collections.namedtuple('input_validation', [
    # field's value
    'value',
    # field format, u'{lb}{key}{rb}mail:    {email}'
    'field_fmt',
    # field text y/x loc,
    'display_location',
    # interactive edit field x/y loc, (None=read-only)
    'edit_location',
    # edit field key, (None=read-only)
    'key',
    # width of field (None=not justified)
    'width',
    # validating function
    'validate_fn',
    # text description for the content of this field,
    'description',
])


def get_display_fields(user, point):
    """ Return OrderedDict of display fields. """
    # reference the description text fields from nua.py
    # for their same purpose here.
    descriptions = {
        key: field.description for (key, field) in
        nua.get_validation_fields(user).items()}

    fields = collections.OrderedDict()
    _indent = point.x + 4 + nua.username_max_length
    # user: <name> last called 10m ago
    #              from ssh-127.0.0.1:65534
    #              1 calls, 1 posts
    fields['user'] = field(
        value=user.handle,
        field_fmt=u'{rb}{value}{lb}',
        display_location=Point(y=point.y, x=point.x),
        edit_location=Point(y=point.y, x=point.x + 1),
        key=None, width=nua.username_max_length, validate_fn=None,
        description=descriptions.get('handle')
    )
    fields['ago'] = field(
        value=timeago(time.time() - user.lastcall),
        field_fmt=u'last called {value} ago',
        display_location=Point(y=point.y, x=_indent),
        edit_location=Point(None, None),
        key=None, width=None, validate_fn=None, description=None,
    )
    fields['last_from'] = field(
        value=user.get('last_from', 'None'),
        field_fmt=u'from {value}',
        display_location=Point(y=point.y + 1, x=_indent),
        edit_location=Point(None, None),
        key=None, width=None, validate_fn=None, description=None,
    )
    fields['calls'] = field(
        value=str(user.calls),
        field_fmt=u'{value} calls',
        display_location=Point(y=point.y + 2, x=_indent),
        edit_location=Point(None, None),
        key=None, width=None, validate_fn=None, description=None,
    )
    fields['posts'] = field(
        value=str(user.get('msgs_sent', 0)),
        field_fmt=u'{value} posts',
        display_location=Point(y=point.y + 2,
                               x=_indent + len('1999 calls') + 1),
        edit_location=Point(None, None),
        key=None, width=None, validate_fn=None, description=None,
    )
    # go ahead, show them the password salt; it gets trimmed, and its gibberish,
    # maybe it gives them confidence that we don't know their actual password.
    _password = u''
    if user.handle != 'anonymous':
        _password = u''.join(user.password)
    fields['password'] = field(
        value=_password,
        field_fmt=u'{lb}{key}{rb}assword{colon} {value}',
        display_location=Point(y=point.y + 5, x=point.x),
        edit_location=Point(y=point.y + 5, x=point.x + 12),
        key=u'p', width=nua.password_max_length,
        validate_fn=nua.validate_password, description=None,
    )
    fields['location'] = field(
        value=user.location,
        field_fmt=u'{lb}{key}{rb}rigin{colon}   {value}',
        display_location=Point(y=point.y + 7, x=point.x),
        edit_location=Point(y=point.y + 7, x=point.x + 12),
        key=u'o', width=nua.location_max_length,
        validate_fn=None, description=descriptions.get('location'),
    )
    fields['email'] = field(
        value=user.email,
        field_fmt=u'{lb}{key}{rb}mail{colon}    {value}',
        display_location=Point(y=point.y + 9, x=point.x),
        edit_location=Point(y=point.y + 9, x=point.x + 12),
        key=u'e', width=nua.email_max_length,
        validate_fn=None, description=descriptions.get('email'),
    )
    fields['timeout'] = field(
        value=str(user.get('timeout', 'no')),
        field_fmt=u'{lb}{key}{rb}dle off{colon} {value}',
        display_location=Point(y=point.y + 11, x=point.x),
        edit_location=Point(y=point.y + 11, x=point.x + 12),
        key=u'i', width=5,
        # XXX
        validate_fn=None,
        description=(u"When set, Your session will be disconnected after this "
                     u"period of time has elapsed (in seconds).  0 disables."),
    )
    fields['pubkey'] = field(
        value=user.get('pubkey') or 'no',
        field_fmt=u'{lb}{key}{rb}sh-key{colon}  {value}',
        display_location=Point(y=point.y + 11, x=point.x + 19),
        edit_location=Point(y=point.y + 11, x=point.x + 31),
        key=u's', width=20,
        # XXX
        validate_fn=None,
        description=(u"Place your OpenSSH-compatible ssh public key into your "
                     u"clipboard, using command `pbcopy < ~/.ssh/id_rsa.pub` "
                     "on OSX or `xclip -i < ~/.ssh/id_rsa.pub` in X11.  Then, "
                     "simply paste it here. "),
    )
    fields['groups'] = field(
        value=','.join(user.groups),
        field_fmt=u'{lb}{key}{rb}roups{colon}   {value}',
        display_location=Point(y=point.y + 13, x=point.x),
        edit_location=Point(y=point.y + 13, x=point.x + 12),
        key=u'g', width=30,
        validate_fn=None,
        description=(u"Groups this user is a member of, separated by comma.  "
                     u"Notably, group 'sysop' has system-wide access, and "
                     u"group 'moderator' is able to moderate messages. "),
    )
    return fields


def show_banner(term):
    """ Display banner, calculate and return x/y coords as Point. """
    if term.height >= 24:
        echo(term.move(term.height - 1, 0))
        yloc = display_banner('art/ue.ans') + 1
    else:
        echo(term.move(term.height - 1, 0))
        # create a new, empty screen
        echo(u'\r\n' * (term.height + 1))
        yloc = 1
    return Point(y=yloc, x=max(5, (term.width // 2) - 30))


def display_options(term, fields):
    """ Display all fields with their values and edit-key commands. """
    _color1, _color2, _color3, _color4 = [
        getattr(term, _color)
        for _color in (color_lowlight,
                       color_highlight,
                       color_field_display,
                       color_field_edit)]

    lb, rb, colon = _color1('['), _color1(']'), _color1(':')
    out_text = u''
    for field_name, field in fields.items():
        # trim and padd field-value to maximum length,
        _align = term.center if field_name == 'user' else term.ljust
        _value = (
            # field value is greater than field width, trim to size
            u'.. ' + field.value[-(field.width - len(u'.. ')):]
            if field.width and term.length(field.value) > field.width
            # left-adjust string to length of field, except for user,
            # which is always centered
            else _align(field.value, field.width)
            if field.width
            # dynamic-length field, as-is
            else field.value)

        # backlight editable fields, bold others, except for 'user',
        # which has a special case of always being highlighted by
        # the 4th color of the palette.
        _value = (_color3(_value) if field.key
                  else _color4(_value) if field_name == 'user'
                  else _color2(_value))

        # bold keystroke if not None,
        _key = _color2(field.key) if field.key else None

        out_text += (
            u'{move_yx}{text}{clear_eol}'.format(
                move_yx=term.move(*field.display_location),
                text=field.field_fmt.format(
                    rb=rb, lb=lb, colon=colon, value=_value, key=_key),
                clear_eol=term.clear_eol))
    return out_text


def display_prompt(term, session, point):
    """ Display prompt. """
    # < [q]uit, [f]ind user, [d]elete > ?
    _color1, _color2, = [getattr(term, _color)
                         for _color in (color_lowlight, color_highlight)]
    lb, rb, colon = _color1('['), _color1(']'), _color1(':')

    out_text = term.move(*point)
    if session.user.is_sysop:
        out_text = u''.join(
            (out_text,
             u'{lb}{key_lt}{rb}prev, '
             .format(lb=lb, key_lt=_color2(u'<'), rb=rb)))

    out_text = u''.join(
        (out_text,
         u'{lb}{key_d}{rb}elete, '
         u'{lb}{key_q}{rb}uit'
         .format(lb=lb, rb=rb,
                 key_q=_color2(u'q'),
                 key_d=_color2(u'd'),
                 )))

    if session.user.is_sysop:
        # administrative functions (sysops only)
        out_text = u''.join(
            (out_text,
             u', {lb}{key_f}{rb}ind user, '
             u'{lb}{key_gt}{rb}next'
             .format(lb=lb, rb=rb,
                     key_f=_color2(u'f'),
                     key_gt=_color2(u'>'))))

    out_text = u''.join(
        (out_text,
         u'{colon}{clear_eos} ?\b\b'
         .format(colon=colon, clear_eos=term.clear_eos)))

    return out_text


def do_command(term, session, inp, fields, tgt_user, point):
    """ Perform action by given input. """
    _color1, _color2, _color3 = [
        getattr(term, _color) for _color in (
            color_lowlight, color_highlight, color_field_edit)]

    # discover edit field by matching command key
    field_name = None
    for _fname, field in fields.items():
        if field.key == inp.lower():
            field_name = _fname
            break

    if field_name is None:
        # return False if no field matches this key
        return False

    # only 'sysop' may edit user groups
    if field_name == 'groups' and not session.user.is_sysop:
        return False

    # pylint: disable=W0631
    #         Using possibly undefined loop variable 'field'

    # TODO: we could probably stand to do a bit of a better job of detecting
    # screen resizes and providing ^L full-screen refresh during the remainder
    # of this procedure ... It would require quite the refactor, though.

    # special case; ssh public keys and groups use scrolling editor
    if field_name in ('pubkey', 'groups'):
        editor = ScrollingEditor(
            # issue #161; because of a 'border' (that we don't draw),
            # y must be offset by 1 and height by 2.
            yloc=field.edit_location.y - 1,
            xloc=field.edit_location.x - 1,
            width=field.width + 2,
            colors={'highlight': _color3})
        # limit input to 1K
        editor.max_length = 1024
    else:
        editor = LineEditor(field.width, colors={'highlight': _color3})

    # find width for displaying description text and validation errors
    width = term.width - (point.x * 2)

    # show field description and cancellation
    description = (field.description or u'') + '  Press escape to cancel.'
    description_text = term.wrap(description, width=width)
    for y_offset, txt in enumerate(description_text):
        echo(term.move(point.y + y_offset, point.x))
        echo(_color1(txt) + term.clear_eol)
    echo(term.clear_eos)

    # edit input field (occludes display field).
    echo(term.move(*field.edit_location))
    inp = editor.read()
    if inp is None:
        # escape was pressed
        echo(term.move(*point))
        echo(_color2('Canceled !') + term.clear_eos)
        time.sleep(1)
        return True

    else:
        # validate input
        if field.validate_fn is not None:
            errmsg, _ = field.validate_fn(tgt_user, inp)
            if errmsg:
                # failed validation, display validation error
                errmsg += '  Press any key.'
                for y_offset, txt in enumerate(term.wrap(errmsg, width=width)):
                    echo(term.move(point.y + y_offset, point.x))
                    echo(_color2(txt) + term.clear_eol)
                echo(term.clear_eos)
                term.inkey()
                return True

        # well, it has validated, shall we apply it, then?
        if field_name in ('password', 'location', 'email',):
            # except for anonymous,
            if tgt_user.handle != 'anonymous':
                setattr(tgt_user, field_name, inp)
        elif field_name in ('timeout', 'pubkey',):
            if field_name == 'timeout':
                # coerce to integer, set, and if tgt_user is our current
                # user, then send new value for as engine event
                timeout_val = int(inp)
                if tgt_user.handle != 'anonymous':
                    tgt_user[field_name] = timeout_val
                if tgt_user.handle == session.user.handle:
                    session.send_event('set-timeout', timeout_val)
            elif field_name == 'pubkey':
                if tgt_user.handle != 'anonymous':
                    tgt_user[field_name] = inp
        elif field_name in ('groups'):
            new_groups = set(filter(None, set(map(unicode.strip, inp.split(',')))))
            for old_grp in tgt_user.groups.copy():
                if old_grp not in new_groups:
                    tgt_user.group_del(old_grp)
            for new_grp in new_groups:
                if new_grp not in tgt_user.groups:
                    tgt_user.group_add(new_grp)
        else:
            raise ValueError('unknown field name: {0}'.format(field_name))
    if tgt_user.handle != 'anonymous':
        tgt_user.save()
    return True


def delete_user(term, tgt_user, point):
    """ Delete given user. You may delete yourself. """
    _color1, _color2 = [getattr(term, _color)
                        for _color in (color_lowlight, color_highlight)]
    lb, rb, colon = _color1('['), _color1(']'), _color1(':')

    echo(term.move(*point))
    echo(u'Delete {handle} {lb}yN{rb}{colon}{clear_eos} ?\b\b'
         .format(handle=_color2(tgt_user.handle),
                 rb=rb, lb=lb, colon=colon,
                 clear_eos=term.clear_eos))
    inp = term.inkey()
    echo(inp + term.move(point.y + 2, point.x))
    if inp == u'y':
        if tgt_user.handle != 'anonymous':
            tgt_user.delete()
        echo(_color2('Deleted !'))
        time.sleep(1)
        return True

    echo(_color2('Canceled !'))
    time.sleep(1)
    return False


def locate_user(term, point):
    """ Prompt for search pattern and return discovered User. """
    _color1, _color2, _color3 = [
        getattr(term, _color) for _color in (
            color_lowlight, color_highlight, color_field_edit)]

    # show help
    width = term.width - (point.x * 2)
    help_txt = (u'Enter username or glob pattern.  Press escape to cancel.')
    y_offset = 0
    for y_offset, txt in enumerate(term.wrap(help_txt, width=width)):
        echo(term.move(point.y + y_offset, point.x))
        echo(_color1(txt) + term.clear_eol)
    point_prompt = Point(y=point.y + y_offset + 2, x=point.x)

    editor = LineEditor(nua.username_max_length, colors={'highlight': _color3})
    while True:
        # prompt for handle
        echo(term.move(*point_prompt))
        echo(u'handle: ' + term.clear_eol)
        inp = editor.read()

        point = Point(y=point_prompt.y + 2, x=point.x)
        if inp is None:
            # canceled (escape)
            return
        elif u'*' in inp or u'?' in inp:
            # a glob pattern, fetch all usernames
            handles = fnmatch.filter(list_users(), inp)
            if len(handles) == 0:
                echo(u''.join((term.move(*point),
                               u'No matches for {0}.'.format(_color2(inp)),
                               term.clear_eos)))
            elif len(handles) == 1:
                return get_user(handles[0])
            else:
                matches_text = (
                    u'{0} accounts matched, chose one: {1}.'.format(
                        _color2(str(len(handles))), u', '.join(
                            _color2(handle) for handle in handles)))
                echo(term.move(*point))
                for y_offset, txt in enumerate(
                        term.wrap(matches_text, width=width)):
                    echo(term.move(point.y + y_offset, point.x))
                    echo(txt + term.clear_eol)
                    if point.y + y_offset > term.height - 3:
                        # we simply cannot display anymore
                        break
                echo(term.clear_eos)
        else:
            handle = find_user(inp)
            if handle is not None:
                return get_user(handle)
            echo(u''.join((term.move(*point),
                           u'No matches for {0}.'.format(_color2(inp)),
                           term.clear_eos)))


def get_prev_user(tgt_user):
    """ Get previous user in sorted order. """
    handles = sorted(list_users())
    idx = max(handles.index(tgt_user.handle) - 1, 0)
    return get_user(handles[idx])


def get_next_user(tgt_user):
    """ Get next user in sorted order. """
    handles = sorted(list_users())
    try:
        current_idx = handles.index(tgt_user.handle)
    except ValueError:
        # what if we just deleted the target user?
        # inject it back into `handles' list and try again
        handles = sorted(handles + [tgt_user.handle])
        current_idx = handles.index(tgt_user.handle)
    idx = min(current_idx + 1, len(handles) - 1)
    try:
        return get_user(handles[idx])
    except KeyError:
        # and what if we deleted the last user of the list?
        # take the previous one.
        return get_user(handles[idx - 1])


def main():
    """ Main procedure. """
    dirty = -1
    session, term = getsession(), getterminal()
    tgt_user = session.user
    legal_input_characters = string.letters + u'<>'

    # re-display entire screen on loop,
    while True:

        # full-screen refresh on -1; otherwise only the fields (such as when an
        # edit has occurred).  dirty = -1 is set on screen resize, for example.
        if dirty == -1:
            # display banner, discover (y,x) point after,
            point_margin = show_banner(term)

            # forward-calculate the prompt (y,x) point
            point_prompt = Point(y=point_margin.y + 15, x=point_margin.x)

        # get all field values and locations,
        fields = get_display_fields(tgt_user, point=point_margin)

        # display all fields and prompt
        echo(display_options(term, fields))
        echo(display_prompt(term, session, point=point_prompt))

        dirty = 0

        # blocking loop until screen refresh or keystroke
        event = None
        while event is None:
            # This dual input/refresh trick only works here, receiving
            # raw (undecoded) keyboard data as 'inp' because we don't
            # require the use of any application keys or multi-byte
            # sequences, only alphabetic characters.
            event, data = session.read_events(('input', 'refresh'))
            if event == 'refresh':
                dirty = -1
                break

            inp = data
            if inp in legal_input_characters:
                # display command input
                echo(inp.decode('ascii'))

            if inp == u'q':
                # [q]uit
                echo(u'\r\n')
                return
            elif inp == u'\x0c':
                # [^L] refresh
                dirty = -1
                break
            elif inp == u'f' and session.user.is_sysop:
                tgt_user = locate_user(term, point_prompt) or tgt_user
                break
            elif inp == u'd':
                # yes, you can delete yourself !!
                if delete_user(term, tgt_user, point_prompt):
                    if tgt_user == session.user:
                        # but if you delete yourself,
                        # you must logoff.
                        goto('logoff')

                    # otherwise, move to next user
                    tgt_user = get_next_user(tgt_user)
                break
            elif inp == u'<' and session.user.is_sysop:
                tgt_user = get_prev_user(tgt_user)
                break
            elif inp == u'>' and session.user.is_sysop:
                tgt_user = get_next_user(tgt_user)
                break
            elif inp in string.letters:
                if do_command(
                        term, session, inp, fields, tgt_user, point_prompt):
                    # when returning True, perform full-screen refresh,
                    break
                else:
                    # otherwise, clean prompt field
                    time.sleep(0.2)
                    echo(u'\b \b')
            elif inp in legal_input_characters:
                # though legal, not authorized: clean prompt field
                time.sleep(0.2)
                echo(u'\b \b')
            event = None
        dirty = dirty or 1
