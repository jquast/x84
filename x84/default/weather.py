"""
Weather retriever for x/84 https://github.com/jquast/x84
"""
from xml.etree import cElementTree as ET
import itertools
import textwrap
import requests
import warnings
import logging
import time
import os


log = logging.getLogger(__name__)

weather_icons = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), 'art', 'weather')
panel_width = 15
panel_height = 8
top_margin = 1
next_margin = 2
timeout_fch = 3  # timeout of fahrenheit vs. centigrade prompt
cf_key = u'!'


def temp_conv(val, centigrade):
    """
    Convert temperature ``val`` to C or F, returning both the integer
    value and brief descriptor as tuple, fe. (33, u'F',).
    """
    try:
        val = int(val)
    except ValueError:
        return '', ''
    if not centigrade:
        return val, u'F'
    val = int((val - 32) * (float(5) / 9))
    return val, u'C'


def speed_conv(val, centigrade):
    """
    Convert windspeed ``val`` to MPH or KPH, returning both the integer
    value and brief descriptor as tuple, fe. (10, u'MPH',). We re-use
    the session boolean 'centigrade' as weather or not to use MPH or KPH,
    (centigrade is metric, otherwise imperial). This isn't 100% accurate,
    but close enough for our needs ..
    """
    # we simply use the 'centigrade' measurement as imperial vs. metric
    try:
        val = int(val)
    except ValueError:
        return '', ''
    if not centigrade:
        return val, u'MPH'
    else:
        return int(float(val) / 0.62137), 'KPH'


def disp_msg(msg):
    """ Display unicode string ``msg`` in yellow. """
    from x84.bbs import getterminal, echo
    term = getterminal()
    msg = term.bold_yellow(msg)
    dotdot = term.yellow_reverse_bold(u'...')
    echo(u'\r\n\r\n{msg} {dotdot}'.format(msg=msg, dotdot=dotdot))


def disp_notfound():
    """ Display 'bad request -/- not found in red. """
    from x84.bbs import getsession, getterminal, echo, getch
    term = getterminal()
    bad_req = term.bold(u'bAd REQUESt')
    decorator = term.bold_red(u'-/-')
    not_found = term.bold(u'NOt fOUNd.')
    echo(u'\r\n\r\n{bad_req} {decorator} {not_found}'.format(
        bad_req=bad_req, decorator=decorator, not_found=not_found))
    if not getsession().user.get('expert', False):
        getch(1.7)


def disp_found(num):
    """ Display 'N locations discovered' in yellow/white. """
    from x84.bbs import getterminal, echo
    term = getterminal()
    disp_n = term.bold_white(u'{}'.format(num))
    locations = term.yellow(u'Location{s} discovered'.format(
        s=u's' if num > 1 else u'',))
    dotdot = term.bold_black(u'...')
    echo(u'\r{disp_n} {locations} {dotdot}'.format(
        disp_n=disp_n, locations=locations, dotdot=dotdot))


def disp_search_help():
    """ Display searchbar usage. """
    from x84.bbs import getterminal, echo
    term = getterminal()

    enter = term.yellow(u'Enter U.S.')
    postal = term.bold_yellow(u'postal code')
    or_nearest = term.yellow(u', or nearest')
    int_city = term.bold_yellow(u'international citY.')
    keyhelp = (u'{t.bold_yellow}({t.normal}'
               u'{t.underline_yellow}Escape{t.normal}'
               u'{t.bold_white}:{t.normal}'
               u'{t.yellow}exit{t.normal}'
               u'{t.bold_yellow}){t.normal}'.format(t=term))

    echo(u'\r\n\r\n' + term.normal)
    echo(u''.join((
        term.wrap(u'{enter} {postal}{or_nearest} {int_city} {keyhelp}'
                  .format(enter=enter, postal=postal,
                          or_nearest=or_nearest,
                          int_city=int_city,
                          keyhelp=keyhelp),
                  term.width)
    )))


def fetch_weather(postal):
    """
    Given postal code, fetch and return xml root node of weather results.
    """
    import StringIO
    disp_msg(u'fEtChiNG')
    resp = requests.get(u'http://apple.accuweather.com'
                        + u'/adcbin/apple/Apple_Weather_Data.asp',
                        params=(('zipcode', postal),))
    if resp is None:
        disp_notfound()
        return None
    if resp.status_code != 200:
        raise RuntimeError('Status code: {}, content={!r}'.format(
            resp.status_code, resp.content))
    xml_stream = StringIO.StringIO(resp.content)
    tree = ET.parse(xml_stream)
    return tree.getroot()


def do_search(search):
    """
    Given any arbitrary string, return list of possible matching locations.
    """
    import StringIO
    from x84.bbs import echo, getch
    disp_msg(u'SEARChiNG')
    resp = requests.get(u'http://apple.accuweather.com'
                        + u'/adcbin/apple/Apple_find_city.asp',
                        params=(('location', search),))
    locations = list()
    if resp is None:
        disp_notfound()
    elif resp.status_code != 200:
        # todo: logger.error
        echo(u'\r\n' + u'Status Code: %s\r\n\r\n' % (resp.status_code,))
        echo(repr(resp.content))
        echo(u'\r\n\r\n' + 'Press any key')
        getch()
    else:
        # print resp.content
        xml_stream = StringIO.StringIO(resp.content)
        locations = list([dict(elem.attrib.items())
                          for _event, elem in ET.iterparse(xml_stream)
                          if elem.tag == 'location'])
        if 0 == len(locations):
            disp_notfound()
        else:
            disp_found(len(locations))
    return locations


def parse_todays_weather(root):
    """
    Parse and return dictionary describing today's weather
    from weather xml root node.
    """
    weather = dict()
    # parse all current conditions from XML, value is cdata.
    current_conditions = root.find('CurrentConditions')
    if current_conditions is None:
        log.error('Current conditions is None: root={!r}'
                  .format(ET.tostring(root)))
        return weather
    for elem in current_conditions:
        weather[elem.tag] = elem.text.strip() if elem.text is not None else u''
        # store attribute values
        for attr, val in elem.attrib.items():
            weather['%s-%s' % (elem.tag, attr)] = val
    return weather


def parse_forecast(root):
    """
    Parse and return dictionary describing weather forecast
    from weather xml root node.
    """
    forecast = dict()
    xml_forecast = root.find('Forecast')
    if xml_forecast is None:
        log.error('Forecast is None: root={!r}'
                  .format(ET.tostring(root)))
        return forecast

    for elem in xml_forecast:
        if elem.tag == 'day':
            key = int(elem.attrib.get('number'))
            forecast[key] = dict()
            for subelem in elem:
                forecast[key][subelem.tag] = subelem.text.strip()
    return [value for _key, value in sorted(forecast.items())]


def get_centigrade():
    """
    Blocking prompt for setting C/F preference
    """
    from x84.bbs import getterminal, getsession, echo, getch
    term = getterminal()
    session = getsession()
    echo(u'\r\n\r\n')
    echo(term.yellow(u'Celcius'))
    echo(term.bold_yellow(u'('))
    echo(term.bold_yellow_reverse(u'C'))
    echo(term.bold_yellow(u')'))
    echo(u' or ')
    echo(term.yellow(u'Fahrenheit'))
    echo(term.bold_yellow(u'('))
    echo(term.bold_yellow_reverse(u'F'))
    echo(term.bold_yellow(u')'))
    echo(u'? ')
    anonymous = bool(session.user.handle == 'anonymous')
    while True:
        inp = getch()
        if inp in (u'c', u'C'):
            session.user['centigrade'] = True
            if not anonymous:
                session.user.save()
            break
        elif inp in (u'f', u'F'):
            session.user['centigrade'] = False
            if not anonymous:
                session.user.save()
            break
        elif inp in (u'q', u'Q', term.KEY_EXIT):
            break


def chk_centigrade():
    """
    Provide hint for setting C/F preference (! key)
    """
    from x84.bbs import getterminal, getsession, echo, getch
    session, term = getsession(), getterminal()
    echo(u'\r\n\r\n')
    echo(u'USiNG ')
    if session.user.get('centigrade', None):
        echo(term.yellow(u'Celcius'))
    else:
        echo(term.yellow(u'Fahrenheit'))
    echo(term.bold_black('...'))
    echo(u' press ')
    echo(term.bold_yellow_reverse(cf_key))
    echo(u' to change.')
    if getch(timeout=timeout_fch) == cf_key:
        get_centigrade()


def chk_save_location(location):
    """
    Prompt user to save location for quick re-use
    """
    from x84.bbs import getterminal, getsession, echo, getch
    session, term = getsession(), getterminal()
    stored_location = session.user.get('location', dict()).items()
    if (sorted(location.items()) == sorted(stored_location)):
        # location already saved
        return
    if session.user.handle == 'anonymous':
        # anonymous cannot save preferences
        return

    # prompt to store (unsaved/changed) location
    echo(u'\r\n\r\n')
    echo(term.yellow(u'Save Location'))
    echo(term.bold_yellow(u' ('))
    echo(term.bold_black(u'private'))
    echo(term.bold_yellow(u') '))
    echo(term.yellow(u'? '))
    echo(term.bold_yellow(u'['))
    echo(term.underline_yellow(u'yn'))
    echo(term.bold_yellow(u']'))
    echo(u': ')
    while True:
        inp = getch()
        if inp is None or inp in (u'n', u'N', u'q', u'Q', term.KEY_EXIT):
            break
        if inp in (u'y', u'Y', u' ', term.KEY_ENTER):
            session.user['location'] = location
            break


def get_zipsearch(zipcode=u''):
    """
    Prompt user for zipcode or international city.
    """
    from x84.bbs import getterminal, LineEditor, echo
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
                   term.bold_yellow(u'  -'),
                   term.reverse_yellow(u':'),
                   u' ')))
    return LineEditor(width=min(30, term.width - 5), content=zipcode).read()


def chose_location_dummy(locations):
    """
    dummy pager to chose location
    """
    from x84.bbs import getterminal, echo, getch, LineEditor
    term = getterminal()
    msg_enteridx = (
        term.bold_yellow(u'('),
        term.underline_yellow(u'0'),
        term.yellow(u'-'),
        term.underline_yellow(u'%d' % (len(locations) - 1,)),
        term.yellow(u','),
        term.underline_yellow('Escape'),
        term.bold_white(u':'),
        term.yellow('exit'),
        term.bold_yellow(u')'), u' ',
        term.reverse_yellow(':'),)
    max_nwidth = len('%d' % (len(locations) - 1,))

    def disp_entry(num, loc):
        """ Display City, State.  """
        return u''.join((
            term.bold_yellow(u'['),
            u'%*d' % (max_nwidth, num),
            term.bold_yellow(u']'), u' ',
            term.yellow(loc['city']), u', ',
            term.yellow(loc['state']), u'\r\n',))
    echo(u'\r\n\r\n')
    lno = 3
    for num, loc in enumerate(locations):
        echo(disp_entry(num, loc))
        lno += 1
        if lno != 0 and (0 == lno % (term.height)):
            echo(term.yellow_reverse('--MORE--'))
            if getch() is None:
                break
            echo(u'\r\n')
            lno += 1
    idx = u''
    while True:
        echo(u'\r\n' + u''.join(msg_enteridx))
        idx = LineEditor(width=max_nwidth, content=idx).read()
        if idx is None or len(idx) == 0:
            return None
        try:
            int_idx = int(idx)
        except ValueError as err:
            echo(term.bold_red(u'\r\n%s' % (err,)))
            continue
        if int_idx < 0 or int_idx > len(locations) - 1:
            echo(term.bold_red(u'\r\nValue out of range'))
            continue
        return locations[int_idx]


def chose_location_lightbar(locations):
    """
    Lightbar pager for chosing a location.
    """
    from x84.bbs import getterminal, echo, Lightbar
    term = getterminal()
    fmt = u'%(city)s, %(state)s'
    lookup = dict([(loc['postal'], loc) for loc in locations])
    fullheight = min(term.height - 8, len(locations) + 2)
    fullwidth = min(75, int(term.width * .8))
    # shrink window to minimum width
    maxwidth = max([len(fmt % val) for val in lookup.values()]) + 2
    if maxwidth < fullwidth:
        fullwidth = maxwidth
    echo(u'\r\n' * fullheight)
    lightbar = Lightbar(height=fullheight,
                        width=fullwidth,
                        yloc=term.height - fullheight,
                        xloc=int((term.width / 2) - (fullwidth / 2)))
    lightbar.update([(key, fmt % val) for key, val in lookup.items()])
    lightbar.update([(key, fmt % val) for key, val in lookup.items()])
    lightbar.colors['border'] = term.yellow
    echo(lightbar.border())
    echo(lightbar.title(u''.join((
        term.yellow(u'-'), term.bold_white(u'[ '),
        term.bold_yellow('CitY'),
        term.bold_white(u', '),
        term.bold_yellow('StAtE'),
        term.bold_white(u' ]'), term.yellow(u'-'),))))
    echo(lightbar.footer(u''.join((
        term.yellow(u'-'), term.bold_black(u'( '),
        term.yellow_underline('Escape'), u':',
        term.yellow('EXit'),
        term.bold_black(u' )'), term.yellow(u'-'),))))
    lightbar.colors['highlight'] = term.yellow_reverse
    choice = lightbar.read()
    echo(lightbar.erase())
    return ((loc for loc in locations if choice == loc['postal']
             ).next() if choice is not None else choice)


def chose_location(locations):
    """
    Prompt user to chose a location.
    """
    from x84.bbs import getterminal, getsession, echo
    session, term = getsession(), getterminal()
    assert len(locations) > 0, (
        u'Cannot chose from empty list')
    msg_chosecity = (
        term.yellow(u'ChOSE A'),
        term.bold_yellow('CitY'),
        term.yellow_reverse(':'), u' ',)
    echo(u'\r\n\r\n')
    echo(u' '.join(msg_chosecity))
    if (session.user.get('expert', False) or 0 == term.number_of_colors):
        return chose_location_dummy(locations)
    return chose_location_lightbar(locations)


def location_prompt(location, msg='WEAthER'):
    """
    Prompt user to display weather or forecast.
    """
    from x84.bbs import getterminal, echo, getch
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
                   term.yellow(u'Display %s for ' % (msg,)),
                   term.bold('%(city)s, %(state)s' % location),
                   term.yellow(' ? '),
                   term.bold_yellow(u'['),
                   term.underline_yellow(u'yn'),
                   term.bold_yellow(u']'),
                   u': '),))
    while True:
        inp = getch()
        if inp is None or inp in (u'n', u'N', u'q', u'Q', term.KEY_EXIT):
            return False
        if inp in (u'y', u'Y', u' ', term.KEY_ENTER):
            return True


def get_icon(weather):
    from x84.bbs import from_cp437

    # attribute 'WeatherIcon' is mapped to one of the {}.ans files
    icon = int(weather.get('WeatherIcon', '1'))
    artfile = os.path.join(weather_icons, '{}.ans'.format(icon))
    if not os.path.exists(artfile):
        warnings.warn('{} not found'.format(artfile))
        art = u'[ .{:>2}. ]'.format(icon)
    else:
        art = [from_cp437(line.rstrip())
               for line in open(artfile, 'r').readlines()]
    return art


def display_panel(weather, column, centigrade):
    from x84.bbs import getterminal, echo, from_cp437
    term = getterminal()

    # display day of week,
    day_txt = term.bold(weather.get('DayCode', u'').center(panel_width))
    echo(term.move(top_margin, column))
    echo(day_txt)

    # display WeatherIcon ansi art,
    for row_idx, art_row in enumerate(get_icon(weather)):
        echo(term.move(row_idx + top_margin + 1, column))
        echo(art_row)
    echo(term.normal)

    degree = from_cp437(''.join([chr(248)]))
    # display days' high,
    echo(term.move(panel_height + top_margin + 1, column))
    high = weather.get('High_Temperature', None)
    high, conv = temp_conv(high, centigrade)
    echo(u'High: {high:>2}{degree}{conv}'.format(
        high=high, degree=degree, conv=conv).rjust(panel_width - 3))

    # display days' low,
    echo(term.move(panel_height + top_margin + 2, column))
    low = weather.get('Low_Temperature', None)
    low, conv = temp_conv(low, centigrade)
    echo(u'Low: {low:>2}{degree}{conv}'.format(
        low=low, degree=degree, conv=conv).rjust(panel_width - 3))

    # display short txt,
    weather_txt = unicode(weather.get('TXT_Short', ''))
    txt_wrapped = textwrap.wrap(weather_txt, (panel_width - 2))

    for row_idx, txt_row in enumerate(txt_wrapped):
        row_loc = panel_height + top_margin + row_idx + 4
        echo(term.move(row_loc, column + 1))
        echo(txt_row.center(panel_width - 2))
    return row_loc


def display_weather(todays, weather, centigrade):
    """
    Display weather as vertical panels.

    Thanks to xzip, we now have a sortof tv-weather channel art :-)
    """
    from x84.bbs import getterminal, echo, from_cp437
    term = getterminal()

    echo(term.height * u'\r\n')
    echo(term.move(0, 0))
    at = term.yellow_bold('At')
    city = term.bold(todays.get('City', u''))
    state = todays.get('State', u'')
    if state:
        state = u', {}'.format(term.bold_yellow_reverse(state))
    dotdot = term.bold_black('...')
    echo(u'{at} {city}{state} {dotdot}'.format(
        at=at, city=city, state=state, dotdot=dotdot))
    bottom = 2
    if weather:
        for column in range(0, (term.width - panel_width), panel_width):
            try:
                day = weather.pop(0)
            except IndexError:
                break
            bottom = max(display_panel(day, column, centigrade), bottom)

    timenow = time.strftime('%I:%M%p',
                            time.strptime(todays.get('Time', '00:00'),
                                          '%H:%M'))
    temp, deg_conv = temp_conv(todays.get('Temperature', ''), centigrade)
    real_temp, deg_conv = temp_conv(todays.get('RealFeel', ''), centigrade)
    speed, spd_conv = speed_conv(todays.get('WindSpeed', ''), centigrade)
    degree = from_cp437(''.join([chr(248)]))

    current_0 = u'Current conditions at {timenow}'.format(timenow=timenow)
    current_1 = u'{0}'.format(todays.get('WeatherText', ''))
    current_2 = u'Temperature is {temp}{degree}{deg_conv}'.format(
        temp=temp, degree=degree, deg_conv=deg_conv)
    current_3 = u'' if real_temp == temp else (
        u'(feels like {real_temp}{degree}{deg_conv})'.format(
            real_temp=real_temp, degree=degree, deg_conv=deg_conv))
    current_4 = u'Winds {speed}{spd_conv} {wind}'.format(
        speed=speed, spd_conv=spd_conv,
        wind=todays.get('WindDirection', ''))
    current_5 = u'Humidity of {0}'.format(todays.get('Humidity', ''))

    wrapped = textwrap.wrap(
        u'{0}: {1}. {2} {3}, {4}, {5}.'.format(
            current_0, current_1, current_2, current_3,
            current_4, current_5), min(term.width - panel_width - 2, 40))
    row_num = 0

    art = get_icon(todays)
    joined_art_conditions = list(itertools.izip_longest(wrapped, art))
    last_line = lambda row_num: row_num == len(joined_art_conditions) - 1
    for row_num, (row_txt, art_txt) in enumerate(joined_art_conditions):
        echo(term.move(bottom + next_margin + row_num, 1))
        echo(art_txt)
        if not row_txt and not last_line(row_num):
            echo(u'\r\n')
        elif row_txt:
            echo(term.move(bottom + next_margin + row_num, panel_width + 5))
            echo(term.normal)
            echo(row_txt)


def main():
    """ Main routine. """
    from x84.bbs import getsession, getterminal, echo, getch
    session, term = getsession(), getterminal()
    session.activity = 'Weather'

    while True:
        echo(u'\r\n\r\n')
        location = session.user.get('location', dict())
        search = location.get('postal', u'')
        disp_search_help()
        search = get_zipsearch(search)
        if search is None or 0 == len(search):
            # exit (no selection)
            return
        locations = do_search(search)
        if 0 != len(locations):
            location = (locations.pop() if 1 == len(locations)
                        else chose_location(locations) or dict())
        root = fetch_weather(location.get('postal'))
        if root is None:
            # exit (weather not found)
            return
        todays = parse_todays_weather(root)
        forecast = parse_forecast(root)
        if session.user.get('centigrade', None) is None:
            # request C/F preference,
            get_centigrade()
        else:
            # offer C/F preference change
            chk_centigrade()
        while True:
            centigrade = session.user.get('centigrade', False)
            display_weather(todays, forecast, centigrade)
            echo(term.move(term.height - 1, panel_width + 5))
            echo(term.yellow_reverse(u'--ENd Of tRANSMiSSiON--'))
            # allow re-displaying weather between C/F, even at EOT prompt
            if getch() == cf_key:
                get_centigrade()
                continue
            break
        break

    chk_save_location(location)
