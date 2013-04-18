"""
Weather retriever for x/84 https://github.com/jquast/x84
"""
from xml.etree import cElementTree as ET
import requests

# sorry this isn't doing celcius, etc., its just how the data comes,
# conversions were done in previous versions, but removed when rewritten
# for brevity.

def disp_msg(msg):
    """ Display unicode string ``msg`` in yellow. """
    from x84.bbs import getterminal, echo
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
                   term.bold_yellow('%s ' % (msg,),),
                   term.yellow_reverse_bold(u'...'),)))


def disp_notfound():
    """ Display 'bad request -/- not found in red. """
    from x84.bbs import getsession, getterminal, echo, getch
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
                   term.bold(u'bAd REQUESt'),
                   term.bold_red(' -/- '),
                   term.bold('NOt fOUNd.',),)))
    if not getsession().user.get('expert', False):
        getch(1.7)


def disp_found(num):
    """ Display 'N locations discovered' in yellow/white. """
    from x84.bbs import getterminal, echo
    term = getterminal()
    echo(u''.join((u'\r',
                   term.bold_white(u'%d' % (num,)),
                   term.yellow(u' lOCAtiON%s diSCOVEREd ' %
                               (u's' if num > 1 else u'')),
                   term.bold_black(u'...'),)))


def disp_search_help():
    """ Display searchbar usage. """
    from x84.bbs import getterminal, echo
    term = getterminal()
    msg_enterzip = (
        term.yellow(u'ENtER US '),
        term.bold_yellow(u'POStAl COdE'),
        term.yellow(u', OR NEARESt '),
        term.bold_yellow(u'iNtERNAtiONAl CitY. '),
        term.bold_yellow(u'('),
        term.underline_yellow('Escape'),
        term.bold_white(u':'),
        term.yellow('EXit'),
        term.bold_yellow(u')'),)
    echo(u''.join((u'\r\n\r\n', term.normal,) + msg_enterzip))


def do_fetch(postal):
    """
    Given postal code, fetch and return xml root node of weather results.
    """
    from x84.bbs import echo, getch, getterminal
    import StringIO
    term = getterminal()
    disp_msg('fEtChiNG')
    resp = requests.get(u'http://apple.accuweather.com'
                        + u'/adcbin/apple/Apple_Weather_Data.asp',
                        params=(('zipcode', postal),))
    if resp is None:
        disp_notfound()
        return None
    if resp.status_code != 200:
        # todo: logger.error
        echo(u'\r\n')
        echo(term.bold_red(u'StAtUS COdE: %s' % (resp.status_code,)))
        echo(u'\r\n\r\n')
        echo(repr(resp.content))
        echo(u'\r\n\r\n' + 'PRESS ANY kEY')
        getch()
        return None
    print resp.content
    xml_stream = StringIO.StringIO(resp.content)
    tree = ET.parse(xml_stream)
    return tree.getroot()


def do_search(search):
    """
    Given any arbitrary string, return list of possible matching locations.
    """
    import StringIO
    from x84.bbs import echo, getch
    disp_msg('SEARChiNG')
    resp = requests.get(u'http://apple.accuweather.com'
                        + u'/adcbin/apple/Apple_find_city.asp',
                        params=(('location', search),))
    locations = list()
    if resp is None:
        disp_notfound()
    elif resp.status_code != 200:
        # todo: logger.error
        echo(u'\r\n' + u'StAtUS COdE: %s\r\n\r\n' % (resp.status_code,))
        echo(repr(resp.content))
        echo(u'\r\n\r\n' + 'PRESS ANY kEY')
        getch()
    else:
        print resp.content
        xml_stream = StringIO.StringIO(resp.content)
        locations = list([dict(elem.attrib.items())
                          for _event, elem in ET.iterparse(xml_stream)
                          if elem.tag == 'location'])
        if 0 == len(locations):
            disp_notfound()
        else:
            disp_found(len(locations))
    return locations


def parse_weather(root):
    """
    Parse and return dictionary describing today's weather
    from weather xml root node.
    """
    weather = dict()
    # parse all current conditions from XML, value is cdata.
    for elem in root.find('CurrentConditions'):
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
    for elem in root.find('Forecast'):
        if elem.tag == 'day':
            key = elem.attrib.get('number')
            forecast[key] = dict()
            for subelem in elem:
                forecast[key][subelem.tag] = subelem.text.strip()
    return forecast


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
    dummy pager for chosing a location
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
        term.yellow('EXit'),
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
                   term.yellow(u'diSPlAY %s fOR ' % (msg,)),
                   term.bold('%(city)s, %(state)s' % location),
                   term.yellow(' ? '),
                   term.bold_yellow(u'['),
                   term.underline_yellow(u'yn'),
                   term.bold_yellow(u']'),
                   u': '),))
    while True:
        inp = getch()
        if inp is None or inp in (u'n', u'N', 'q', 'Q', term.KEY_EXIT):
            return False
        if inp in (u'y', u'Y', u' ', term.KEY_ENTER):
            return True


def disp_forecast(forecast):
    """ Display weather forecast.  """
    from x84.bbs import getterminal, echo, Ansi, getch
    term = getterminal()
    lno = 1
    echo(u'\r\n')
    for key in sorted(forecast.keys()):
        fcast = forecast[key]
        rstr = u''.join((
            term.bold_yellow_underline(fcast['DayCode']),
            u', ',
            u'/'.join(fcast['ObsDate'].split('/', 3)[0:2]),
            term.bold_underline(u':'), u' ',
            u'%s. ' % (
                term.bold(
                    fcast.get('TXT_Long', fcast.get('TXT_Short', u''))),),
            u'hiGH Of %sF, lOW Of %sF. ' % (
                term.bold(fcast.get('High_Temperature')),
                term.bold(fcast.get('Low_Temperature')),),))
        if 0.0 != float(fcast.get('Snow_Amount', '0.0')):
            rstr += u'SNOW AMOUNt %s iN., ' % (
                    term.yellow(fcast.get('Snow_Amount')),)
        if 0.0 != float(fcast.get('Rain_Amount', '0.0')):
            rstr += u'RAiN AMOUNt %s iN., ' % (
                    term.yellow(fcast.get('Snow_Amount')),)
        if 0.0 != float(fcast.get('Precip_Amount', '0.0')):
            rstr += u'PRECiPiTAtiON %s iN., ' % (
                    term.yellow(fcast.get('Precip_Amount')),)
        if 0 != int(fcast.get('TStorm_Prob', '0')):
            rstr += u'thUNdERStORM PRObAbilitY: %s, ' % (
                    term.yellow(fcast.get('TStorm_Prob')),)

        if 0 != len(fcast.get('WindDirection', u'')):
            rstr += u'WiNdS %s ' % (
                    term.yellow(fcast.get('WindDirection')),)
        if 0 != len(fcast.get('WindSpeed', u'')):
            rstr += u'At %sMPh, ' % (
                    term.yellow(fcast.get('WindSpeed')),)
        if 0 != len(fcast.get('WindGust', u'')):
            rstr += u'GUStS Of %sMPh. ' % (
                    term.yellow(fcast.get('WindGust')),)
            if 0 != len(fcast.get('Real_Feel_High', u'')):
                rstr += u'PROdUCiNG '
        if 0 != len(fcast.get('Real_Feel_High', u'')):
            rstr += u'A WiNdCHill HiGh Of %sF, lOW %sF. ' % (
                    term.yellow(
                        fcast.get('Real_Feel_High')),
                    term.yellow(
                        fcast.get('Real_Feel_Low', u'?')),)
        echo(u'\r\n')
        lno += 1
        lines = Ansi(rstr).wrap(min(60, int(term.width * .8))).splitlines()
        for line in lines:
            lno += 1
            echo(line + u'\r\n')
            if 0 == lno % (term.height - 1):
                echo(term.yellow_reverse('--MORE--'))
                if getch() is None:
                    return False
                echo(u'\r\n')


def disp_weather(weather):
    """ Display today's weather. """
    from x84.bbs import getterminal, echo, Ansi
    term = getterminal()
    rstr = u''.join((u'At ',
                     term.bold(u'%s%s' % (weather.get('City'),
                         u', %s' % (weather['State'],) if ('State' in weather
                             and 0 != len(weather['State'])) else u'',)),
                     term.underline(u':'), u' ',
                     u'%s. ' % (
                     term.bold_yellow(weather.get('WeatherText')),),
                     u'tEMPERAtURE Of %sF, ' % (
                     term.bold(weather.get('Temperature')),),
                     u'RElAtiVE hUMiditY %s. ' % (
                     term.yellow(weather.get('Humidity')),),
                     u'WiNdS %s At %s MPh' % (
                     term.yellow(weather.get('WindDirection')),
                     term.yellow(weather.get('WindSpeed'))),
                     u', PROdUCiNG A WiNdCHill Of %sF. ' % (
                     term.yellow(weather.get('RealFeel')),)
                     if (weather.get('RealFeel', weather.get('Temperature'))
                         != weather.get('Temperature'))
                     else u'. ',
                     u'ThE PRESSURE WAS %s iNChES ANd %s.' % (
                     term.yellow(weather.get('Pressure')),
                     term.yellow(weather.get('Pressure-state')),
                     ),))
    echo(u'\r\n\r\n')
    echo(Ansi(rstr).wrap(min(60, int(term.width * .8))))


def main():
    """ Main routine. """
    from x84.bbs import getsession, getterminal, echo, getch
    session, term = getsession(), getterminal()
    session.activity = 'Weather'

    echo(u'\r\n\r\n')
    location = session.user.get('location', dict())
    while True:
        search = location.get('postal', u'')
        disp_search_help()
        search = get_zipsearch(search)
        if search is None or 0 == len(search):
            return  # exit
        locations = do_search(search)
        if 0 != len(locations):
            location = (locations.pop() if 1 == len(locations)
                        else chose_location(locations) or dict())
        root = do_fetch(location.get('postal'))
        if root is None:
            return
        weather = parse_weather(root)
        #if False == location_prompt(location, 'WEAthER'):
        #    break
        disp_weather(weather)
        if False == location_prompt(location, 'fORECASt'):
            break
        forecast = parse_forecast(root)
        disp_forecast(forecast)
        echo(u'\r\n')
        echo(term.yellow_reverse('--ENd Of tRANSMiSSiON--'))
        getch()
        break

    if (sorted(location.items())
            != sorted(session.user.get('location', dict()).items())):
        echo(u''.join((u'\r\n\r\n',
                       term.yellow(u'SAVE lOCAtION'),
                       term.bold_yellow(' ('),
                       term.bold_black(u'PRiVAtE'),
                       term.bold_yellow(') '),
                       term.yellow('? '),
            term.bold_yellow(u'['),
            term.underline_yellow(u'yn'),
            term.bold_yellow(u']'),
            u': '),))
        while True:
            inp = getch()
            if inp is None or inp in (u'n', u'N', 'q', 'Q', term.KEY_EXIT):
                break
            if inp in (u'y', u'Y', u' ', term.KEY_ENTER):
                session.user['location'] = location
                break
