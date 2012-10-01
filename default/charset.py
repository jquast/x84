"""
This script helps the user select between cp437 and utf8 encoding.
"""
import textwrap
def main():
  session, term = getsession(), getterminal()
  user = session.user
  artfile = 'art/cp437_test.ans'
  choice_1 = 'utf8' # default
  choice_2 = 'cp437'
  choice_1txt = choice_1 + " (YES!)"
  choice_2txt = choice_2 + " (OldSChOOliN' iT)"
  enc_prompt = "Use %s encoding? Press left/right until artwork " \
      "looks best. Adjust your terminal encoding or font if " \
      "necessary. %s is preferred, otherwse only %s is supported. " \
      "Press return to accept selection." % (choice_1txt, choice_1,
          choice_2txt,)

  def refresh(enc):
    # set session encoding
    enc = choice_1 if enc is None else enc
    getsession().encoding = enc
    if enc == 'cp437':
      # ESC %@ goes back from UTF-8 to ISO 2022 in case UTF-8 had been entered
      # via ESC %G.
      echo ('\033%@')
      # ESC ) K or ESC ) U Sets character set G1 to codepage 437, for examble
      # linux vga console
      echo ('\033)K')
      echo ('\033)U')
    elif enc == 'utf8':
      # ESC %G activates UTF-8 with an unspecified implementation level from
      # ISO 2022 in a way that allows to go back to ISO 2022 again.
      echo ('\033%G')

    # clear & display art
    echo (term.move (0,0) + term.clear)
    showfile (artfile)
    echo (term.normal + '\r\n\r\n')
    echo ('\r\n'.join(textwrap.wrap(enc_prompt, term.width-3)) + '\r\n')

    # create left/right encoding selector
    state = LeftRightClass.LEFT if enc == choice_1 else LeftRightClass.RIGHT
    bar_width = max(8, (term.width/2) -10)
    lb = LeftRightClass ((5, term.height-1), state)
    lb.left_text  = choice_1txt.center(bar_width)
    lb.right_text = choice_2txt.center(bar_width)
    lb.interactive = True
    lb.laststate = lb.state
    lb.refresh ()
    return lb

  # start with preferred charset
  senc = session.encoding if user.get('charset', None) is None \
      else user.get('charset')
  lightbar = refresh (senc)

  toss = getch (0.5)
  while True:
    (ev, data) = readevent(('input','refresh',),
        int(ini.cfg.get('session','timeout')))
    if (ev, data) == (None, None):
      raise ConnectionTimeout ('timeout selecting character set')
    if ev == 'input':
      state = lightbar.run (data)
      if lightbar.exit:
        return
      elif state is not None:
        # return was pressed
        senc = choice_1 if state == LeftRightClass.LEFT else choice_2
        if lightbar.state != lightbar.laststate:
          lightbar = refresh (senc)
        user.set ('charset', senc)
        user.save ()
        echo ("\r\n\r\n'%s' is now your preferred charset.\r\n" % \
            (user.get('charset'),))
        return
      elif lightbar.state != lightbar.laststate:
        # lightbar was moved
        new_enc = choice_1 \
            if lightbar.state == LeftRightClass.LEFT else choice_2
        lightbar = refresh (new_enc)
    if ev == 'refresh' or lightbar.state != lightbar.laststate:
    # re-locate lightbar; re-display art & prompt
      lightbar = refresh(session.encoding)
      lightbar.state = lightbar.laststate
