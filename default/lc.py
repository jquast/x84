"""
Last Callers script for x/84, http://github.com/jquast/x84
"""

from bbs import *

def dummy_pager(last_callers):
    term = getterminal()
    prompt_msg = u'\r\n[c]ontinue, [s]top, [n]on-stop  ?\b\b'
    nonstop = False
    echo (term.normal + '\r\n\r\n')
    if term.width > 71:
        echo ('\r\n'.join((line.rstrip().center(term.width).rstrip()
            for line in open('default/art/lc.asc'))))
    echo (term.normal + '\r\n\r\n')
    for row in range(len(last_callers)):
        echo (last_callers[row].rstrip() + '\r\n')
        if not nonstop and row > 0 and 0 == (row % (term.height-1)):
            echo (prompt_msg)
            inp = getch()
            if inp in (u's', u'S', u'q', u'Q', term.KEY_EXIT):
                return
            if inp in ('n', u'N'):
                nonstop = True
    echo ('\r\npress any key .. ')
    getch ()
    return

def redraw(pager):
    term = getterminal()
    rstr = term.move(0, 0) + term.normal + term.clear
    for line in open('default/art/lc.asc'):
        rstr += line.center(term.width).rstrip() + '\r\n'
    rstr += pager.border ()
    if len(pager.content) < pager._visible_height:
        rstr += pager.footer ('%s-%s (q)uit %s-%s' % (
            term.bold_white, term.normal, term.bold_white, term.normal))
    else:
        rstr += pager.footer ('%s-%s up%s/%sdown%s/%s(q)uit %s-%s' % (
            term.bold_white, term.normal, term.bold_red, term.normal,
            term.bold_red, term.normal, term.bold_white, term.normal))
    rstr += pager.refresh ()
    return rstr

def get_pager(lcalls):
    term = getterminal()
    width = 69
    height = term.height - 15
    yloc = 10
    xloc = max(3, int((float(term.width) / 2) - (float(width) / 2)))
    pager = Pager(height, width, yloc, xloc)
    pager.xpadding = 2
    pager.ypadding = 1
    pager.colors['border'] = term.red
    pager.update (lcalls)
    return pager

def lc_retrieve():
    term = getterminal()
    udb = dict ()
    for handle in list_users():
        user = get_user(handle)
        udb[(user.lastcall, handle)] = (user.calls, user.location)
    padd_handle = ini.CFG.getint('nua', 'max_user')
    padd_location = ini.CFG.getint('nua', 'max_location')
    rstr = u''
    for ((tm_lc, handle), (nc, origin)) in (reversed(sorted(udb.items()))):
        rstr += ( term.bright_red(handle[:len(handle) / 3])
                + term.bright_black(handle[len(handle) / 3:])
                + term.dim_yellow('.' * (max(1, padd_handle - len(handle))))
                + u' ')
        rstr += ( term.bright_yellow(origin[:len(origin) / 2])
                + term.bright_yellow(origin[len(origin) / 2:])
                + term.dim_red('.' * (max(1, padd_location - len(origin))))
                + u' ')
        rstr += ( term.bright_yellow(timeago(tm_lc))
                + term.red(' ago;     n') + term.bright_yellow('C')
                + term.red('alls: ') + term.bright_red(str(nc))
                + u'\n')
    return rstr.rstrip()


def main(record_only=False):
    session, term = getsession(), getterminal()
    session.activity = u'Viewing last callers'
    dirty = True
    lcalls_txt = lc_retrieve ()
    if (session.env.get('TERM') == 'unknown'
            or term.number_of_colors == 0
            or term.height <= 20 or term.width <= 72 or
            session.user.get('expert', False)):
        dummy_pager (lcalls_txt.split('\n'))
        return
    while True:
        if (term.height <= 20 or term.width <= 72):
            # window became too small
            dummy_pager (lcalls_txt.split('\n'))
            return
        if dirty:
            pager = get_pager(lcalls_txt)
            echo (redraw(pager))
            dirty = False
        inp = getch(1)
        if pollevent('refresh'):
            dirty = True
        if inp is not None:
            echo (pager.process_keystroke (inp))
            if pager.quit == True:
                break
