"""
This game demonstrates a few things. Firstly, a typical system-wide high
scores database, simple (programmed almost basic-like) game programming,
and the construction of a simple interface in pick_lock() over a list
of lightbar objects.
"""

deps = ['bbs']

def rebuild_db():
  " re-create raw oneliners database "
  global udb
  udb = openudb('mastermind')
  lock ()
  udb['scores'] = PersistentMapping ()
  udb['scores']['noset'] = [(0, 1, 9, 8, 4, 'biG BROthER')]
  unlock ()
  commit ()

def init ():
  # open oneliners database
  global udb, choices, ccodes, length, tries

  udb = openudb ('mastermind')
  if not udb.has_key('scores'):
    rebuild_db ()

  choices = [ \
    'black',
    'green',
    'brown',
    'purple',
    'red',
    'white',
    'blue',
    'yellow']

  ccodes = [ \
    color() + color(GREY),
    attr(INVERSE) + color(GREEN),
    attr(INVERSE) + color(BROWN),
    attr(INVERSE) + color(PURPLE),
    attr(INVERSE) + color(RED),
    attr(INVERSE) + color(GREY),
    attr(INVERSE) + color(BLUE),
    color() + color(*YELLOW)]

  length = 5
  tries = 11

def colorof (choice):
  return ccodes[choices.index(choice)]

def get_code():
  " return random combination "
  if random.choice([True, False, False]):
    # return new game 1/3 of the time :D
    return tuple([random.choice(choices) for n in range (0, length)])
  # return random old game, any old game will do
  return random.choice(udb['scores'].keys())

def pincode (set):
  " return combination of pin codes "
  return [lb.selection for lb in set]

def create_pins():
  " return array of lightbar objects that represent pin codes "
  set = []
  def setcolor(x, c):
    themeOverlay = {'colors': {'highlight': c, 'ghostlight': c, 'lowlight': c}}
    x.setTheme (themeOverlay)
  h, w, y = 3, 9, 1
  for n in range(0, length):
    x = (w*n)+7
    set.append (LightClass(h, w, y, x))
    set[n].update (choices)
    setcolor(set[n], colorof(set[n].selection))
    set[n].refresh ()
    set[n].interactive = True
    set[n].partial = True

  return set

def shift_pinset(set):
  " shift pins down "
  def setcolor(x, c):
    themeOverlay = {'colors': {'highlight': c, 'ghostlight': c, 'lowlight': c}}
    x.setTheme (themeOverlay)
  for n in range(0, length):
    set[n].y += 2
    setcolor(set[n], colorof(set[n].selection))
    set[n].refresh ()

def pick_lock(set, lock):
  " interactive user UI for lock picking "
  # read key in last else
  key = None

  def setcolor(x, c):
    themeOverlay = {'colors': {'highlight': c, 'ghostlight': c, 'lowlight': c}}
    x.setTheme (themeOverlay)
  setcolor(set[lock], colorof(set[lock].selection))
  set[lock].highlight ()

  while True:
    if key in ['q','\030']:
      return -1, None
    elif key in [KEY.LEFT,'h'] and lock > 0:
      set[lock].noborder ()
      lock -=1
      setcolor(set[lock], colorof(set[lock].selection))
      set[lock].highlight ()
    elif key in [KEY.RIGHT,'l'] and lock < len(set) -1:
      set[lock].noborder ()
      lock +=1
      setcolor(set[lock], colorof(set[lock].selection))
      set[lock].highlight ()
    elif key == KEY.ENTER:
      set[lock].noborder ()
      return lock, set
    else:
      set[lock].run ()
      key = set[lock].lastkey
      if set[lock].moved:
        setcolor(set[lock], colorof(set[lock].selection))
        set[lock].refresh ()
        echo (color())
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

def pattern(tumblers, gears):
  return color(*BRIGHTGREY) + 'o '*tumblers \
       + color(*BRIGHTRED)  + '* '*gears

def attempt_breakin (set, answer):
  " set UI for breakin attempt, return True if sucessful"
  tumblers, gears = check_match(pincode(set), answer)

  # set pegs
  echo (pos(set[len(set)-1].x +9, set[len(set)-1].y +1))
  echo (pattern(tumblers, gears))

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

  # you win!
  if gears == length:
    return True

def disp_rules():
  " display game rules"
  cw=60
  cx=getsession().width/2 -(cw/2)
  pager = ParaClass(h=18,w=cw,y=6,x=cx, xpad=1, ypad=1)
  pager.update (fopen('mastermind-rules.txt').read())
  pager.border ()
  pager.title ('press any key...', align='bottom')
  flushevent ('input')
  readkey ()
  echo (cls() + cursor_hide())

def set_score(boardcode, turns, time, tumblers, gears):
  " set current player in high score "
  # tally score
  score = 0
  if gears == length:
    score = gears *5
    # get 1/2 point for each second
    # not elapsed under 120 seconds
    if time < 120:
      score += (120 -time)/2
  else:
    score += gears*3 + tumblers
  turnBonus = (tries -turns)*7

  # create score record
  myscore = (score, turns, time, tumblers, gears, handle())

  # record in database
  if not udb['scores'].has_key (boardcode):
    udb['scores'][boardcode] = [(myscore)]
  else:
    udb['scores'][boardcode].append (myscore)

  # return score record
  return myscore

def disp_scores(boardcode, myscore):
  " display high scores for set "

  highScores = sorted(udb['scores'][boardcode])
  highScores.reverse ()

  # clear window region hack
  echo (''.join([pos(1, y) + ' '*62 for y in range(1, 23) if y != 3 ]))
  # title
  echo (pos (2, 3) + strpadd('High Scores',62,'center') )
  rowMatch = -1
  # for each score
  for row, highScore in enumerate(highScores):
    rowMatch = row
    # unpack from database
    score, turns, time, tumblers, gears, handle = highScore
    if row >= 20:
      # only top-most 30
      break

    echo (pos (5, 6+row))
    if not row: echo (color(*LIGHTRED))
    else: echo (color(*LIGHTBLUE))
    echo (handle)
    sleep (0.25)

    echo (pos (5, 6+row))
    if row: echo (color(GREY, NORMAL))
    else: echo (color(*WHITE))
    echo (handle)
    sleep (0.25)

    echo (pos(5+cfg.max_user+2, 6+row))
    echo (color(*DARKGREY))
    echo (str(int(score)))
    sleep (0.25)

    echo (pos(5+cfg.max_user+2, 6+row))
    if not row: echo (color(*WHITE))
    else: echo (color(GREY, NORMAL))
    echo (strpadd(str(int(score)),5,'left'))
    sleep (0.35)

    if not row: echo (color(*LIGHTRED))
    else: echo (str(color(GREY, NORMAL)))
    echo (pos(5+cfg.max_user+7, 6+row))
    echo (strpadd(str(turns),4,'right'))
    echo (color(*DARKGREY) + ' turns in ')
    if not row: echo (color(*LIGHTRED) + strpadd(asctime(time),7,'right'))
    else: echo (color(GREY, NORMAL) + strpadd(asctime(time),7,'right'))
    sleep (0.25)

    echo (color() + '  ' + pattern(tumblers, gears))
  # TODO: animate our matching row during PAK?

def disp_answer(answer):
  " display answer "
  AnsiWindow(3,45,23,7).border()
  echo (pos(1, 24) + color() + cl() + pos(6, 24))
  for n in range(0, length):
    echo (color() + '  ' + colorof(answer[n]) + strpadd(answer[n],7))
  echo (color())
  return

def main():
  echo (cls() + color() + cursor_show())
  getsession().activity = 'Playing Mastermind!'
  w = getsession().width
  h = getsession().height
  if h < 24:
    echo (color(*LIGHTRED)+'your screen must be at least 24 rows to play this game!\r\nHowever, your screen is detected as ' + str(h) + '\r\n\r\n')
    echo (color() + 'press any key to continue....')
    readkey()
    return
  if w < 80:
    echo (color(*LIGHTRED)+'your screen must be at least 80 columns to play this game!\r\nHowever, your screen is detected as ' + str(w) + '\r\n\r\n')
    echo (color() + 'press any key to continue....')
    readkey()
    return

  txt = ['Mastermind','(c) 1970 by Mordecai Meirowitz','Instructions? [ynq]']
  for n, txt in enumerate(txt):
    echo (pos(w/2-(len(txt)/2), 2+(n*2)) + txt)
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
    turns, position, broke_code = 0, 0, False
    start = timenow()
    while turns < tries:
      # advance turn
      position, set = pick_lock(set, position)
      if position == -1:
        # early exit
        break
      if attempt_breakin (set, answer):
        echo (color() + pos(65, 22) + 'You win!')
        broke_code = True
        break
      turns += 1

      # move pinset combination downward
      shift_pinset (set)

    tumblers, gears = check_match(pincode(set), answer)
    myscore = set_score \
      (answer, turns, timenow() -start, tumblers, gears)

    disp_answer (answer)

    echo (color() + pos(63, 24) + 'Press any key')
    readkey ()

    disp_scores (answer, myscore)

    flushevent ('input')
    echo (color() + pos(63, 24) + 'Play again? [yn] ')
    while True:
      k = readkey()
      if k.lower() in ['n','q']:
        echo ('n')
        readkey (0.2)
        return
      if k.lower() in ['y']:
        break
