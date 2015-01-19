"""
fail2ban module for x/84.

To enable, add to default.ini::

    [fail2ban]
    enabled = yes

The following options are available, but not required:

- ``ip_blacklist``: space-separated list of IPs on permanent blacklist.
- ``ip_whitelist``: space-separated list of IPs to always allow.
- ``max_attempted_logins``: max no. of logins allowed for given time window
- ``max_attempted_logins_window``: the length (in seconds) of the time window
  for which logins will be tracked (sliding scale).
- ``initial_ban_length``: ban length (in seconds) when an IP is blacklisted.
- ``ban_increment_length``: amount of time (in seconds) to add to a ban on
  subsequent login attempts
"""

# std imports
import logging
import time

# globals
BANNED_IP_LIST, ATTEMPTED_LOGINS = dict(), dict()


def get_fail2ban_function():
    """
    Return a function used to ban aggressively-connecting clients.

    This is analogous to the 'fail2ban' utility, for example, telnet
    or ssh connect scanners.

    Returns a function which may be passed an IP address, returning True
    if the connection from address ``ip`` should be accepted.

    :return: function accepting ip address, returning boolean
    :rtype: callable
    """
    # local imports
    from x84.bbs import get_ini

    if not get_ini(section='fail2ban', key='enabled', getter='getboolean'):
        return lambda ip: True

    # configuration
    ip_blacklist = get_ini(section='fail2ban',
                           key='ip_blacklist',
                           split=True)

    ip_whitelist = get_ini(section='fail2ban',
                           key='ip_whitelist',
                           split=True)

    max_attempted_logins = get_ini(
        section='fail2ban',
        key='max_attempted_logins',
        getter='getint'
    ) or 3

    max_attempted_logins_window = get_ini(
        section='fail2ban',
        key='max_attempted_logins_window',
        getter='getint'
    ) or 30

    initial_ban_length = get_ini(
        section='fail2ban',
        key='initial_ban_length',
        getter='getint'
    ) or 360

    ban_increment_length = get_ini(
        section='fail2ban',
        key='ban_increment_length',
        getter='getint'
    ) or 360

    def wrapper(ip):
        """ Inner wrapper function. """
        log = logging.getLogger(__name__)

        # pylint: disable=W0602
        #         Using global for 'BANNED_IP_LIST' but no assignment is done
        global BANNED_IP_LIST, ATTEMPTED_LOGINS

        now = int(time.time())

        # check to see if IP is blacklisted
        if ip in ip_blacklist:
            log.debug('Blacklisted IP rejected: {ip}'.format(ip=ip))
            return False

        # check to see if IP is banned
        elif ip in BANNED_IP_LIST:
            # expired?
            if now > BANNED_IP_LIST[ip]:
                # expired ban; remove it
                del BANNED_IP_LIST[ip]
                ATTEMPTED_LOGINS[ip] = {
                    'attempts': 1,
                    'expiry': now + max_attempted_logins_window
                }
                log.debug('Banned IP expired: {ip}'.format(ip=ip))
            else:
                # increase the expiry and kick them out
                BANNED_IP_LIST[ip] += ban_increment_length
                log.debug('Banned IP rejected: {ip}'.format(ip=ip))
                return False

        # check num of attempts, ban if exceeded max
        elif ip in ATTEMPTED_LOGINS:
            if now > ATTEMPTED_LOGINS[ip]['expiry']:
                # window closed; start over
                record = ATTEMPTED_LOGINS[ip]
                record['attempts'] = 1
                record['expiry'] = now + max_attempted_logins_window
                ATTEMPTED_LOGINS[ip] = record
                log.debug('Attempt outside of expiry window')
            elif ATTEMPTED_LOGINS[ip]['attempts'] > max_attempted_logins:
                # max # of attempts reached
                del ATTEMPTED_LOGINS[ip]
                BANNED_IP_LIST[ip] = now + initial_ban_length
                log.warn('Exceeded maximum attempts; banning {ip}'
                         .format(ip=ip))
                return False
            else:
                # extend window
                record = ATTEMPTED_LOGINS[ip]
                record['attempts'] += 1
                record['expiry'] += max_attempted_logins_window
                ATTEMPTED_LOGINS[ip] = record
                log.debug('Window extended')

        # log attempted login
        elif ip not in ip_whitelist:
            log.debug('First attempted login for this window')
            ATTEMPTED_LOGINS[ip] = {
                'attempts': 1,
                'expiry': now + max_attempted_logins_window,
            }
        return True

    return wrapper
