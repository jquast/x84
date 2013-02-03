"""
(US) Weather retriever for x/84 https://github.com/jquast/x84
"""
from xml.etree import cElementTree as ET
import StringIO
import requests
import time

weather_xmlurl = (u'http://apple.accuweather.com/'
                  + 'adcbin/apple/')  # ?zipcode=%s'
location_xmlurl = (u'http://apple.accuweather.com/'
                   + 'adcbin/apple/Apple_find_city.asp')  # ?location=%s'
days = ('Sunday', 'Monday',
        'Tuesday', 'Wednesday',
        'Thursday', 'Friday',
        'Saturday',)
current_keys = (
    'City', 'State', 'Time', 'Temperature', 'RealFeel', 'Humidity',
    'WeatherText', 'WeatherIcon', 'WindSpeed', 'WindDirection',
    'Visibility', 'Precip', 'DayCode', 'Pressure', 'GmtDiff', 'Tree',
    'Weed', 'Grass', 'Mold', 'UVIndex', 'Copyright', 'AirQuality',
    'AirQualityType',)
fcast_keys = (
    'TXT_Short', 'TXT_Long', 'High_Temperature', 'Low_Temperature',
    'Real_Feel_High', 'Real_Feel_Low', 'WindGust', 'MaxUV',
    'Rain_Amount', 'Snow_Amount', 'Precip_Amount', 'TStorm_Prob',
    'DayCode', 'WeatherIcon', 'WindSpeed', 'WindDirection', 'Max_UV',)


def disp_searching():
    from x84.bbs import getterminal, echo
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
        term.clear_eol,
        term.bold_yellow(u'SEARChiNG '),
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
    echo(u''.join((u'\r\n\r\n', term.clear_eol, term.normal,) + msg_enterzip))

def get_zipsearch(zipcode=u''):
    from x84.bbs import getterminal, LineEditor, echo
    term = getterminal()
    echo(u''.join((u'\r\n\r\n',
        term.clear_eol,
        term.normal,
        term.bold_yellow(u'  -'),
        term.reverse_yellow(u':'),
        u' ')))
    return LineEditor(width=min(30, term.width - 5), content=zipcode).read()

def do_weather(postal):
    import StringIO
    resp = requests.get(u'http://apple.accuweather.com'
            + u'/adcbin/apple/Apple_Weather_Data.asp',
            params=(('zipcode', postal),))
    weather = dict()
    if resp is None:
        disp_notfound()
    elif resp.status_code != 200:
        # todo: logger.error
        echo(u'\r\n\r\n')
        echo(term.bold_red(u'StAtUS COdE: %s' % (resp.status_code,)))
        echo(u'\r\n\r\n')
        echo(repr(resp.content))
        echo(u'\r\n\r\n' + 'PRESS ANY kEY')
        getch()
    else:
        xml_stream = StringIO.StringIO(resp.content)
        tree = ET.parse(xml_stream)
        root = tree.getroot()
        for elem in root.find('CurrentConditions'):
            if elem.tag in ('City', 'State', 'DaylightSavingsActive', 'UFDB'):
                continue
            weather[elem.tag] = elem.text.strip()
        weather['Pressure-state'] = root.find('CurrentConditions'
                ).find('Pressure').attrib.get('state')
        for elem in root.find('Forecast'):
            print elem.tag, elem.attrib
            for subelem in elem:
                print subelem.tag, subelem.attrib, repr(subelem.text)
    return weather

def do_search(search):
    import StringIO
    from x84.bbs import echo, getch, getterminal
    disp_searching()
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


def chose_location(locations):
    from x84.bbs import getterminal, getsession, echo, Lightbar
    session, term = getsession(), getterminal()
    echo(u''.join((u'\r\n\r\n', term.clear_eol, term.normal,)))
    echo(u' '.join((term.yellow(u'ChOSE A'),
        term.bold_yellow('CitY'),
        term.yellow_reverse(': '),)))
    assert len(locations) > 0, (
            u'Cannot chose from empty list')
    if (session.user.get('expert', False) == True
            or 0 == term.number_of_colors):
        max_width = len('%d' % (len(locations),))
        for num, loc in enumerate(locations):
            echo(u' '.join((
                term.blue('u['),
                u'%*d' % (max_width, num),
                term.blue(u']'),
                term.bold(loc['city']), u',',
                term.bold(loc['state']), u'\r\n')))
            if 0 == num % (term.height - 1):
                echo(term.reverse('--MORE--'))
                if getch() is None:
                    break
                echo(u'\r\n')
        echo(' '.join((u'\r\n\r\n',
            term.bold_blue(u'['),
            term.bold_black(u'%d-%d' % (0, len(locations),)),
            term.bold_blue(u']'),
            term.reverse_blue(':'),)))
        idx = LineEditor.read(width=max_width)
        if idx is None or len(idx) == 0:
            return None
    else:
        fullheight = min(term.height - 8, len(locations))
        fullwidth = max(int(term.width * .8),
            min(term.width - 8, max([len(u'%(city)s, %(state)s' % loc)
                for loc in locations])))
        echo(u'\r\n' * fullheight)
        lightbar = Lightbar(height=fullheight,
                            width=fullwidth,
                            yloc=term.height - fullheight,
                            xloc=int((term.width / 2) - (fullwidth / 2)))
        lookup = dict([(loc['postal'], loc) for loc in locations])
        lightbar.update([(loc['postal'], (u'%(city)s, %(state)s' % loc))
            for loc in locations])
        lightbar.colors['border'] = term.yellow
        echo(lightbar.border())
        echo(lightbar.title(u''.join((
            term.yellow(u' -'), term.bold_white(u'-[ '),
            term.bold_yellow('CitY'),
            term.bold_white(u', '),
            term.bold_yellow('StAtE'),
            term.bold_white(u' ]-'), term.yellow(u'- '),))))
        echo(lightbar.footer(u''.join((
            term.bold_yellow(u' ( '),
            term.yellow_underline('Escape'),
            term.bold_white(u':'),
            term.yellow('EXit'),
            term.bold_yellow(u' ) '),))))
        lightbar.colors['highlight'] = term.yellow_reverse
        choice = lightbar.read()
        echo(lightbar.erase())
        return ((loc for loc in locations if choice == loc['postal']
            ).next() if choice is not None else choice)


def prompt_wfc(location):
    from x84.bbs import getterminal, echo, getch
    term = getterminal()
    echo(u''.join((u'\r\n\r\n', term.clear_eol,
        term.bold_yellow(u'diSPlAY'),
        term.yellow(u' WEAthER fORECASt fOR '),
        term.yellow_reverse('%(city)s, %(state)s' % location),
        term.bold_white(' ? '),
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


def main():
    from x84.bbs import getsession, getterminal, echo, LineEditor, getch
    from x84.bbs import Lightbar, Pager
    session, term = getsession(), getterminal()

    echo(u'\r\n\r\n' + term.clear_eol + term.normal)
    search = u''
    location = session.user.get('location', dict())
    while not 'postal' in location:
        if False == session.user.get('expert', False):
            disp_search_help()
        search = get_zipsearch(search)
        if search is None or 0 == len(search):
            return # exit
        locations = do_search(search)
        if 0 != len(locations):
            location = (locations.pop() if 1 == len(locations)
                    else chose_location(locations) or dict())

    if False == prompt_wfc(location):
        return
    forecast = do_weather(location.get('postal'))
    return
#    echo(term.move(4, 16) + term.clear_eol)
#
#    # convert forecast data into list, ordered sunday through monday
#    for key in forecast.keys():
#        fc[days.index(forecast[key]['DayCode'])] = forecast[key]
#        fc[days.index(forecast[key]['DayCode'])]['key'] = str(key)
#    # find today's weekday, and reorder list
#    usr_wkday = time.strftime('%A', time.strptime(today, '%m/%d/%Y'))
#    fc = fc[days.index(usr_wkday):] + fc[:days.index(usr_wkday)]
#    # add fake forecast named 'Moon Data'
#    fc.append({'DayCode': 'Moon Data'})
#
#    # forecast Week-day selection
#    lightbar_fc = Lightbar(height=10, width=11, yloc=9, xloc=6)
#    lightbar_fc.interactive = True
#    lightbar_fc.update(lightbar_fc.content + [
#        (entry['DayCode'], entry['DayCode']) for entry in fc])
#
#    # weather data window
#    pager = Pager(height=19, width=57, yloc=5, xloc=20)
#    pager.colors['border'] = term.white
#    title = (u''.join((current['City'],
#                       u', ',
#                       current['State'],) if 'State' in current
#                      else current['City']))
#
#    def refresh_windows():
#        # clear
#        echo(term.move(0, 0) + term.clear + term.normal)
#        echo(lightbar_fc.refresh() + term.normal)
#        echo(pager.refresh() + pager.border())
#        echo(pager.title(u''.join(
#            (term.red, u'-< ',
#             term.reverse, title,
#             term.normal, term.red,
#             u' >-',))))
#        echo(pager.footer(u''.join(
#            (term.red, u'-< ',
#             term.red_reverse, u'q:QUit, UP/dOWN: fORECASt',
#             term.normal, term.red,
#             u' >-',))))
#    refresh_windows()
#    #
#    # current conditions/forecast selector
#    #
#    txt, inp = u'', u''
#    while not lightbar_fc.quit:
#        if lightbar_fc.moved or session.poll_event('refresh'):
#            refresh_windows()
#            echo(pager.update(txt))
#        inp = getch(1)
#        lightbar_fc.process_keystroke(inp)
#        if lightbar_fc.moved:
#            echo(term.normal)
#            for index in range(0, len(fc)):
#                if fc[index]['DayCode'] == lightbar_fc.selection[0]:
#                    break
#            txt = u''
#            if index == 0:
#                c_temp = conv_t(current['Temperature'])
#                c_real = conv_t(current['RealFeel'])
#                c_wspeed = conv_s(current['WindSpeed'])
#                txt = u''.join(
#                    (u'Current conditions, Last updated ',
#                     current['Time'], u'\n\n',
#                     current['WeatherText'].capitalize(),
#                     u' and ', c_temp, temp(),
#                     u' (feels like ', c_real, temp(), u'), ',
#                     u'with winds of ', c_wspeed, speed(),
#                     u', travelling ', current['WindDirection'],
#                     u'. ', 'Visibility level is ',
#                     current['Visibility'], u' with humidity of ',
#                     current['Humidity'], '.\n\n',))
#
#            if index < len(lightbar_fc.content) - 1:
#                # Localization of forecast data
#                date = time.strftime(
#                    '%A, %b %d',
#                    time.strptime(fc[index]['key'], u'%m/%d/%Y'))
#                fc_high = conv_t((fc[index]['High_Temperature']))
#                fc_low = conv_t(fc[index]['Low_Temperature'])
#                fc_wspeed = conv_s(fc[index]['WindSpeed'])
#                fc_wgust = conv_s(fc[index]['WindGust'])
#                fc_rain = conv_m(fc[index]['Rain_Amount'])
#                fc_snow = conv_m(fc[index]['Snow_Amount'])
#
#                txt += u''.join(
#                    (u'Forecast for ', date, ':\n\n',
#                     fc[index]['TXT_Long'], ', ',
#                     u'high of ', fc_high, temp(),
#                     u' and low of ', fc_low, temp(),
#                     u'. ',))
#
#                txt += u''.join(
#                    ('Winds of ', fc_wspeed, speed(),
#                     u', travelling ', fc[index]['WindDirection'],
#                     u', with ', fc_wgust, speed(),
#                     u' gusts.',))
#
#                if float(fc_rain) > 0.0:
#                    pager.colors['border'] = term.blue
#                    txt += u''.join(
#                        (u' Rain precipitations of ',
#                         fc_rain, ' ', measure(), '.',))
#
#                if float(fc_snow) > 0.0:
#                    pager.colors['border'] = term.blue_bold
#                    txt += u''.join(
#                        (u' Snow accumulaitons of ',
#                         fc_snow, u' ', measure(), u'.'))
#                txt += u'\n\n'
#
#            elif index == (len(lightbar_fc.content) - 1):
#                for k in pom.keys():
#                    if pom[k]['text'] != '':
#                        txt += u''.join(
#                            (pom[k]['text'] + u' Moon: ',
#                             time.strftime(
#                                 '%A, %b %d', time.strptime(k, '%m/%d/%Y')),
#                             u'.\n\n',))
#
#            txt += u''.join((u'\n(c) ', current['Copyright'],))
#            echo(pager.update(txt))
#
##
##def start(name, attrs):
##    global cname, cattrs, lookup
##    cname, cattrs = name, attrs
##    if 'city' in cattrs.keys():
##        lookup.append(cattrs)
##
##
##def end(name):
##    global cname, cattrs
##    cname, cattrs = None, None
##
##
##def weather_chdata(data):
##    global cname, cattrs, cfdate, today
##    if cname == 'ObsDate' and data.strip():
##        # forecast date
##        cfdate = data.strip()
##        if not today:
##            today = data.strip()
##        return
##    if cname in current_keys and data.strip() and not cfdate:
##        # current weather
##        current[cname] = data.strip()
##
##    elif cname in fcast_keys and data.strip() and cfdate:
##        # forecasted
##        if not cfdate in forecast:
##            forecast[cfdate] = {}
##        forecast[cfdate][cname] = data.strip()
##
##    elif cname == 'Phase' and data.strip():
##        # phase of moon
##        pomdate = cattrs['date']
##        if not pomdate in pom:
##            pom[pomdate] = {}
##        pom[pomdate]['text'] = cattrs['text']
##        # data represents integer phase, 0=new, etc.
##        pom[pomdate]['phase'] = data.strip()
##
##
#def location_chdata(data):
#    global cname, cattrs, lookup
    # global 'state' & 'data' variables for SAX parsing
    #global cname, cattrs, cfdate
    #global current, forecast, pom, lookup, today
    # is location a US zipcode?
    #def isUS():
    #    return 5 == len(zipcode) and not False in \
    #        (ch.isdigit() for ch in zipcode)
#
#    # measurement converstions
#    def conv_t(f):
#        return (f if isUS()
#                else str(int((5.0 * float(int(f) - 32)) / 9)))
#
#    def conv_s(mph):
#        return (mph if isUS()
#                else str(int(float(mph) * 1.6)))
#
#    def conv_m(inch):
#        return (inch if isUS()
#                else str(int(float(inch) * 2.54)))
#
#    # measurement types
#    def temp():
#        return ('F' if isUS()
#                else 'C')
#
#    def speed():
#        return ('mph' if isUS()
#                else 'km/h')
#
#    def measure():
#        return 'inches' if isUS() else 'centimeters'
#


