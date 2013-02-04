"""
Weather retriever for x/84 https://github.com/jquast/x84
"""
from xml.etree import cElementTree as ET
import StringIO
import requests
import time
# TODO: weather.get('WeatherIcon') ascii art


def disp_msg(msg):
    from x84.bbs import getterminal, echo
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
        term.bold_yellow('%s ' % (msg,),),
        term.yellow_reverse_bold(u'...'),)))


def disp_notfound():
    from x84.bbs import getsession, getterminal, echo, getch
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
        term.bold(u'bAd REQUESt'),
        term.bold_red(' -/- '),
        term.bold('NOt fOUNd.',),)))
    if not getsession().user.get('expert', False):
        getch(1.7)


def disp_found(num):
    from x84.bbs import getsession, getterminal, echo, getch
    term = getterminal()
    echo(u''.join((u'\r',
        term.bold_white(u'%d' % (num,)),
        term.yellow(u' lOCAtiON%s diSCOVEREd ' % (u's' if num > 1 else u'')),
        term.bold_black(u'...'),)))


def disp_search_help():
    from x84.bbs import getterminal, echo
    term = getterminal()
    msg_enterzip = (
            term.yellow(u'ENtER US '),
            term.bold_yellow(u'POStAl COdE'),
            term.yellow(u', OR NEARESt '),
            term.yellow(u'iNtERNAtiONAl CitY. '),
            term.bold_yellow(u'('),
            term.underline_yellow('Escape'),
            term.bold_white(u':'),
            term.yellow('EXit'),
            term.bold_yellow(u')'),)
    echo(u''.join((u'\r\n\r\n', term.normal,) + msg_enterzip))


def do_fetch(postal):
    import StringIO
    disp_msg('fEtChiNG')
    resp = requests.get(u'http://apple.accuweather.com'
            + u'/adcbin/apple/Apple_Weather_Data.asp',
            params=(('zipcode', postal),))
    weather = dict()
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
    xml_stream = StringIO.StringIO(resp.content)
    tree = ET.parse(xml_stream)
    return tree.getroot()


def do_search(search):
    import StringIO
    from x84.bbs import echo, getch, getterminal
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
        getch()
    else:
        xml_stream = StringIO.StringIO(resp.content)
        locations = list([dict(elem.attrib.items())
            for event, elem in ET.iterparse(xml_stream)
            if elem.tag == 'location'])
        if 0 == len(locations):
            disp_notfound()
        else:
            disp_found(len(locations))
    return locations


def parse_weather(root):
    weather = dict()
    # parse all current conditions from XML, value is cdata.
    for elem in root.find('CurrentConditions'):
        weather[elem.tag] = elem.text.strip() if elem.text is not None else u''
        # store attribute values
        for attr, val in elem.attrib.items():
            weather['%s-%s' % (elem.tag, attr)] = val
    return weather


def parse_forecast(root):
    forecast = dict()
    for elem in root.find('Forecast'):
        if elem.tag == 'day':
            key = elem.attrib.get('number')
            forecast[key] = dict()
            for subelem in elem:
                forecast[key][subelem.tag] = subelem.text.strip()
    return forecast


def get_zipsearch(zipcode=u''):
    from x84.bbs import getterminal, LineEditor, echo
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
        term.bold_yellow(u'  -'),
        term.reverse_yellow(u':'),
        u' ')))
    return LineEditor(width=min(30, term.width - 5), content=zipcode).read()


def chose_location_dummy(locations):
    from x84.bbs import getterminal, echo
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
    max_nwidth = len('%d' % (len(locations - 1),))
    def disp_entry(num, loc):
        return u''.join((
            term.bold_yellow('u['),
            u'%*d' % (max_nwidth, num),
            term.bold_yellow(u']'), u' ',
            term.yellow(loc['city']), u', ',
            term.yellow(loc['state']), u'\r\n',))
    for num, loc in enumerate(locations):
        echo(disp_entry(num, loc))
        if 0 == num % (term.height - 1):
            echo(term.reverse('--MORE--'))
            if getch() is None:
                break
            echo(u'\r\n')
    idx = u''
    while True:
        echo(u''.join(msg_enteridx))
        idx = LineEditor.read(width=max_width, content=idx)
        if idx is None or len(idx) == 0:
            return None
        try:
            idx = int(idx)
        except ValueError as err:
            echo(term.bold_red(u'\r\n%s' % (err,)))
            continue
        if idx < 0 or idx > len(locations) - 1:
            echo(term.bold_red(u'\r\nValue out of range'))
            continue
        return locations[idx]


def chose_location_lightbar(locations):
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
        yn = getch()
        if yn is None or yn in (u'n', u'N', 'q', 'Q', term.KEY_EXIT):
            return False
        if yn in (u'y', u'Y', u' ', term.KEY_ENTER):
            return True

def disp_forecast(forecast):
    from x84.bbs import getterminal, echo, Ansi, getch
    term = getterminal()
    width = min(60, term.width *.8)
    lno = 1
    echo(u'\r\n')
    for key in sorted(forecast.keys()):
        fc = forecast[key]
        rstr = u''.join((
            term.bold_yellow_underline(fc['DayCode']),
            u', ',
            term.yellow('/'.join(fc['ObsDate'].split('/',3)[0:2])),
            term.bold(u': '),
        u'%s. ' % (
                term.yellow_underline(
                    fc.get('TXT_Long', fc.get('TXT_Short', u''))),),
        u'hiGH Of %s, lOW Of %s. ' % (
                fc.get('High_Temperature'),
                fc.get('Low_Temperature'),),))
        if 0 != len(fc.get('WindDirection', u'')):
            rstr += 'WiNdS %s ' % (
                    term.bold_yellow(fc.get('WindDirection')),)
        if 0 != len(fc.get('WindSpeed', u'')):
            rstr += u'At %sMPh, ' % (
                    term.bold_yellow(fc.get('WindSpeed')),)
        if 0 != len(fc.get('WindGust', u'')):
            rstr += u'GUStS Of %sMPh. ' % (
                    term.bold_yellow(fc.get('WindGust')),)
            if 0 != len(fc.get('Real_Feel_High', u'')):
                rstr += u'PROdUCiNG '
        if 0 != len(fc.get('Real_Feel_High', u'')):
            rstr += u'A WiNdCHill Of %s/%s HiGh/lOW. ' % (
                    term.bold_yellow_underline(fc.get('Real_Feel_High')),
                    term.bold_yellow_underline(fc.get('Real_Feel_Low', u'?')),)
        echo(u'\r\n')
        lno += 1
        for line in Ansi(rstr).wrap(min(60, int(term.width * .8))
                ).split('\r\n'):
            lno += 1
            echo(line + u'\r\n')
            if 0 == lno % (term.height - 4):
                echo(term.reverse('--MORE--'))
                if getch() is None:
                    return False
                echo(u'\r\n')


def disp_weather(weather):
    from x84.bbs import getterminal, echo, Ansi, getch
    term = getterminal()
    width = min(60, term.width * .8)
    rstr = u''.join((u'At ',
        term.yellow(u'%s%s' % (weather.get('City'),
            u', %s' % (weather['State'],) if ('State' in weather
                and 0 != len(weather['State'])) else u'',)),
            term.bold(u': '),
        u'%s. ' % (
            term.yellow_underline(weather.get('WeatherText')),),
        u'ThE tEMPERAtURE WAS %s dEGREES, ' % (
            term.bold_yellow_underline(weather.get('Temperature')),),
        u'RElAtiVE hUMiditY WAS %s. ' % (
            term.bold_yellow(weather.get('Humidity')),),
        u'ThE WiNd WAS %s At %s MPh' % (
            term.bold_yellow(weather.get('WindDirection')),
            term.bold_yellow(weather.get('WindSpeed'))),
        u', PROdUCiNG A WiNdCHill Of %s dEGREES. ' % (
            term.bold_yellow_underline(weather.get('RealFeel')),)
        if (weather.get('RealFeel', weather.get('Temperature'))
              != weather.get('Temperature'))
        else u'. ',
        u'ThE PRESSURE WAS %s iNChES ANd %s.' % (
            term.bold_yellow(weather.get('Pressure')),
            term.bold_yellow(weather.get('Pressure-state')),
            ),))
    echo(u'\r\n\r\n')
    echo(Ansi(rstr).wrap(min(60, int(term.width * .8))))


def main():
    from x84.bbs import getsession, getterminal, echo, LineEditor, getch
    from x84.bbs import Lightbar, Pager
    session, term = getsession(), getterminal()

    echo(u'\r\n\r\n')
    search = u''
    location = session.user.get('location', dict())
    while not 'postal' in location:
        disp_search_help()
        search = get_zipsearch(search)
        if search is None or 0 == len(search):
            return # exit
        locations = do_search(search)
        if 0 != len(locations):
            location = (locations.pop() if 1 == len(locations)
                    else chose_location(locations) or dict())
    root = do_fetch(location.get('postal'))
    if root is None:
        return
    weather = parse_weather(root)
    if False == location_prompt(location, 'WEAthER'):
        return
    disp_weather(weather)
    if False == location_prompt(location, 'fORECASt'):
        return
    forecast = parse_forecast(root)
    disp_forecast(forecast)
    echo(u'\r\n')
    echo(term.yellow_reverse('--ENd Of tRANSMiSSiON--'))
    getch()
