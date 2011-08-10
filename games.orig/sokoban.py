# Split-screen chat module for PRSV
#
# (c) 2007 Jeffrey Quast
# (c) 2007 Johannas Lundberg

from bbs import *
from ui.fancy import *
from ui.ansiwin import *
from strutils import *
from usercfg import *

main_menu = ["Play", "Join Game", "High Scores", "Help", "Quit"]

# global listing of users available for chat
players = []
timeout_req = 10
timeout_slice = .33

def percentage_text (text, percentage):
  brk = int(float(len(text))*percentage)
  return color() + bcolor(WHITE) + color(BLACK) \
    + text[:brk] + color() \
    + text[brk:]

def main ():
  import ui.pager
  reload (ui.pager)
  from ui.pager import paraclass
  import ui.lightwin
  reload (ui.lightwin)
  from ui.lightwin import lightclass
  import ui.fancy
  reload (ui.fancy)
  from ui.fancy import warning, prompt
  map = ['------  ----- ',
         '|....|  |...| ',
         '|....----...| ',
         '|...........| ',
         '|..|-|.|-|..| ',
         '---------|.---',
         '|......|.....|',
         '|..----|.....|',
         '--.|   |.....|',
         ' |.|---|.....|',
         ' |...........|',
         ' |..|---------',
         ' ----         ']
  height =len (map)
  width  =maxwidth (map)
  boulders, pits, stairs = [], [], []
  for row in range(0, height):
    boulders.append (' '*width)
    pits.append     (' '*width)
    stairs.append   (' '*width)
  def addobj(type, pos):
    row, col= pos[0], pos[1]
    if type == 'boulder':
      boulders[row] = boulders[row][:col]+'O'+boulders[row][col+1:]
    elif type == 'pit':
      pits[row] = pits[row][:col]+'^'+pits[row][col+1:]
    elif type == 'upstairs':
      stairs[row] = stairs[row][:col]+'<'+stairs[row][col+1:]
    elif type == 'downstairs':
      stairs[row] = stairs[row][:col]+'>'+stairs[row][col+1:]

  def delobj(type, pos):
    row, col= pos[0], pos[1]
    if type == 'boulder':
      boulders[row] = boulders[row][:col]+' '+boulders[row][col+1:]
    elif type == 'pit':
      pits[row] = pits[row][:col]+' '+pits[row][col+1:]
    elif type == 'upstairs':
      stairs[row] = stairs[row][:col]+' '+stairs[row][col+1:]
    elif type == 'downstairs':
      stairs[row] = stairs[row][:col]+' '+stairs[row][col+1:]

  addobj ('boulder',[2,2])
  addobj ('boulder',[3,2])
  addobj ('boulder',[2,10])
  addobj ('boulder',[3,9])
  addobj ('boulder',[4,10])
  addobj ('boulder',[7,8])
  addobj ('boulder',[8,9])
  addobj ('boulder',[9,9])
  addobj ('boulder',[10,8])
  addobj ('boulder',[10,10])
  addobj ('pit',[6,3])
  addobj ('pit',[6,4])
  addobj ('pit',[6,5])
  addobj ('pit',[8,2])
  addobj ('pit',[9,2])
  addobj ('pit',[10,4])
  addobj ('pit',[10,5])
  addobj ('pit',[10,6])
  addobj ('pit',[10,7])
  addobj ('upstairs',[6,6])
  addobj ('downstairs',[4,6])
  safe = ['.','<','>','^']

  def whatat(p):
    row,col = p[0], p[1]
    if boulders[row][col] != ' ':
      return boulders[row][col]
    elif pits[row][col]!= ' ':
      return pits[row][col]
    elif stairs[row][col]!= ' ':
      return stairs[row][col]
    else:
      return map[row][col]

  def find(obj):
    for row in range(0, height):
      for col in range(0, width):
        if obj == 'upstairs' and whatat([row, col]) == '<' \
        or obj == 'downstairs' and whatat([row, col]) == '>':
          return (row, col)

  def display_at(p, ch=None):
    if ch: echo (pos(p[1]+1, p[0]+1) + ch)
    else: echo (pos(p[1]+1, p[0]+1) + whatat(p))

  def showmap():
    echo (cls())
    for row in range(0, height):
      echo (pos(1, row+1))
      for col in range(0, width):
        echo (whatat([row, col]))

  def moveboulder(fro, to):
    if whatat((to)) in safe:
      delobj('boulder', fro)
      if whatat(to) == '^':
        delobj('pit', to)
      else:
        addobj('boulder', to)
      display_at(to)
      return True
    else:
      return False

  def move_player(fro, to):
    direction = ''
    if fro[0] > to[0]: direction = 'up'
    if fro[0] < to[0]: direction = 'down'
    if fro[1] > to[1]: direction += 'left'
    if fro[1] < to[1]: direction += 'right'
    if whatat(to) == 'O':
      boulderto = ''
      if direction == 'left': boulderto = leftof(to)
      elif direction == 'right': boulderto = rightof(to)
      elif direction == 'up': boulderto = above(to)
      elif direction == 'down': boulderto = below(to)
      if not (boulderto and moveboulder(to, boulderto)):
        return fro
    elif not whatat(to) in safe:
      return fro
    elif (direction == 'upright' and not (whatat(above(fro)) in safe or whatat(rightof(fro)) in safe)) \
    or (direction == 'upleft' and not (whatat(above(fro)) in safe or whatat(leftof(fro)) in safe)) \
    or (direction == 'downright' and not (whatat(below(fro)) in safe or whatat(rightof(fro)) in safe)) \
    or (direction == 'downleft' and not (whatat(below(fro)) in safe or whatat(leftof(fro)) in safe)):
      return fro
    display_at(fro)
    display_at(to, '@\b')
    return to

  def leftof(p):  return [p[0],   p[1]-1]
  def rightof(p): return [p[0],   p[1]+1]
  def above(p):   return [p[0]-1, p[1]  ]
  def below(p):   return [p[0]+1, p[1]  ]

  def move(p, key):
    if key in [KEY.DOWN, 'j']: return move_player (p, below(p))
    elif key in [KEY.UP, 'k']: return move_player (p, above(p))
    elif key in [KEY.LEFT, 'h']: return move_player (p, leftof(p))
    elif key in [KEY.RIGHT, 'l']: return move_player (p, rightof(p))
    elif key in ['y']: return move_player (p, above(leftof(p)))
    elif key in ['u']: return move_player (p, above(rightof(p)))
    elif key in ['b']: return move_player (p, below(leftof(p)))
    elif key in ['n']: return move_player (p, below(rightof(p)))
    else: return p

  def dial (remotesid):
    """ Request remote session to chat, waiting only as long as
        global value timeout_req. If chat request is acknowledged,
        return unique communication channel. Otherwise return 0 """
    # send chat request
    sendevent (remotesid, 'soko-page', session.sid)
    # wait for remote user to accept
    session.activity = 'Requesting to join sokoban game'
    for n in range(0, int(timeout_req/timeout_slice)):
      # display percentage bar
      status.update (percentage_text('  Waiting for reply...  ',
                     n /(timeout_req /timeout_slice)))
      event, data = readevent (['soko-ack','input'], timeout_slice)
      if event == 'soko-ack' and data[0] == 'accept':
        channel = data[1]
        # send acknowledgement
        status.update ('player accepted')
        sendevent (remotesid, 'soko-ack', 'go')
        return channel
      elif event == 'soko-ack' and data == 'decline':
        # invintation declined
        warning ('Chat with ' + repr(userbysid(remotesid)) + ' was declined', [60,prompt_y])
        break
      elif event == 'soko-ack' and data == 'soko-hangup':
        warning ('remote user hung up!', [60,prompt_y])
    sendevent (remotesid, 'soko-ack', 'soko-hangup')
    return 0

  def answer (data, channel):
    # received invintation
    session.activity = 'Reviewing game invintation'
    remotesid, mysid = data, session.sid
    p = 'z'
    while (not p in ['y','n','none']):
      # wait until user accepts or denies chat, or until timeout
      p = prompt ('Play with ' + repr(userbysid(remotesid)), [45,prompt_y], clean=True, timeout=timeout_req)
    if p == 'y':
      # agree to play
      status.update (low('Hello?','ispunct'), align='center')
      sendevent (remotesid, 'soko-ack', ('accept', channel))
      event, data = readevent ('soko-ack', 1)
      if event == 'soko-ack' and data == 'go':
        status.update ('Playing with ' + userbysid(remotesid), align='center')
        return True
      else:
        warning ('remote user hung up!', [60,prompt_y])
    elif p == 'n':
      status.update ('* Click!', align='center')
      sendevent (remotesid, 'soko-ack', 'decline')
    if p == 'None':
      warning ('remote user hung up!', [60,prompt_y])
    return 0

  def play(channel):
    prompt_y = 1
    players.append ([session.handle, session.sid])
    echo (cls())
    showmap ()
    player_pos = find('downstairs')
    player_pos = [player_pos[0], player_pos[1]]
    echo (pos(player_pos[1]+1, player_pos[0]+1) + '*')
    while 1:
      event, data = readevent (['input', 'soko-page', channel])
      if event == 'input':
        # process user keystroke
        if data == '\030':
          return
        else:
          player_pos = move (player_pos, data)
          None
      elif event == 'soko-page':
        # answer call
        answer (data, channel)
      elif event == channel:
        # process someone else's keystroke
        None

    # make self available for play
    players.remove ([session.handle, session.sid])
    echo (cls())
    if len(names): userctl.ans.lowlight (partial=True)
    menuctl.ans.lowlight (partial=True)
    menuctl.update (main_menu)
    prompt_y = menuctl.ans.y +menuctl.ans.h +1

  def available ():
    " list users available for chat, except thyself "
    l = []
    for p in range(0,len(players)):
      if players[p][1] != session.sid:
        l.append (players[p][0])
    return l

  def userbysid (sid):
    " pass sessionid, return username for that user "
    for s in sessionlist ():
      if s.sid == sid:
        return s.handle

  def sidbyname (name):
    " pass username, return first sessionid found for that user "
    for p in range(0,len(players)):
      if players[p][0] == name:
        return players[p][1]

  # retrieve list of persons available for chat
  names = available ()

  # status bar (middle of bottom window)
  status = paraclass (ansiwin(1,78,24,2), split=0, xpad=1, ypad=0)
  status.ans.lowlight (partial=True)

  # game option window
  menuctl = lightclass (ansiwin(len(main_menu)+1, max_user+6, 2,  40-((max_user+6)/2)))
  # user selection window
  userctl = lightclass (ansiwin(8, max_user+6, 11, 40-((max_user+6)/2)))

  prompt_y = menuctl.ans.y +menuctl.ans.h +1
  echo (cls())

  if len(names):
    userctl.ans.lowlight (partial=True)
  menuctl.ans.lowlight (partial=True)
  menuctl.update (main_menu)

  # userctl: lightbar object
  # oplayers: when not equal to current number of players, refresh
  # or re-evaluate if lobby is occupie
  oplayers = -1

  while 1:

    names = available ()
    session.activity = 'Sokoban main screen'

    if oplayers != len(names) and len(names):
      # update 'currently playing' window
      userctl.update (available())
      if oplayers <=0:
        userctl.ans.lowlight (partial=True)
        userctl.ans.title(low('Other games:'))
    if oplayers != len(names) and not len(names):
      if oplayers > 0:
        userctl.ans.noborder()
        userctl.ans.clear()
      status.update (low('Sokoban v0.1!','ispunct'), align='center')

    selection = menuctl.run (timeout=0.76)
    if selection == 'Play':
      play(timenow())
      prompt_y = menuctl.ans.y +menuctl.ans.h +1
    elif selection == 'Join Game':
      session.activity = 'Reviewing other games'
      if len(names):
        print 'join'
        while 1:
          data = readkey()
          if data == '\030': break
          # users are available for chat, process keypress through lightbar
          index = userctl.run (key=data, byindex=True)
          if index is not None:
            # dial user by sessionid (XXX what if 2 users, 2 sid's?)
            remotesid = sidbyname(names[index])
            channel = dial (remotesid)
            if channel > 0:
              play(channel)
      else:
        warning ('No games to watch-', [60,prompt_y])
        menuctl.refresh ()
    elif selection == 'High Scores':
      warning ('You win-', [60,prompt_y])
      menuctl.refresh ()
    elif selection == 'Help':
      warning ('Don\'t panic-', [60,prompt_y])
      menuctl.refresh ()
    elif selection == 'Quit' or menuctl.lastkey == '\030':
      p = 'z'
      while (not p in ['y','n']):
        # wait until user accepts or denies chat, or until timeout
        p = prompt ('Really Quit', [45,prompt_y], clean=True)
      if p == 'y':
        return
    oplayers = len(names)
