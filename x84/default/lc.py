"""
Last Callers script for x/84, http://github.com/jquast/x84
"""

import os
from x84.bbs import getterminal, echo, getch, list_users, get_user, ini
from x84.bbs import timeago, getsession, Ansi, Lightbar


def dummy_pager(last_callers):
    term = getterminal()
    prompt_msg = u'\r\n\r\n[c]ONtiNUE, [s]tOP, [n]ON-StOP  ?\b\b'
    nonstop = False
    if term.width > 71:
        echo(term.normal + u'\r\n')
        echo(u'\r\n'.join((line.rstrip().center(term.width).rstrip()
                          for line in open(
                              os.path.join(os.path.dirname(__file__),
                                           'art', 'lc.asc')))))
    else:
        echo(term.normal + '\r\n')
        echo('// ' + term.red('LASt CAllERS').center(term.width))
    echo(u'\r\n\r\n')
    for row in range(len(last_callers)):
        echo(Ansi(last_callers[row]).ljust(term.width / 2).center(term.width))
        echo(u'\r\n')
        if not nonstop and row > 0 and 0 == (row % (term.height - 2)):
            echo(prompt_msg)
            inp = getch()
            if inp in (u's', u'S', u'q', u'Q', term.KEY_EXIT):
                return
            if inp in ('n', u'N'):
                nonstop = True
    echo(u'\r\npress any key .. ')
    getch()
    return


def redraw(pager):
    term = getterminal()
    rstr = term.move(0, 0) + term.normal + term.clear
    for line in open(os.path.join(os.path.dirname(__file__), 'art', 'lc.asc')):
        rstr += line.center(term.width).rstrip() + '\r\n'
    rstr += pager.border()
    if len(pager.content) < pager.visible_height:
        rstr += pager.footer(u'%s-%s (q)uit %s-%s' % (
            term.bold_white, term.normal, term.bold_white, term.normal))
    else:
        rstr += pager.footer(u'%s-%s up%s/%sdown%s/%s(q)uit %s-%s' % (
            term.bold_white, term.normal, term.bold_red, term.normal,
            term.bold_red, term.normal, term.bold_white, term.normal))
    rstr += pager.refresh()
    return rstr


def get_pager(lcallers, lcalls):
    term = getterminal()
    width = 65
    height = term.height - 15
    yloc = 10
    xloc = max(3, int((float(term.width) / 2) - (float(width) / 2)))
    pager = Lightbar(height, width, yloc, xloc)
    pager.xpadding = 2
    pager.ypadding = 1
    pager.alignment = 'center'
    pager.colors['border'] = term.red
    pager.colors['highlight'] = term.yellow_reverse
    pager.update([(lcallers[n], txt,)
                  for (n, txt) in enumerate(lcalls.split('\n'))])
    return pager


def lc_retrieve():
    """
    Returns tuple of ([nicknames,] u'text'), where 'text' describes in Ansi
    color the last callers to the system, and 'nicknames' is simply a list
    of last callers (for lightbar selection key).
    """
    import time
    #term = getterminal()
    udb = dict()
    for handle in list_users():
        user = get_user(handle)
        udb[(user.lastcall, handle)] = (user.calls, user.location)
    padd_handle = (ini.CFG.getint('nua', 'max_user') + 2) * -1
    padd_origin = (ini.CFG.getint('nua', 'max_location') + 2) * -1
    rstr = u''
    nicks = []
    for ((tm_lc, handle), (nc, origin)) in (reversed(sorted(udb.items()))):
        rstr += '%-*s' % (padd_handle, handle)
        rstr += '%-*s' % (padd_origin, origin)
        rstr += timeago(time.time() - tm_lc)
        rstr += '\n'
        nicks.append(handle)
#            (term.bold_yellow(origin[:len(origin) / 2])
#                 + term.bold_yellow(origin[len(origin) / 2:])
#                 + u' ' * (max(1, padd_location - len(origin))) + u' ')
#        rstr += (term.bold_yellow(timeago(time.time() - tm_lc))
#                 + term.red(' ago  n') + term.bold_yellow('C')
#                 + term.red('/') + term.bold_red(str(nc)) + u'\n')
    return (nicks, rstr.rstrip())


def main():
    session, term = getsession(), getterminal()
    session.activity = u'Viewing last callers'
    dirty = True
    lcallers, lcalls_txt = lc_retrieve()
    if (session.env.get('TERM') == 'unknown'
            or term.number_of_colors == 0
            or term.height <= 20 or term.width <= 71 or
            session.user.get('expert', False)):
        dummy_pager(lcalls_txt.split(u'\n'))
        return
    while True:
        if (term.height <= 20 or term.width <= 71):
            # window became too small
            dummy_pager(lcalls_txt.split('\n'))
            return
        if dirty:
            pager = get_pager(lcallers, lcalls_txt)
            echo(redraw(pager))
            dirty = False
        inp = getch(1)
        if session.poll_event('refresh'):
            dirty = True
        if inp is not None:
            echo(pager.process_keystroke(inp))
            if pager.quit:
                break
