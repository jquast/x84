from bbs import *
from ui.ansiwin import *
from ui.lightwin import *
from ui.pager import *
from strutils import *
from usercfg import *

choices = ['black','green','brown','purple','red','white','blue','yellow']
ccodes = [
  bcolor(BLACK)+color(GREY), bcolor(GREEN)+color(BLACK),
  bcolor(BROWN)+color(BLACK), bcolor(PURPLE)+color(BLACK),
  bcolor(RED)+color(BLACK), bcolor(GREY)+color(BLACK),
  bcolor(BLUE)+color(BLACK), bcolor(BROWN)+color(*YELLOW) ]

length = 5
tries = 11

def colorof (choice):
  return ccodes[choices.index(choice)]

def get_code():
  " return random combination "
  c = []
  for n in range(0, length):
    c.append (random.choice(choices))
    readkey (.01)
  return c

def pincode (set):
  " return combination of pin codes "
  c = []
  for lb in set:
    c.append (lb.selection)
  return c

def create_pins():
  " return array of lightbar objects that represent pin codes "
  set = []
  h, w, y = 3, 9, 1
  for n in range(0, length):
    x = (w*n)+7
    set.append (lightclass(ansiwin(h, w, y, x)))
    set[n].update (choices)
    set[n].bcolor = colorof(choices[0])
    set[n].refresh ()
    set[n].interactive = True
  return set

def shift_pinset(set):
  " shift pins down "
  for n in range(0, length):
    set[n].ans.y += 2
    set[n].refresh ()

def pick_lock(set, lock):
  " interactive user UI for lock picking "
  set[lock].ans.highlight (partial=True)
  # read key in last else
  key = None
  while True:
    if key in ['q','\030']:
      return -1, None
    elif key in [KEY.LEFT,'h'] and lock > 0:
      set[lock].ans.noborder ()
      lock -=1
      set[lock].ans.highlight (partial=True)
    elif key in [KEY.RIGHT,'l'] and lock < len(set) -1:
      set[lock].ans.noborder ()
      lock +=1
      set[lock].ans.highlight (partial=True)
    elif key == KEY.ENTER:
      set[lock].ans.noborder ()
      return lock, set
    else:
      set[lock].run ()
      key = set[lock].lastkey
      if set[lock].moved:
        set[lock].bcolor = colorof(set[lock].selection)
        set[lock].refresh ()
      continue
    # last action was movement, read key in next else
    key = None

def check_match(attempt, answer):
  " logical matching of tumblers and gears "
  # tumblers are matches in wrong position
  # gears are matches in correct position
  tumblers, gears = 0, 0

  # placeholders for matches
  match_tumblers, match_gears = [], []
  for n in range(0, len(attempt)):
    match_tumblers.append (False)
    match_gears.append (False)

  # find exact matches (gears)
  for n in range(0, len(attempt)):
    if attempt[n] == answer[n]:
      match_gears[n] = True
      gears += 1

  # find matches in wrong position (tumblers)
  for n in range(0, len(attempt)):
    if match_gears[n]: continue
    for i in range(0, len(attempt)):
      if match_gears[i] or match_tumblers[i]: continue
      if attempt[n] == answer[i]:
        tumblers += 1
        match_tumblers[i] = True
        break

  return tumblers, gears

def attempt_break (set, answer):
  " set UI for breakin attempt, return True if sucessful"
  tumblers, gears = check_match(pincode(set), answer)

  # set pegs
  echo (pos(set[len(set)-1].ans.x +9, set[len(set)-1].ans.y +1))
  if tumblers:
    echo (color(*BRIGHTGREY) + 'o '*tumblers)
  if gears:
    echo (color(*BRIGHTRED) + '* '*gears)
  if gears == 5: return True

  # nethack style message
  s = ''
  if tumblers > 0:
    s += str(tumblers) + ' tumbler'
    if tumblers > 1: s += 's'
    s += ' turn'
  if gears > 0:
    if s != '': s += ' and '
    s += str(gears) + ' gear'
    if gears > 1: s += 's'
    s += ' click'
  if s != '':
    s = 'You hear ' + s
  echo (color() + pos(10, 24) + cl() + s)

def disp_rules():
  " display game rules"
  pager = paraclass(ansiwin(20,64,2,8))
  pager.update (fopen('mastermind-rules.txt').read())
  pager.ans.title ('press any key...', align='bottom')
  readkey ()
  echo (cls() + cursor_hide())

def set_score(set, turns, time):
  " set current player in high score "
  return

def disp_scores(set):
  " display high scores for set "
  pager = paraclass(ansiwin(24,58,0,4))
  pager.add ('\n')
  pager.add (strpadd('High Scores',56,'center'))
  pager.add ('\n')
  pager.add ('   whatever......................................')
  pager.add ('   whatever......................................')
  pager.add ('   whatever......................................')
  pager.add ('   whatever......................................')
  pager.add ('   whatever......................................')
  pager.add ('   whatever......................................')
  pager.add ('   whatever......................................')
  return

def disp_answer(answer):
  " display answer "
  ansiwin(3,45,23,7).border()
  echo (pos(1, 24) + color() + cl() + pos(6, 24))
  for n in range(0, length):
    echo (color() + '  ' + colorof(answer[n]) + strpadd(answer[n],7))
  echo (color())
  return

def main():
  echo (cls() + color() + cursor_show())
  session.activity = 'Playing Mastermind!'

  echo (pos(35, 8) + 'Mastermind' )
  echo (pos(25, 10) + '(c) 1970 by Mordecai Meirowitz')
  echo (pos(30, 14) + 'Instructions? [ynq] ')
  k = readkey()
  if k in ['q','Q','\030']:
    return
  elif k not in ['n','N']:
    echo ('y')
    readkey (0.2)
    disp_rules ()

  while True:
    echo (cls() + cursor_hide())
    set, answer = create_pins(), get_code()
    turn, position, broke_code = 0, 0, False
    start = timenow()
    while turn < tries:
      if turn:
        # move pinset combination downward
        shift_pinset (set)
      # advance turn
      position, set = pick_lock(set, position)
      if position == -1:
        break
      if attempt_break (set, answer):
        echo (color() + pos(65, 22) + 'You win!')
        broke_code = True
        break
      turn += 1

    set_score (set, turn, timenow() -start)
    disp_answer (answer)

    echo (color() + pos(63, 24) + 'Press any key')
    readkey ()

    disp_scores (set)

    echo (color() + pos(63, 24) + 'Play again? [yn] ')
    k = readkey()
    if k not in ['y','Y']:
      echo ('n')
      readkey (0.2)
      return
