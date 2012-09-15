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
import urllib, cStringIO, gzip
import xml.parsers.expat
import time
deps = ['bbs']

weather_xmlurl = \
  'http://apple.accuweather.com/adcbin/apple/Apple_Weather_Data.asp'
  #?zipcode=%s'
location_xmlurl = \
  'http://apple.accuweather.com/adcbin/apple/Apple_find_city.asp'
  #?location=%s'

days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']

# xml keys for current conditions
current_keys = ( \
  'City', 'State', 'Time', 'Temperature', 'RealFeel', 'Humidity', \
  'WeatherText', 'WeatherIcon', 'WindSpeed', 'WindDirection', \
  'Visibility', 'Precip', 'DayCode', 'Pressure', 'GmtDiff', 'Tree',
  'Weed', 'Grass', 'Mold', 'UVIndex', 'Copyright', 'AirQuality',
  'AirQualityType' )

# xml keys for forecast data
fcast_keys = ( \
  'TXT_Short', 'TXT_Long', 'High_Temperature', 'Low_Temperature', \
  'Real_Feel_High', 'Real_Feel_Low', 'WindGust', 'MaxUV', \
  'Rain_Amount', 'Snow_Amount', 'Precip_Amount', 'TStorm_Prob', \
  'DayCode', 'WeatherIcon', 'WindSpeed', 'WindDirection', 'Max_UV' \
  )

def main(zipcode=''):
  session, term = getsession(), getterminal()
  user = session.user

  # global 'state' & 'data' variables for SAX parsing
  global cname, cattrs, cfdate
  global current, forecast, pom, lookup, today

  zipcode = None
  prompt_location = 'Enter US postal code, or nearest major international city'
  # is location a US zipcode?
  def isUS():
    return 5 == len(zipcode) and not False in \
        (ch.isdigit() for ch in zipcode)

  # measurement converstions
  def conv_t(f):
    return f if isUS() else str(int((5.0*float(int(f)-32))/9))
  def conv_s(mph):
    return mph if isUS() else str(int(float(mph)*1.6))
  def conv_m(inch):
    return inch if isUS() else str(int(float(inch)*2.54))

  # measurement types
  def temp():
    return 'F' if isUS() else 'C'
  def speed():
    return 'mph' if isUS() else 'km/h'
  def measure():
    return 'inches' if isUS() else 'centimeters'

  if not zipcode:
    echo (term.move (0,0) + term.clear + term.normal)
    # retrieve user's zipcode from db
    search = user.get('zipcode') \
      if user.get('zipcode') is not None \
      else ''

    # location finder
    while True:
      echo (term.normal + term.move(4, 8) + term.clear_eol)
      echo (prompt_location)
      echo (term.move (2, 26) + term.clear_eol + term.red_reverse)
      echo (' '*30)
      echo (term.move (2, 26))
      search = readline(30, search)
      if not search:
        break

      echo (term.normal + term.move(4, 8) + term.clear_eol)
      echo ('Searching ...')
      r = requests.get (location_xmlurl, params=(('location', search),))
      if 200 != r.status_code:
        echo (term.bold_red + term.move (8, 4) + term.clear_eol)
        echo ('Bad request, Enter city name')
        inkey (1.7)
        continue

      lookup = []
      # xml parser for location lookup
      lp = xml.parsers.expat.ParserCreate ()
      lp.StartElementHandler = start
      lp.EndElementHandler = end
      lp.CharacterDataHandler = location_chdata
      lp.Parse (r.content, True)

      if not len(lookup):
        echo (term.normal + term.move (4, 8) + term.clear_eol)
        echo ('No results found!')
        inkey (1.7)
        continue

      if len(lookup) == 1:
        zipcode = str(lookup[0]['postal'])
        break
      else:
        echo (term.normal + term.move (4, 8) + term.clear_eol)
        echo ('Chose a city')
        picker = [l['city'].encode('iso8859-1','replace')
              + ', ' + l['state'].encode('iso8859-1','replace') \
                  for l in lookup]
        # picker width: width always > 1/4 width, leaves 8 chars margin minimum
        mw=min(max(max([len(p) for p in picker]),term.width/4),term.width-8)
        llb = LightClass \
            (h=max(term.height-4,2), w=mw, y=5,
                x=(term.width -mw)/2)
        llb.interactive = True
        llb.partial = True
        llb.update (picker, refresh=False)
        llb.lowlight ()
        llb.interactive = False
        llb.title('-< CtRl-X: CANCEl >-')
        llb.refresh ()
        choice = llb.run ()
        llb.noborder ()
        llb.fill ()
        if llb.exit:
          continue
        zipcode = str(lookup[picker.index(llb.selection)]['postal'])
        break

  # cancellation/exit
  if not zipcode:
    return

  user.set ('zipcode', zipcode)
  s = 'postal code: '
  echo (term.move(2, 26) + term.clear_eol + term.red + s \
      + term.reverse + zipcode + (30-len(zipcode))*' ')

  cname, cattrs, cfdate = None, None, None
  current, forecast, pom, today = {}, {}, {}, ''
  # array becomes forecast data in order, today first
  fc = ['','','','','','','']
  echo (term.normal + term.move(4, 16))
  echo ('Retrieving weather data...')

  # retrieve weather data
  #fobj = cStringIO.StringIO(urllib.urlopen(weather_xmlurl +zipcode).read())
  #try: data = gzip.GzipFile(fileobj=fobj).read()
  #except: data = '<?' + fobj.read()
  r = requests.get (weather_xmlurl, params=(('zipcode', zipcode),))
  if 200 != r.status_code:
    return # log

  # parse xml weather data
  wp = xml.parsers.expat.ParserCreate ()
  wp.StartElementHandler = start
  wp.EndElementHandler = end
  wp.CharacterDataHandler = weather_chdata
  wp.Parse(r.content, True)

  echo (term.move(4, 16) + term.clear_eol)

  # convert forecast data into list, ordered sunday through monday
  for key in forecast.keys():
    fc[days.index(forecast[key]['DayCode'])] = forecast[key]
    fc[days.index(forecast[key]['DayCode'])]['key'] = str(key)
  # find today's weekday, and reorder list
  usr_wkday = time.strftime('%A', time.strptime(today, '%m/%d/%Y'))
  fc = fc[days.index(usr_wkday):] + fc[:days.index(usr_wkday)]
  # add fake forecast named 'Moon Data'
  fc.append ({'DayCode':'Moon Data'})

  # forecast Week-day selection
  flb = LightClass(h=10,w=11,y=9,x=6)
  flb.interactive = True
  for entry in fc:
    flb.add (str(entry['DayCode']))

  # weather data window
  pager = ParaClass(h=19, w=57, y=5, x=20, xpad=2, ypad=2)
  if current.has_key('State'):
    title = str(current['City']) + ', ' + str(current['State'])
  else: title = str(current['City'])

  def refresh_windows():
    # clear
    echo (term.move (0,0) + term.clear)
    flb.partial = True
    flb.lowlight ()
    flb.refresh ()
    pager.partial = True
    pager.lowlight ()
    pager.title (''.join((term.red, '-< ', term.reverse, title, term.normal,
      term.red, ' >-',)), align='top')
    pager.title (''.join((term.red, '-< ', term.reverse,
      'q:QUit, UP/dOWN: fORECASt', term.normal, term.red, ' >-',)),
      align='bottom')

  refresh_windows()
  #
  # current conditions/forecast selector
  #
  while not flb.exit:
    if not flb.moved and flb.lastkey == '\014':
      refresh_windows ()
      pager.update (str(txt))

    if flb.moved:
      echo (term.normal)
      for index in range(0, len(fc)):
        if fc[index]['DayCode'] == flb.selection: break
      txt = ''
      if index == 0:
        c_temp = conv_t(current['Temperature'])
        c_real = conv_t(current['RealFeel'])
        c_wspeed = conv_s(current['WindSpeed'])
        txt += 'Current conditions, Last updated ' + current['Time'] + '\n\n' \
            + current['WeatherText'].capitalize() \
            + ' and ' + c_temp + temp() \
            + ' (feels like ' + c_real + temp() \
            + '), with winds of ' + c_wspeed + speed() \
            + ', travelling ' + current['WindDirection'] + '. ' \
            + 'Visibility level is ' + current['Visibility'] \
            + ' with humidity of ' + current['Humidity'] \
            + '.\n\n'

      if index < len(flb.content) -1:
        # Localization of forecast data
        date = time.strftime('%A, %b %d', time.strptime(fc[index]['key'], '%m/%d/%Y'))
        fc_high = conv_t((fc[index]['High_Temperature']))
        fc_low = conv_t(fc[index]['Low_Temperature'])
        fc_wspeed = conv_s(fc[index]['WindSpeed'])
        fc_wgust = conv_s(fc[index]['WindGust'])
        fc_rain = conv_m(fc[index]['Rain_Amount'])
        fc_snow = conv_m(fc[index]['Snow_Amount'])

        txt += 'Forecast for ' + date + ':\n\n' \
            + fc[index]['TXT_Long']  \
            + ', high of ' + fc_high + temp() \
            + ' and low of ' + fc_low + temp() + '. '

        txt += 'Winds of ' + fc_wspeed + speed() \
          + ', travelling ' + fc[index]['WindDirection'] \
          + ', with ' + fc_wgust + speed() + ' gusts.'

        if float(fc_rain) > 0.0:
          txt += ' Rain precipitations of ' \
              + fc_rain + ' ' + measure() + '.'

        if float(fc_snow) > 0.0:
          txt += ' Snow accumulaitons of ' \
              + fc_snow + ' ' + measure() + '.'
        txt += '\n\n'

      elif index == len(flb.content) -1:
        for k in pom.keys():
          if pom[k]['text'] != '':
            txt += pom[k]['text'] + ' Moon: ' \
                + time.strftime('%A, %b %d', \
                  time.strptime(k, '%m/%d/%Y')) \
                + '.\n\n'

      txt += '\n(c) '+ str(current['Copyright'])

      pager.update (str(txt))

    flb.run ()

    if flb.exit: break

def start(name, attrs):
  global cname, cattrs
  cname, cattrs = name, attrs
  if 'city' in cattrs.keys():
    lookup.append (cattrs)

def end(name):
  global cname, cattrs
  cname, cattrs = None, None

def weather_chdata(data):
  global cname, cattrs, cfdate, today
  if cname == 'ObsDate' and data.strip():
    # forecast date
    cfdate = data.strip()
    if not today: today = data.strip()
    return
  if cname in current_keys and data.strip() and not cfdate:
    # current weather
    current[cname] = data.strip()

  elif cname in fcast_keys and data.strip() and cfdate:
    # forecasted
    if not forecast.has_key(cfdate):
      forecast[cfdate] = {}
    forecast[cfdate][cname] = data.strip()

  elif cname == 'Phase' and data.strip():
    # phase of moon
    pomdate = cattrs['date']
    if not pom.has_key(pomdate):
      pom[pomdate] = {}
    pom[pomdate]['text'] = cattrs['text']
    # data represents integer phase, 0=new, etc.
    pom[pomdate]['phase'] = data.strip()

def location_chdata(data):
  global cname, cattrs, lookup
