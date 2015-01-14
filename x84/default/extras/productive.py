#!/usr/bin/env python
from __future__ import print_function
from datetime import datetime, timedelta

# measure and report productivity in sense
# of work-weeks and work-hours, productive
# hours, and rest hours.

# ... A reference to the movie 'Visioneers'.

msg_rest = (
    u'There are {0} minutes of rest remaining until work begins.'
).format

msg_productivity = (
    u'There are {0} minutes of productivity remaining this work-week.'
).format


# productive times by week and starting & ending hour
p_time = {
    0: {'h_start': 9, 'h_end': 18},
    1: {'h_start': 9, 'h_end': 18},
    2: {'h_start': 9, 'h_end': 18},
    3: {'h_start': 9, 'h_end': 18},
    4: {'h_start': 9, 'h_end': 18}
}

tgt = now = datetime.now()

# target countdown is always end of nearest work week
lastday = max(p_time)
lasthour = p_time[lastday]['h_end']


def productive(date):
    " Is the datetime `date' a productive time? "
    dt = date.timetuple()
    if (not dt.tm_wday in p_time
        or (dt.tm_hour < p_time[dt.tm_wday]['h_start'] or
            dt.tm_hour >= p_time[dt.tm_wday]['h_end'])):
        # not a productive time, enjoy your rest.
        return False
    return True


def rest(date):
    " Is the datetime `date' period for resting? "
    minutes = 0
    tgt = date
    dt = tgt.timetuple()
    while (not dt.tm_wday in p_time or (
            not dt.tm_hour == p_time[dt.tm_wday]['h_start'])):
        tgt += timedelta(minutes=1)
        dt = tgt.timetuple()
        minutes += 1
    return minutes


def remaining(date):
    " How much time remains until work? "
    tgt = date
    minutes = 0
    while not (tgt.timetuple().tm_wday == lastday and
               tgt.timetuple().tm_hour == lasthour):
        tgt += timedelta(minutes=1)
        if productive(tgt):
            minutes += 1
    return minutes


def main():
    """ Only called by x/84 bbs, https://github.com/jquast/x84 """
    from x84.bbs import echo
    now = datetime.now()
    echo(u'\r\n\r\n')
    if not productive(now):
        echo(msg_rest(rest(now)))
        echo(u'\r\n')
    echo(msg_productivity(remaining(now)))
    echo(u'\r\n')

if __name__ == '__main__':
    """ Cmd-line version """
    now = datetime.now()
    if not productive(now):
        print(msg_rest(rest(now)))
    print(msg_productivity(remaining(now)))
