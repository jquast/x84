"""
  Default logoff script for X/84, http://1984.ws
"""
TIMEOUT = 35
AUTOMSG_LENGTH = 40

import os
#pylint: disable=W0614
#        Unused import from wildcard import
from x84.bbs import *

def main():
    import time
    db = DBProxy('automsg')
    session = getsession()
    term = session.terminal
    expert = session.user.get('expert', False) \
        if session.user is not None else False
    session.activity = u'Logging Off!'
    prompt_msg = u'[spnG]: ' if expert is True \
        else u'%s:AY SOMEthiNG %s:REViOUS %s:EXt %s:Et thE fUCk Off !\b' \
        % (''.join((term.cyan_reverse, 's', term.normal, term.bold_black,)),
          ''.join((term.white_on_blue, 'p', term.normal, term.bold_black,)),
          ''.join((term.white_on_blue, 'n', term.normal, term.bold_black,)),
          ''.join((term.red_reverse, 'g', term.normal, term.bold_black,)),)
    prompt_say = u''.join \
        ((term.bold_blue, session.handle \
          if session.user is not None else u'PROlE', term.normal,
          u' sAYs ', term.cyan_reverse, u'WhAt: ', term.normal,))
    goodbye_msg = u''.join((term.black_bold, u'\r\n\r\n',
            u'back to the mundane world...', u'\r\n',))
    commit_msg = u'-- !  thANk YOU fOR YOUR CONtRibUtiON, bROthER  ! --'
    write_msg = u'bURNiNG tO ROM, PlEASE WAiT ...'
    newDb = ((time.time() -1984, u'B. b.', u'bEhAVE YOURSElVES ...'),)
    chk_next = ('n', 'N', term.KEY_DOWN, term.KEY_NPAGE,)
    chk_prev = ('p', 'P', term.KEY_UP, term.KEY_PPAGE,)
    chk_say  = ('s', 'S',)
    chk_bye  = ('g', 'G', None)
    nick = session.handle if session.handle is not None else 'anonymous'

    def refresh_prompt(msg):
        """Refresh automsg prompt using string msg"""
        echo (term.move (max(14, (term.height -6)),
                         max(6, (term.width /2) -(AUTOMSG_LENGTH /2))))
        echo (u''.join((term.normal, term.clear_eol)))
        echo (msg)

    def refresh_automsg(idx):
        """Refresh automsg database, create a fancy string like 'nick', ':msg',
        and '[n time ago]' of record idx, and return idx, which can differ if
        adjusted to bounds.
        """
        session.flush_event ('automsg')
        echo (term.move(max(12, (term.height/2)),
                        max(3, (term.width /2) -(AUTOMSG_LENGTH /2))))
        echo (u''.join((term.normal, term.clear_eol, term.bold_black,)))
        echo (u' ... ') # loading
        automsgs = sorted(db.values()) if len(db) else newDb
        idx = len(automsgs) -1 if idx < 0 \
            else 0 if idx > len(automsgs) -1 \
            else idx
        t, nick, msg = automsgs[idx]
        artnick = ''.join((term.blue_reverse, nick \
            .rjust(int(ini.CFG.get('nua', 'max_user'))),))
        artmsg = ''.join((term.cyan_reverse, '/', term.blue_reverse, '%d' % (idx,),
          term.normal, ': ', term.cyan_reverse, msg \
            .ljust(AUTOMSG_LENGTH),))
        artago = ''.join((term.blue_reverse,
          (u'%s ago' % (timeago(time.time() -t),)) \
              .ljust (AUTOMSG_LENGTH -len(Ansi(artmsg)))))
        # output & return new index
        echo (term.normal.join((artnick, artmsg, ' ', artago,)))
        return idx

    def refresh_all(idx=None):
        """
        refresh screen, database, and return database index
        """
        session.flush_event ('refresh')
        echo (term.move(0,0) + term.clear)
        showcp437 (os.path.join(os.path.dirname(__file__), 'art', '1984.asc'))
        idx = refresh_automsg (-1 if idx is None else idx)
        refresh_prompt (prompt_msg)
        return idx

    idx = refresh_all ()
    chk_events = ('input', 'automsg', 'refresh',)
    while True:
        event, data = session.read_event(chk_events, timeout=TIMEOUT)
        if (event, data) == (None, None):
            # timeout
            raise ConnectionTimeout, 'login prompt'
        if event == 'refresh':
            idx = refresh_all ()
        elif event == 'automsg':
            refresh_automsg (-1)
            echo (u'\a') # bel
        elif event == 'input':
            if data in chk_bye:
                echo (goodbye_msg)
                disconnect ()
            elif data in chk_next:
                idx = refresh_automsg(idx +1)
            elif data in chk_prev:
                idx = refresh_automsg(idx -1)
            elif data in chk_say:
                # new prompt: say something !
                refresh_prompt (prompt_say)
                #(y, x) = getpos(2)
                (y, x) = (None, None)
                if (None, None) != (y, x):
                    # illegal ? white_reverse ?
                    echo (term.cyan_reverse)
                    echo (u' ' * AUTOMSG_LENGTH)
                    echo (term.move (y, x))
                else:
                    echo ( u' '* AUTOMSG_LENGTH)
                    echo (u'\b'* AUTOMSG_LENGTH)
                msg = readline(AUTOMSG_LENGTH)
                if len(msg.strip()):
                    if (None,None) != (y, x):
                        echo (term.move (y, x))
                        echo (term.clear_bol)
                        echo (write_msg .rjust(AUTOMSG_LENGTH))
                    idx = len(db)
                    db[idx] = (time.time(), nick, msg.strip())
                    session.send_event ('automsg', True)
                    refresh_automsg (idx)
                    if (None,None) != (y, x):
                        echo (term.move (y, x))
                        echo (term.clear_bol)
                        echo (term.green_reverse)
                        echo (commit_msg .rjust(AUTOMSG_LENGTH))
                        getch (1.5) # for effect, LoL

                # display prompt
                refresh_prompt (prompt_msg)
