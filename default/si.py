"""
System info for X/84 BBS, http://1984.ws
$Id: si.py,v 1.7 2009/05/31 16:14:59 dingo Exp $

This is just for fun :)

"""
__author__ = 'Wijnand Modderman <python@tehmaze.com> & Jeff Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Wijnand Modderman, Jeff Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs', 'fileutils']

import platform
import socket
import twisted
import ZODB
import random

def init():
  global txt, width, height
  txt = fopen('art/si-footer.asc').read()
  txt += \
  ' Authors:\n' \
  '   Johannes Lundberg <johannes.lundberg@gmail.com>\n' \
  '   Jeffrey Quast <dingo@1984.ws>\n' \
  '   Wijnand Modderman <python@tehmaze.com>\n' \
  ' Artwork: spidy!food, hellbeard!impure\n'
  txt += fopen('art/si-header.asc').read()
  from engine import __version__ as engine_version
  system, node, release, version, machine, processor = platform.uname()
  txt += ' System: %s %s %s\n' % (system, release, machine)
  txt += ' Software:\n    X/84 cvs: %s; python ' % (engine_version)
  if hasattr(platform, 'python_implementation'): # 2.6+ (for real men)
    txt += '%s %s\n' % (platform.python_implementation(),
                         platform.python_version())
  else:
    txt += '%s %s\n' % ('.'.join(map(str, sys.version_info[:3])),
                         '-'.join(map(str, sys.version_info[3:])))
  PAK = 'Press any key ... (or +-*)'
  txt += '\n' + ((maxwidth(txt.split('\n'))/2)-(len(PAK)/2))*' ' + PAK
  txt = txt.split('\n')
  width, height = maxwidth(txt), len(txt)

def main ():
  def refresh ():
    session = getsession()
    getsession().activity = 'System Info Screen'
    echo(cls() + color() + cursor_hide ())
    if getsession().width < width+3:
      echo (color(*LIGHTRED) + 'your screen is too thin! (%s/%s)\r\n' \
        'press any key...' % (getsession().width, width+5))
      getch ()
      return
    if getsession().height < height:
      echo (color(*LIGHTRED) + 'your screen is too short! (%s/%s)\r\n' \
        'press any key...' % (getsession().height, height))
      getch ()
      return
    x = (session.width /2) -(width /2)
    y = (session.height /2) -(height /2)
    echo (''.join([pos(x, y+abs_y) + data \
          for abs_y, data in enumerate(txt)]))
    return x, y

  def charAtPos(x, y, txt_x, txt_y):
    row, col = y-txt_y, x-txt_x
    if row < 0 or row >= height or col < 0: return ' '
    rowtxt = txt[row]
    if col >= len(rowtxt): return ' '
    else: return rowtxt[col]

  txt_x, txt_y = refresh ()
  stars = {}
  melting = {}
  numStars = (getsession().width * getsession().height)*.02
  plusStar = False
  t=.08
  tMIN, tMAX, tSTEP =0.02, 2.0, .02
  # winds is (x-slope, y-slope, x-direction, y-direction)
  wind = (0.7, 0.1, 0.01, 0.01)

  melt_colors = \
    [color()] +[color(*WHITE)]*16 +[color(*LIGHTCYAN)]*16 +[color(*LIGHTBLUE)]

  for n in range(numStars):
    stars[n] = (random.choice(['\\','|','/','-']),
                float(random.choice(range(getsession().width))),
                float(random.choice(range(getsession().height))))

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
    if x < 1 or x > getsession().width:
      x = 1.0 if x > getsession().width \
          else float(getsession().width)
      y = float(random.choice \
          (range(getsession().height)))
    if y < 1 or y > getsession().height:
      y = 1.0 if y > getsession().height \
          else float(getsession().height)
      x = float(random.choice \
          (range(getsession().width)))
    return char, x, y

  def erase(s):
    if plusStar:
      char, x, y = stars[s]
      echo (pos(int(x), int(y)) + color() + charAtPos(int(x), int(y), txt_x, txt_y))

  def melted(x, y):
    melting[(x, y)] -= 1
    if not melting[(x,y)]:
      del melting[(x,y)]

  def melt():
    for (x, y), phase in melting.items():
      echo (pos(x, y) + melt_colors[phase-1] + charAtPos(x, y, txt_x, txt_y))
      melted(x, y)

  def drawStar (star, x, y):
    ch = charAtPos(int(x), int(y), txt_x, txt_y)
    if ch != ' ':
      melting[(int(x), int(y))] = len(melt_colors)
    if plusStar:
      echo (pos(int(x), int(y)) + melt_colors[-1] + star)

  while True:
    event, data = readevent(['input','refresh'], timeout=t)
    if event == 'refresh':
      txt_x, txt_y = refresh ()
    elif event == 'input':
      if data == '+':
        if t >= tMIN: t -= tSTEP
      elif data == '-':
        if t <= tMAX: t += tSTEP
      elif data == '*' and not plusStar: plusStar = True
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
  echo (cursor_show())
