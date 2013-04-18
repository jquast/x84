#!/usr/bin/env python

# measure and report productivity in sense
# of work-weeks and work-hours, productive
# hours, and rest hours.

# ... a reference to the movie 'Visioneers'
msg_rest = u'There are %s minutes of rest remaining until work begins.'
msg_productivity = u'There are %s minutes of productivity remaining ' \
                   u'this work-week.'
from datetime import *

# productive times by week and starting & ending hour
p_time = \
  {0: {'h_start':9, 'h_end':18},
   1: {'h_start':9, 'h_end':18},
   2: {'h_start':9, 'h_end':18},
   3: {'h_start':9, 'h_end':18},
   4: {'h_start':9, 'h_end':18}}

tgt = now = datetime.now()

# target count down is always end of nearest work week
lastday = max(p_time)
lasthour = p_time[lastday]['h_end']

def productive(date):
  dt = date.timetuple()
  return False if not dt.tm_wday in p_time \
    or (dt.tm_hour < p_time[dt.tm_wday]['h_start'] or \
        dt.tm_hour >= p_time[dt.tm_wday]['h_end']) \
  else \
    True

def rest(date):
  minutes = 0
  tgt = date
  dt = tgt.timetuple()
  while not dt.tm_wday in p_time \
  or (not dt.tm_hour == p_time[dt.tm_wday]['h_start']):
    tgt += timedelta(minutes=1)
    dt = tgt.timetuple()
    minutes += 1
  return minutes

def remaining(date):
  tgt = date
  minutes = 0
  while not (tgt.timetuple().tm_wday == lastday \
  and tgt.timetuple().tm_hour == lasthour):
    tgt += timedelta(minutes=1)
    if productive(tgt):
      minutes += 1
  return minutes

def main():
    from x84.bbs import echo
    now = datetime.now()
    echo(u'\r\n\r\n')
    if not productive(now):
      echo(msg_rest % (rest(now),))
      echo(u'\r\n')
    echo(msg_productivity % (remaining(now),))
    echo(u'\r\n')

if __name__ == '__main__':
  now = datetime.now()
  if not productive(now):
    print(msg_rest % (rest(now),))
  print(msg_productivity % (remaining(now),))
