"""
Last Callers script for x/84, http://github.com/jquast/x84
"""

def dummy_pager(last_callers):
    session, term = getsession(), getterminal()
    prompt_msg = u'\r\n[c]ontinue, [s]top, [n]on-stop  ?\b\b'
    session.activity = u'Viewing last callers'
    nonstop = False
    echo (term.normal + '\r\n\r\n')
    if term.width > 71:
        echo ('\r\n'.join((line.rstrip().center(term.width).rstrip()
            for line in fopen('default/art/lc.asc', 'r'))))
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
    rstr = term.move(0, 0) + term.normal + term.clear
    for line in fopen('default/art/lc.asc', 'r'):
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
    width = 67
    height = term.height - 10
    yloc = 10
    xloc = max(3, int((float(term.width) / 2) - (float(width) / 2)))
    pager = Pager(height, width, yloc, xloc)
    pager.xpadding = 2
    pager.ypadding = 1
    pager.colors['border'] = term.red
    pager.update (lcalls)
    return pager

def lc_retrieve():
    rstr = u''
    udb = dict ()
    for handle in list_users():
        user = get_user(handle)
        udb[(user.lastcall, handle)] = (user.calls, user.location)
    padd_handle = ini.CFG.getint('nua', 'max_user') + 1
    padd_loc = ini.CFG.getint('nua', 'max_location') + 1
    padd_lcall = 12
    padd_ncalls = 13
    for ((lcall, handle), (ncalls, location)) in (
            reversed(sorted(udb.items()))):
        rstr += ( handle.ljust(padd_handle)
                + location.ljust(padd_loc)
                + ('%s ago' % (timeago(lcall),)).rjust (padd_lcall)
                + ('   Calls: %s' % (ncalls,)).ljust (padd_ncalls)
                + '\n')
    return rstr.rstrip()


def main(record_only=False):
    session, term = getsession(), getterminal()
    session.activity = u'Viewing last callers'

    lcalls_txt = lc_retrieve ()
    if ((session.env.get('TERM') == 'unknown' or term.number_of_colors == 0
        or term.height <= 22 or term.width <= 71
        or session.user.get('expert', False))):
            return dummy_pager(lcalls_txt.split('\n'))

    dirty = True
    while True:
        if dirty:
            pager = get_pager(lcalls_txt)
            echo (redraw(pager))
            dirty = False
        inp = getch(1)
        if inp is not None:
            echo (pager.process_keystroke (inp))
        if pager.quit == True:
            break
        if pollevent('refresh'):
            dirty = True
