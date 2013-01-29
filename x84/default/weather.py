"""
 (US) Weather retriever for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: weather.py,v 1.4 2008/05/26 07:26:02 dingo Exp $

 This modulde demonstrates extending prsv modules by using external resources.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

import requests
#import urllib, cStringIO, gzip
import xml.parsers.expat
import time
deps = ['bbs']
cname, cattrs, cfdate = None, None, None
lookup, current, forecast, pom, today = [], {}, {}, {}, ''

weather_xmlurl = (u'http://apple.accuweather.com/'
                  + 'adcbin/apple/Apple_Weather_Data.asp')  # ?zipcode=%s'
location_xmlurl = (u'http://apple.accuweather.com/'
                   + 'adcbin/apple/Apple_find_city.asp')  # ?location=%s'

days = ('Sunday', 'Monday',
        'Tuesday', 'Wednesday',
        'Thursday', 'Friday',
        'Saturday',)

# xml keys for current conditions
current_keys = (
    'City', 'State', 'Time', 'Temperature', 'RealFeel', 'Humidity',
    'WeatherText', 'WeatherIcon', 'WindSpeed', 'WindDirection',
    'Visibility', 'Precip', 'DayCode', 'Pressure', 'GmtDiff', 'Tree',
    'Weed', 'Grass', 'Mold', 'UVIndex', 'Copyright', 'AirQuality',
    'AirQualityType',)

# xml keys for forecast data
fcast_keys = (
    'TXT_Short', 'TXT_Long', 'High_Temperature', 'Low_Temperature',
    'Real_Feel_High', 'Real_Feel_Low', 'WindGust', 'MaxUV',
    'Rain_Amount', 'Snow_Amount', 'Precip_Amount', 'TStorm_Prob',
    'DayCode', 'WeatherIcon', 'WindSpeed', 'WindDirection', 'Max_UV',)


def main(zipcode=u''):
    from x84.bbs import getsession, getterminal, echo, LineEditor, getch
    from x84.bbs import Lightbar, Pager
    session, term = getsession(), getterminal()

    # global 'state' & 'data' variables for SAX parsing
    global cname, cattrs, cfdate
    global current, forecast, pom, lookup, today

    zipcode = None
    prompt_location = (u'ENtER US POStAl COdE, '
                       u'OR NEARESt MAjOR iNtERNAtiONAl CitY')

    # TODO: import maze's internationalisation code
    # is location a US zipcode?
    def isUS():
        return 5 == len(zipcode) and not False in \
            (ch.isdigit() for ch in zipcode)

    # measurement converstions
    def conv_t(f):
        return (f if isUS()
                else str(int((5.0 * float(int(f) - 32)) / 9)))

    def conv_s(mph):
        return (mph if isUS()
                else str(int(float(mph) * 1.6)))

    def conv_m(inch):
        return (inch if isUS()
                else str(int(float(inch) * 2.54)))

    # measurement types
    def temp():
        return ('F' if isUS()
                else 'C')

    def speed():
        return ('mph' if isUS()
                else 'km/h')

    def measure():
        return 'inches' if isUS() else 'centimeters'

    if not zipcode:
        echo(term.move(0, 0) + term.clear + term.normal)
        # retrieve user's zipcode from db
        search = session.user.get('zipcode', u'')

        # location finder
        while True:
            echo(term.normal + term.move(4, 8) + term.clear_eol)
            echo(prompt_location)
            echo(term.move(2, 26) + term.clear_eol + term.red_reverse)
            echo(u' ' * 30)
            echo(term.move(2, 26))
            search = LineEditor(width=30, content=search).read()
            if search is None or 0 == len(search):
                break

            echo(term.normal + term.move(4, 8) + term.clear_eol)
            echo(u'Searching ...')
            r = requests.get(location_xmlurl, params=(('location', search),))
            if 200 != r.status_code:
                echo(term.bold_red + term.move(8, 4) + term.clear_eol)
                echo('Bad request, Enter city name')
                getch(1.7)
                continue

            lookup = []
            # xml parser for location lookup
            lp = xml.parsers.expat.ParserCreate()
            lp.StartElementHandler = start
            lp.EndElementHandler = end
            lp.CharacterDataHandler = location_chdata
            lp.Parse(r.content, True)

            if not len(lookup):
                echo(term.normal + term.move(4, 8) + term.clear_eol)
                echo('No results found!')
                getch(1.7)
                continue

            if len(lookup) == 1:
                zipcode = str(lookup[0]['postal'])
                break
            else:
                echo(term.normal + term.move(4, 8) + term.clear_eol)
                echo(u'Chose a city')
                picker = ['%s, %s' % (
                    l['city'], l['state'],)
                    for l in lookup]
                # picker width: width always > 1/4 width,
                # leaves 8 chars margin minimum
                mw = min(max(max([len(p) for p in picker]),
                             term.width / 4), term.width - 8)
                llb = Lightbar(height=max(term.height - 5, 2),
                               width=mw,
                               yloc=5,
                               xloc=(term.width - mw) / 2)
                llb.update([(citystate, citystate) for citystate in picker])
                echo(llb.title('-< CtRl-X: CANCEl >-'))
                choice = llb.read()
                llb.noborder()
                llb.fill()
                if llb.exit:
                    continue
                zipcode = lookup[picker.index(choice)]['postal']
                break

    # cancellation/exit
    if not zipcode:
        print 'cancel'
        return

    session.user['zipcode'] = zipcode
    s = 'postal code: '
    echo(u''.join((term.move(2, 26),
                   term.clear_eol, term.red, s,
                   term.reverse, zipcode,
                   u' ' * (30 - len(zipcode)),)))

    # array becomes forecast data in order, today first
    fc = [u''] * 7
    echo(term.normal + term.move(4, 16))
    echo(u'Retrieving weather data...')

    # retrieve weather data
    #fobj = cStringIO.StringIO(urllib.urlopen(weather_xmlurl +zipcode).read())
    #try: data = gzip.GzipFile(fileobj=fobj).read()
    #except: data = '<?' + fobj.read()
    r = requests.get(weather_xmlurl, params=(('zipcode', zipcode),))
    if 200 != r.status_code:
        print r
        return  # log

    # parse xml weather data
    wp = xml.parsers.expat.ParserCreate()
    wp.StartElementHandler = start
    wp.EndElementHandler = end
    wp.CharacterDataHandler = weather_chdata
    print 'parse'
    wp.Parse(r.content, True)
    print 'done'

    echo(term.move(4, 16) + term.clear_eol)

    # convert forecast data into list, ordered sunday through monday
    for key in forecast.keys():
        fc[days.index(forecast[key]['DayCode'])] = forecast[key]
        fc[days.index(forecast[key]['DayCode'])]['key'] = str(key)
    # find today's weekday, and reorder list
    usr_wkday = time.strftime('%A', time.strptime(today, '%m/%d/%Y'))
    fc = fc[days.index(usr_wkday):] + fc[:days.index(usr_wkday)]
    # add fake forecast named 'Moon Data'
    fc.append({'DayCode': 'Moon Data'})

    # forecast Week-day selection
    flb = Lightbar(height=10, width=11, yloc=9, xloc=6)
    flb.interactive = True
    flb.update(flb.content + [(entry['DayCode'], entry['DayCode'])
                              for entry in fc])

    # weather data window
    pager = Pager(height=19, width=57, yloc=5, xloc=20)
    pager.colors['border'] = term.white
    title = (u''.join((current['City'],
                       u', ',
                       current['State'],) if 'State' in current
                      else current['City']))

    def refresh_windows():
        # clear
        echo(term.move(0, 0) + term.clear + term.normal)
        echo(flb.refresh() + term.normal)
        echo(pager.refresh() + pager.border())
        echo(pager.title(u''.join(
            (term.red, u'-< ',
             term.reverse, title,
             term.normal, term.red,
             u' >-',))))
        echo(pager.footer(u''.join(
            (term.red, u'-< ',
             term.red_reverse, u'q:QUit, UP/dOWN: fORECASt',
             term.normal, term.red,
             u' >-',))))
    refresh_windows()
    #
    # current conditions/forecast selector
    #
    txt, inp = u'', u''
    while not flb.quit:
        if flb.moved or session.poll_event('refresh'):
            refresh_windows()
            echo(pager.update(txt))
        inp = getch(1)
        flb.process_keystroke(inp)
        if flb.moved:
            echo(term.normal)
            for index in range(0, len(fc)):
                if fc[index]['DayCode'] == flb.selection[0]:
                    break
            txt = u''
            if index == 0:
                c_temp = conv_t(current['Temperature'])
                c_real = conv_t(current['RealFeel'])
                c_wspeed = conv_s(current['WindSpeed'])
                txt = u''.join(
                    (u'Current conditions, Last updated ',
                     current['Time'], u'\n\n',
                     current['WeatherText'].capitalize(),
                     u' and ', c_temp, temp(),
                     u' (feels like ', c_real, temp(), u'), ',
                     u'with winds of ', c_wspeed, speed(),
                     u', travelling ', current['WindDirection'],
                     u'. ', 'Visibility level is ',
                     current['Visibility'], u' with humidity of ',
                     current['Humidity'], '.\n\n',))

            if index < len(flb.content) - 1:
                # Localization of forecast data
                date = time.strftime(
                    '%A, %b %d',
                    time.strptime(fc[index]['key'], u'%m/%d/%Y'))
                fc_high = conv_t((fc[index]['High_Temperature']))
                fc_low = conv_t(fc[index]['Low_Temperature'])
                fc_wspeed = conv_s(fc[index]['WindSpeed'])
                fc_wgust = conv_s(fc[index]['WindGust'])
                fc_rain = conv_m(fc[index]['Rain_Amount'])
                fc_snow = conv_m(fc[index]['Snow_Amount'])

                txt += u''.join(
                    (u'Forecast for ', date, ':\n\n',
                     fc[index]['TXT_Long'], ', ',
                     u'high of ', fc_high, temp(),
                     u' and low of ', fc_low, temp(),
                     u'. ',))

                txt += u''.join(
                    ('Winds of ', fc_wspeed, speed(),
                     u', travelling ', fc[index]['WindDirection'],
                     u', with ', fc_wgust, speed(),
                     u' gusts.',))

                if float(fc_rain) > 0.0:
                    pager.colors['border'] = term.blue
                    txt += u''.join(
                        (u' Rain precipitations of ',
                         fc_rain, ' ', measure(), '.',))

                if float(fc_snow) > 0.0:
                    pager.colors['border'] = term.blue_bold
                    txt += u''.join(
                        (u' Snow accumulaitons of ',
                         fc_snow, u' ', measure(), u'.'))
                txt += u'\n\n'

            elif index == (len(flb.content) - 1):
                for k in pom.keys():
                    if pom[k]['text'] != '':
                        txt += u''.join(
                            (pom[k]['text'] + u' Moon: ',
                             time.strftime(
                                 '%A, %b %d', time.strptime(k, '%m/%d/%Y')),
                             u'.\n\n',))

            txt += u''.join((u'\n(c) ', current['Copyright'],))
            echo(pager.update(txt))


def start(name, attrs):
    global cname, cattrs, lookup
    cname, cattrs = name, attrs
    if 'city' in cattrs.keys():
        lookup.append(cattrs)


def end(name):
    global cname, cattrs
    cname, cattrs = None, None


def weather_chdata(data):
    global cname, cattrs, cfdate, today
    if cname == 'ObsDate' and data.strip():
        # forecast date
        cfdate = data.strip()
        if not today:
            today = data.strip()
        return
    if cname in current_keys and data.strip() and not cfdate:
        # current weather
        current[cname] = data.strip()

    elif cname in fcast_keys and data.strip() and cfdate:
        # forecasted
        if not cfdate in forecast:
            forecast[cfdate] = {}
        forecast[cfdate][cname] = data.strip()

    elif cname == 'Phase' and data.strip():
        # phase of moon
        pomdate = cattrs['date']
        if not pomdate in pom:
            pom[pomdate] = {}
        pom[pomdate]['text'] = cattrs['text']
        # data represents integer phase, 0=new, etc.
        pom[pomdate]['phase'] = data.strip()


def location_chdata(data):
    global cname, cattrs, lookup
