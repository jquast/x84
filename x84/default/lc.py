""" Last Callers script for x/84, http://github.com/jquast/x84 """
# this also allows viewing of '.plan' attribute string when set by user,
# or 'e'diting a user when executed by sysop -- gosub('profile', user)

def pak():
    from x84.bbs import echo, getch
    msg_pak = u'PRESS ANY kEY'
    echo(u'\r\n%s ... ' % (msg_pak,))
    getch()
    return


def view_plan(handle):
    from x84.bbs import getterminal, echo, Ansi, get_user
    term = getterminal()
    echo(u'\r\n\r\n')
    echo(Ansi(get_user(handle).get('.plan', u'No Plan.')).wrap(term.width))
    pak()


def dummy_pager(last_callers):
    from x84.bbs import getterminal, getsession, echo, getch, ini
    from x84.bbs import LineEditor, Ansi, list_users, get_user, gosub
    session, term = getsession, getterminal()
    msg_prompt = (
            u'\r\n\r\n%sONtiNUE, %stOP, %sON-StOP %siEW .PlAN%s ?\b\b' % (
                term.bold(u'[c]'),
                term.bold(u'[s]'),
                term.bold(u'n'),
                term.bold(u'[v]'),
                u' [e]dit USR' if (
                    'sysop' in session.user.groups) else u'',))
    msg_partial = u'PARtiAl MAtChES'
    msg_prompt_handle = u'ViEW .PlAN ::- ENtER hANdlE: '

    redraw()
    echo(u'\r\n\r\n')
    nonstop = False
    for row in range(len(last_callers)):
        echo(Ansi(last_callers[row]).ljust(term.width / 2).center(term.width))
        echo(u'\r\n')
        if ((not nonstop and row > 0 and 0 == (row % (term.height - 2)))
                or (row == len(last_callers) - 1)):
            echo(msg_prompt)
            inp = getch()
            if inp in (u's', u'S', u'q', u'Q', term.KEY_EXIT):
                return
            if inp in (u'v', u'V') or 'sysop' in session.user.groups and (
                    inp in (u'e', u'E')):
                echo(u'\r\n')
                echo(msg_prompt_handle)
                handle = LineEditor(ini.CFG.get('nua', 'max_user')).read()
                echo (u'\r\n\r\n')
                usrlist = list_users()
                if handle is None or 0 == len(handle.strip()):
                    continue
                handle = handle.strip()
                if handle.lower() in [nick.lower() for nick in list_users()]:
                    user = get_user((nick for nick in usrlist
                        if nick.lower() == handle.lower()).next())
                    if 'sysop' in session.user.groups and (
                            inp in (u'e', u'E')):
                        gosub('profile', user.handle)
                    else:
                        view_plan(user.handle)
                else:
                    misses = [nick for nick in usrlist.keys()
                        if nick.lower().startswith(handle[:1].lower())]
                    if len(misses) > 0:
                        echo(u'%s:\r\n\r\n%s\r\n' % (msg_partial,
                            Ansi(', '.join(misses)).wrap(term.width)))
                    continue
            if inp in ('n', u'N'):
                nonstop = True
    pak()

def refresh_opts(pager, handle):
    from x84.bbs import getsession, getterminal, get_user
    session, term = getsession(), getterminal()
    has_plan = 0 != len(
            get_user(handle).get('.plan', u'').strip() if handle else u'')
    decorate = lambda key, desc: u''.join((
        term.bold(u'('), term.red_underline(key,),
        term.bold(u')'), term.bold_red(desc.split()[0]),
        u' '.join(desc.split()[1:]),
        term.bold_red(u' -'),))
    return pager.footer(u''.join((
        term.bold_red(u'- '),
        decorate(u'Escape/q', 'Uit'),
        decorate(u'v','iEW .PLAN') if has_plan else u'',
        decorate(u'e','dit USR') if 'sysop' in session.user.groups else u'',
        )))


def get_pager(lcallers, lcalls):
    from x84.bbs import getterminal, Lightbar
    term = getterminal()
    width = min(60, term.width - 1)
    height = max(5, min(len(lcallers), term.height - 15))
    xloc = (term.width / 2) - (width / 2)
    yloc = term.height - (height + 1)
    pager = Lightbar(height, width, yloc, xloc)
    pager.glyphs['left-vert'] = u''
    pager.glyphs['right-vert'] = u''
    pager.xpadding = 2
    pager.ypadding = 1
    pager.alignment = 'center'
    pager.colors['border'] = term.yellow
    pager.colors['highlight'] = term.yellow_reverse
    pager.update([(lcallers[n], txt,)
                  for (n, txt) in enumerate(lcalls.split('\n'))])
    return pager


def redraw(pager=None):
    from x84.bbs import getterminal
    import os
    term = getterminal()
    rstr = u'\r\n\r\n'
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'lc.asc')
    if os.path.exists(artfile):
        rstr += u'\r\n'.join([
            line.rstrip()[:term.width].center(term.width)
            for line in open(artfile)])
        rstr += u'\r\n\r\n'
    rstr += term.bold_red_underline(u'// ')
    rstr += term.red('LASt CAllERS'.center(term.width - 3))
    rstr += u'\r\n\r\n'
    if pager is not None:
        rstr += u'\r\n' * pager.height + pager.border() + pager.refresh()
    return rstr

def lc_retrieve():
    """
    Returns tuple of ([nicknames,] u'text'), where 'text' describes in Ansi
    color the last callers to the system, and 'nicknames' is simply a list
    of last callers (for lightbar selection key).
    """
    from x84.bbs import list_users, get_user, ini, timeago
    import time
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
    return (nicks, rstr.rstrip())


def main():
    from x84.bbs import getsession, getterminal, echo, getch, gosub
    session, term = getsession(), getterminal()
    session.activity = u'Viewing last callers'
    lcallers, lcalls_txt = lc_retrieve()
    pager = None
    dirty = True
    ropts = u''
    handle = None
    if (0 == term.number_of_colors
            or session.user.get('expert', False)):
        dummy_pager(lcalls_txt.split('\n'))
        return
    while pager is None or not pager.quit:
        if dirty or pager is None or session.poll_event('refresh'):
            pager = get_pager(lcallers, lcalls_txt)
            echo(redraw(pager))
            ropts = refresh_opts(pager, handle)
            echo(ropts)
        sel = pager.selection[0]
        if sel != handle or dirty:
            handle = sel
            echo(refresh_opts(pager, handle))
            echo(pager.pos(pager.yloc + (pager.height - 1)))
            dirty = False
        if session.poll_event('refresh'):
            dirty = True
            continue
        inp = getch(1)
        if inp is not None:
            if inp in (u'v', u'V'):
                view_plan(handle)
                dirty = True
            elif inp in (u'e', u'E') and 'sysop' in session.user.groups:
                gosub('profile', handle)
                dirty = True
            else:
                echo(pager.process_keystroke(inp))
