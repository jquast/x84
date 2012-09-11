"""
System info for X/84 BBS, http://1984.ws

This is just for fun :)
"""

def main ():
  import platform
  import random
  body = ' Authors:\n' \
    '   Johannes Lundberg <johannes.lundberg@gmail.com>\n' \
    '   Jeffrey Quast <dingo@1984.ws>\n' \
    '   Wijnand Modderman <python@tehmaze.com>\n' \
    ' Artwork: spidy!food, hellbeard!impure\n'
  footer = fopen('art/si-header.asc').read()
  header = fopen('art/si-footer.asc').read()
  txt = footer + body + header
  session = getsession()
  term = session.terminal
  melt_colors = \
    [term.normal] + [term.bold_white]*16 + [term.bold_cyan]*16 + [term.bold_blue]
  from engine import __version__ as engine_version
  system, node, release, version, machine, processor = platform.uname()
  txt += ' System: %s %s %s\n' % (system, release, machine)
  txt += ' Software: X/84 %s; ' % (engine_version)
  txt += '%s %s\n'%(platform.python_implementation(),platform.python_version()) \
          if hasattr(platform, 'python_implementation') \
      else '%s %s\n' % ('.'.join(map(str, sys.version_info[:3])),
          '-'.join(map(str, sys.version_info[3:])))
  PAK = 'Press any key ... (or +-*)'
  txt += '\n' + ((maxanswidth(txt.split('\n'))/2)-(len(PAK)/2))*' ' + PAK
  txt = txt.split('\n')
  width, height = maxanswidth(txt), len(txt)
  numStars = int((term.width *term.height) *.02)
  stars = dict([(n, (random.choice('\\|/-'),
    float(random.choice(range(term.width))),
    float(random.choice(range(term.height))))) for n in range(numStars)])
  melting = {}
  plusStar = False
  t, tMIN, tMAX, tSTEP = 0.08, 0.02, 2.0, .02
  wind = (0.7, 0.1, 0.01, 0.01)

  def refresh ():
    session.activity = 'System Info'
    echo(term.move(0,0) + term.clear + term.normal)
    if term.width < width+3:
      echo (term.bold_red + 'your screen is too thin! (%s/%s)\r\n' \
        'press any key...' % (term.width, width+5))
      getch ()
      return
    if term.height < height:
      echo (term.bold_red + 'your screen is too short! (%s/%s)\r\n' \
        'press any key...' % (term.height, height))
      getch ()
      return
    x = (term.width /2) -(width /2)
    y = (term.height /2) -(height /2)
    echo (''.join([term.move(y+abs_y, x) + data \
          for abs_y, data in enumerate(txt)]))
    return x, y
  txt_x, txt_y = refresh ()

  def charAtPos(y, x, txt_y, txt_x):
    return ' ' if y-txt_y < 0 or y-txt_y >= height \
        or x-txt_x < 0 or x-txt_x >= len(txt[y-txt_y]) \
        else txt[y-txt_y][x-txt_x]

  def iterWind(xs, ys, xd, yd):
    # an easterly wind
    xs += xd; ys += yd
    if xs <= .5: xd = random.choice([0.01, 0.015, 0.02])
    elif xs >= 1: xd = random.choice([-0.01, -0.015, -0.02])
    if ys <= -0.1: yd = random.choice([0.01, 0.015, 0.02, 0.02])
    elif ys >= 0.1: yd = random.choice([-0.01, -0.015, -0.02])
    return xs, ys, xd, yd

  def iterStar(c, x, y):
    if c == '\\': char = '|'
    elif c == '|': char = '/'
    elif c == '/': char = '-'
    elif c == '-': char = '\\'
    x += wind[0]; y += wind[1]
    if x < 1 or x > term.width:
      x = 1.0 if x > term.width \
          else float(term.width)
      y = float(random.choice \
          (range(term.height)))
    if y < 1 or y > term.height:
      y = 1.0 if y > term.height \
          else float(term.height)
      x = float(random.choice \
          (range(term.width)))
    return char, x, y

  def erase(s):
    if plusStar:
      char, x, y = stars[s]
      echo (''.join((term.move(int(y), int(x)), term.normal,
        charAtPos(int(y), int(x), txt_y, txt_x),)))

  def melted(y, x):
    melting[(y,x)] -= 1
    if 0 == melting[(y,x)]:
      del melting[(y,x)]

  def melt():
    for (y, x), phase in melting.items():
      echo (''.join((term.move(y, x), melt_colors[phase-1],
        charAtPos(y, x, txt_y, txt_x),)))
      melted(y, x)

  def drawStar (star, x, y):
    ch = charAtPos(int(y), int(x), txt_y, txt_x)
    if ch != ' ':
      melting[(int(y), int(x))] = len(melt_colors)
    if plusStar:
      echo (term.move(int(y), int(x)) + melt_colors[-1] + star)

  with term.hidden_cursor():
    while True:
      event, data = readevent(['input','refresh'], timeout=t)
      if event == 'refresh':
        txt_x, txt_y = refresh ()
      elif event == 'input':
        if data == '+':
          if t >= tMIN: t -= tSTEP
        elif data == '-':
          if t <= tMAX: t += tSTEP
        elif data == '*' and not plusStar:
          plusStar = True
        elif data == '*' and plusStar:
          for star in stars: erase (star)
          plusStar = False
        else:
          break
      melt ()
      for starKey, starVal in stars.items():
        erase (starKey)
        stars[starKey] = iterStar(*starVal)
        drawStar (*stars[starKey])
      wind = iterWind(*wind)
