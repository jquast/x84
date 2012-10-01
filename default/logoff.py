"""
  Default logoff script for X/84, http://1984.ws
"""
TIMEOUT = 35
AUTOMSG_LENGTH = 50

def main():
  import time
  db = DBSessionProxy('automsg')
  session = getsession()
  term = session.terminal
  expert = session.user.get('expert', False) \
      if session.user is not None else False
  is_sysop = session.user.is_sysop \
      if session.user is not None else False
  session.activity = 'Logging Off!'
  prompt_msg = '[spnG]: ' if expert is True \
      else '%s:AY SOMEthiNG %s:REViOUS %s:EXt %s:Et thE fUCk Off !\b' \
      % (''.join((term.cyan_reverse, 's', term.normal, term.bold_black,)),
        ''.join((term.white_on_blue, 'p', term.normal, term.bold_black,)),
        ''.join((term.white_on_blue, 'n', term.normal, term.bold_black,)),
        ''.join((term.red_reverse, 'g', term.normal, term.bold_black,)),)
  prompt_say = ''.join \
      ((term.bold_blue, session.handle \
        if session.user is not None else 'PROlE', term.normal,
        ' sAYs ', term.cyan_reverse, 'WhAt: ', term.normal,))
  goodbye_msg = ''.join((term.black_bold, '\r\n\r\n',
          'back to the mundane world...', '\r\n',))
  commit_msg = '-- !  thANk YOU fOR YOUR CONtRibUtiON, bROthER  ! --'
  newDb = ((time.time() -1984, 'B. b.', 'bEhAVE YOURSElVES ...'),)
  chk_next = ('n', 'N', term.KEY_DOWN, term.KEY_NPAGE,)
  chk_prev = ('p', 'P', term.KEY_UP, term.KEY_PPAGE,)
  chk_say  = ('s', 'S',)
  chk_bye  = ('g', 'G', None)
  nick = session.handle if session.handle is not None else 'anonymous'

  def refresh_prompt(msg):
    """Refresh automsg prompt using string msg"""
    echo (term.move (max(14, (term.height -6)),
                     max(6, (term.width /2) -(AUTOMSG_LENGTH /2) -8)))
    echo (''.join((term.normal, term.clear_eol)))
    echo (msg)

  def refresh_automsg(idx):
    """Refresh automsg database, create a fancy string like 'nick', ':msg',
    and '[n time ago]' of record idx, and return idx, which can differ if
    adjusted to bounds.
    """
    flushevent ('automsg')
    echo (term.move(max(12, (term.height/2)),
                    max(3, (term.width /2) -(AUTOMSG_LENGTH /2) -10)))
    echo (''.join((term.normal, term.clear_eol, term.bold_black,)))
    echo (' ... ') # loading
    automsgs = sorted(db.values()) if len(db) else newDb
    idx = len(automsgs) -1 if idx < 0 \
        else 0 if idx > len(automsgs) -1 \
        else idx
    t, nick, msg = automsgs[idx]
    artnick = ''.join((term.blue_reverse, nick \
        .rjust(int(ini.cfg.get('nua', 'max_user'))),))
    artmsg = ''.join((term.cyan_reverse, '/', term.blue_reverse, '%d' % (idx,),
      term.normal, ': ', term.cyan_reverse, msg \
        .ljust(AUTOMSG_LENGTH -10),))
    artago = ''.join((term.blue_reverse,
      ('%s ago' % (asctime(time.time() -t),)) \
          .ljust (AUTOMSG_LENGTH -ansilen(artmsg))))
    # output & return new index
    echo (term.normal.join((artnick, artmsg, ' ', artago,)))
    return idx

  def refresh_all(idx=None):
    """
    refresh screen, database, and return database index
    """
    flushevent ('refresh')
    echo (term.move(0,0) + term.clear)
    showfile ('art/1984.asc')
    idx = refresh_automsg (-1 if idx is None else idx)
    refresh_prompt (prompt_msg)
    return idx

  idx = refresh_all ()
  chk_events = ('input', 'automsg', 'refresh',)
  while True:
    event, data = readevent(events=chk_events, timeout=TIMEOUT)
    if (event, data) == (None, None):
      # timeout
      logger.info ('logoff/automsg timeout exceeded')
      echo (''.join((term.black_bold, '\r\n\r\n',
        'tiMEOUt: 1 dEMERit.', '\r\n',)))
      disconnect ()
    if event == 'refresh':
      idx = refresh_all ()
    elif event == 'automsg':
      refresh_automsg (-1)
      echo ('\a') # bel
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
        (y, x) = getpos()
        if (None,None) != (y, x):
          echo (term.white_reverse)
          echo (' ' * AUTOMSG_LENGTH)
          echo (term.move (y, x))
        msg = readline(AUTOMSG_LENGTH)
        if len(msg.strip()):
          if (None,None) != (y, x):
            echo (term.move (y, x))
            echo (term.clear_bol)
            echo ('bURNiNG tO ROM, PlEASE WAiT ...' .rjust(AUTOMSG_LENGTH))
          idx = len(db)
          db[idx] = (time.time(), nick, msg.strip())
          broadcastevent ('automsg', (nick, msg.strip(),))
          refresh_automsg (idx)
          if (None,None) != (y, x):
            echo (term.move (y, x))
            echo (term.clear_bol)
            echo (term.green_reverse)
            echo (commit_msg .rjust(AUTOMSG_LENGTH))
            getch (1.5) # for effect, LoL

        # display prompt
        refresh_prompt (prompt_msg)
