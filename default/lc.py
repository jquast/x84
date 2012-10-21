"""
Last Callers script for X/84 BBS, http://1984.ws

When the first argument, 'record_only' is set to ``True``, only log the call
and do not display the window pager.
"""

def dummy_pager(last_callers):
    prompt_msg = '\r\n[c]ontinue, [s]top, [n]on-stop?'
    # dummy pager for dummy terminals ..
    session, term = getsession(), getterminal()
    session.activity = u'Viewing last callers'
    nonstop = False
    for row in len(last_callers):
        if nonstop == False and 0 == row % (term.height-1):
            echo (prompt_msg)
            inp = getch()
            if inp in (u's', u'S', u'q', u'Q', term.KEY_EXIT):
                return
            if inp in ('n', u'N'):
                nonstop = True
    return

def main(record_only=False):
    session, term = getsession(), getterminal()
    session.activity = u'Viewing last callers'

    def lc_retrieve():
        # open the database,
        udb = DBProxy('lastcallers')
        # always re-calculate the full call log :-) expensive ..
        for user in listusers():
            udb[user.handle] = user.lastcall
        lc_inorder = (reversed(sorted([(v,k)
                for (k,v) in udb.iteritems()
                if k is not None and finduser(k) is not None])))
        rstr = u''
        padd_handle = ini.CFG.getint('nua','max_user') +1
        padd_origin = ini.CFG.getint('nua','max_origin') +1
        padd_timeago = 12
        padd_ncalls = 13
        for (lcall, handle) in lc_inorder:
            user = getuser(handle)
            rstr += (handle.ljust(padd_handle) +
                    user.location.ljust(padd_origin) +
                    ('%s ago' % (timeago(lcall),)).rjust (padd_timeago) +
                    ('   Calls: %s' % (user.calls,)).ljust (padd_ncalls) +
                    '\n')
        return rstr.rstrip()

    def get_pager(lc):
        pager = Pager(height=min(term.height - 20, 4), width=67,
                xloc=5, yloc=14)
        pager.xpadding = 2
        pager.ypadding = 1
        pager.colors['border'] = term.red
        pager.update (lc)
        return pager

    def redraw(pager):
        rstr = u''
        rstr += term.move(0, 0) + term.normal + term.clear
        rstr += showcp437 ('art/lc.asc')
        footer = ('%s-%s (q)uit %s-%s' % (
            term.bold_white, term.normal,
            term.bold_white, term.normal)
            if len(pager.content) < pager._visible_height else
            '%s-%s up%s/%sdown%s/%s(q)uit %s-%s' % (
                term.bold_white, term.normal, term.bold_red, term.normal,
                term.bold_red, term.normal, term.bold_white, term.normal))
        rstr += pager.border ()
        rstr += pager.footer (footer)
        rstr += pager.refresh ()
        return rstr

    lcalls_txt = lc_retrieve ()
    dirty = True
    while True:
        if (session.env.get('TERM') == 'unknown' or term.number_of_colors == 0
                or term.height < 20 or term.width < 70):
            return dummy_pager(lcalls_txt)
        if None != readevent('refresh', timeout=0):
            dirty = True
        if dirty:
            pager = get_pager(lcalls_txt)
            echo (redraw(pager))
            dirty = False
        inp = getch()
        echo (pager.process_keystroke (inp))
        if pager.quit == True:
            break
