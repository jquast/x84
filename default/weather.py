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

import urllib, cStringIO, gzip, xml.parsers.expat, time
from time import strftime, gmtime, mktime
deps = ['bbs']

weather_xmlurl = \
  'http://apple.accuweather.com/adcbin/apple/Apple_Weather_Data.asp?zipcode='

location_xmlurl = \
  'http://apple.accuweather.com/adcbin/apple/Apple_find_city.asp?location='

days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']

# xml keys for current conditions
current_keys = [ \
  'City', 'State', 'Time', 'Temperature', 'RealFeel', 'Humidity', \
  'WeatherText', 'WeatherIcon', 'WindSpeed', 'WindDirection', \
  'Visibility', 'Precip', 'DayCode', 'Pressure', 'GmtDiff', 'Tree',
  'Weed', 'Grass', 'Mold', 'UVIndex', 'Copyright', 'AirQuality',
  'AirQualityType' \
  ]

# xml keys for forecast data
fcast_keys = [ \
  'TXT_Short', 'TXT_Long', 'High_Temperature', 'Low_Temperature', \
  'Real_Feel_High', 'Real_Feel_Low', 'WindGust', 'MaxUV', \
  'Rain_Amount', 'Snow_Amount', 'Precip_Amount', 'TStorm_Prob', \
  'DayCode', 'WeatherIcon', 'WindSpeed', 'WindDirection', 'Max_UV' \
  ]

def main(zipcode=''):
  # global 'state' variables
  global cname, cattrs, cfdate
  # global 'data' variables
  global current, forecast, pom, lookup, today

  # is location a US zipcode?
  def iUS():
    if len(zipcode) == 5:
      for n in zipcode:
        if not isdigit(ord(n)): return
      return True

  # measurement converstions
  def conv_t(f):
    if iUS(): return f
    return str(int((5.0*float(int(f)-32))/9))
  def conv_s(mph):
    if iUS(): return mph
    return str(int(float(mph)*1.6))
  def conv_m(inch):
    if iUS(): return inch
    return str(int(float(inch)*2.54))

  # measurement types
  def temp():
    if iUS(): return 'F'
    return 'C'
  def speed():
    if iUS(): return 'mph'
    return 'km/h'
  def measure():
    if iUS(): return 'inches'
    return 'centimeters'

  echo (cls() + color() + cursor_show())

  if not zipcode:
    # retrieve user's zipcode from db
    search = getsession().getuser().zipcode \
      if hasattr(getsession().getuser(), 'zipcode') \
      else ''

    # location finder
    while True:
      echo (color() + pos(8,4) + cl() + 'Enter US postal code, or nearest major international city')
      echo (pos(26,2) + cl() + color(RED) + attr(INVERSE) + ' '*30 + pos(26,2))
      search = readline(30, search)
      if not search:
        break

      echo (color() + pos(16,4) + cl() + 'Verifying/Searching...')
      oflush ()

      fobj = cStringIO.StringIO(urllib.urlopen(location_xmlurl+search).read())
      try: data = trim(gzip.GzipFile(fileobj=fobj).read())
      except: data = trim('<?' + fobj.read())
      if 'Bad Request' in data:
        echo (color() + pos(16,4) + cl() + 'Bad request, Enter city only!')
        inkey (1.7)
        continue

      # global variable modified by expat parser (XXX lock issue)
      lookup = []
      # xml parser for location lookup
      lp = xml.parsers.expat.ParserCreate ()
      lp.StartElementHandler = start
      lp.EndElementHandler = end
      lp.CharacterDataHandler = location_chdata
      try:
        lp.Parse (data, True)
      except:
        type, value, tb = sys.exc_info ()
        print handle() + ' weather: Error in parse: ' + str(traceback.format_exception_only(type, value))
        print 'data:'
        print repr(data)

      if not len(lookup):
        echo (color() + pos(16,4) + cl() + 'No results found!')
        inkey (1.7)
        continue
      if len(lookup) == 1:
        zipcode = str(lookup[0]['postal'])
        break
      else:
        echo (color() + pos(16,4) + cl() + 'Chose a city')
        picker = []
        for l in lookup:
          picker.append (stoascii(l['city']) + ', ' + stoascii(l['state']))

        # picker width: width always > 1/4 width, leaves 8 chars margin minimum
        mw=min(max(maxwidth(picker),getsession().width/4),getsession().width-8)
        llb = LightClass \
            (h=max(getsession().height-4,2), w=mw, y=5,
                x=(getsession().width -mw)/2)
        llb.interactive = True
        llb.update (picker, refresh=False)
        llb.lowlight (partial=True)
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

  getsession().getuser().set ('zipcode', zipcode)
  s = 'postal code: '
  echo (pos(26,2) + cl() + color(RED) + s \
    + attr(INVERSE) + zipcode + (30-len(zipcode))*' ')

  # global variables modified by expat parser (XXX lock issue)
  cname, cattrs, cfdate = None, None, None
  current, forecast, pom, today = {}, {}, {}, ''

  # array becomes forecast data in order, today first
  fc = ['','','','','','','']

  echo (color() + pos(16,4) + 'Retrieving weather data...')
  oflush ()

  # retrieve weather data
  fobj = cStringIO.StringIO(urllib.urlopen(weather_xmlurl +zipcode).read())
  try: data = gzip.GzipFile(fileobj=fobj).read()
  except: data = '<?' + fobj.read()

  # parse xml weather data
  wp = xml.parsers.expat.ParserCreate ()
  wp.StartElementHandler = start
  wp.EndElementHandler = end
  wp.CharacterDataHandler = weather_chdata
  wp.Parse(data, True)

  echo (pos(16, 4) + cl() + cursor_hide())

  # convert forecast data into list, ordered sunday through monday
  for key in forecast.keys():
    fc[days.index(forecast[key]['DayCode'])] = forecast[key]
    fc[days.index(forecast[key]['DayCode'])]['key'] = str(key)
  # find today's weekday, and reorder list
  usr_wkday = strftime('%A', time.strptime(today, '%m/%d/%Y'))
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
    echo (cls() + color() + cursor_show())
    flb.lowlight (partial=True)
    flb.refresh ()
    pager.lowlight (partial=True)
    pager.title (color(RED) + '-< ' + attr(INVERSE) + title + color() + color(RED) + ' >-')
    pager.title (color(RED) + '-< ' + attr(INVERSE) + 'q:QUit, UP/dOWN: fORECASt' + color() + color(RED) + ' >-', align='bottom')

  refresh_windows()
  #
  # current conditions/forecast selector
  #
  while not flb.exit:
    if not flb.moved and flb.lastkey == '\014':
      refresh_windows ()
      pager.update (str(txt))
    if flb.moved:
      echo (color())

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
        date = strftime('%A, %b %d', time.strptime(fc[index]['key'], '%m/%d/%Y'))
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
                + strftime('%A, %b %d', \
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
  if cname == 'ObsDate' and trim(data):
    # forecast date
    cfdate = trim(data)
    if not today: today = trim(data)
    return
  if cname in current_keys and trim(data) and not cfdate:
    # current weather
    current[cname] = trim(data)

  elif cname in fcast_keys and trim(data) and cfdate:
    # forecasted
    if not forecast.has_key(cfdate):
      forecast[cfdate] = {}
    forecast[cfdate][cname] = trim(data)

  elif cname == 'Phase' and trim(data):
    # phase of moon
    pomdate = cattrs['date']
    if not pom.has_key(pomdate):
      pom[pomdate] = {}
    pom[pomdate]['text'] = cattrs['text']
    # data represents integer phase, 0=new, etc.
    pom[pomdate]['phase'] = trim(data)

def location_chdata(data):
  global cname, cattrs, lookup
