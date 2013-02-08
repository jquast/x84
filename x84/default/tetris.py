# Single player tetris, originally written for The Progressive (prsv)
# Copyright (C) 2007-2013 Johannes Lundberg

from time import time as timenow
from random import randint

# Help for the artistic developer
def showcharset():
  from x84.bbs import echo
  echo ('**   ')
  for c in range(16):
    echo ('%X '%c)
  echo ('\r\n'+'   +'+'-'*32+'\r\n')
  for b in range(2,256/16):
    echo ('%0X | '%(b*16))
    n=16*b
    for i in range(n,n+16):
      echo (chr(i)+' ')
    echo ('\r\n')
  echo('\r\n')

# Access scheme looks like this:
#   layout[p][r][ypox][xpos]
#layoutcolor = [ 7,2,3,4,4,6,7 ]
layoutcolor = [ 7,2,7,6,3,6,3 ]
layout = [
#  ##
#  ##
[
  [
    [ 1, 1, ],
    [ 1, 1, ],
  ],
],
#  #
#  #
#  #
#  #
[
  [
    [ 0, 1, 0, 0 ],
    [ 0, 1, 0, 0 ],
    [ 0, 1, 0, 0 ],
    [ 0, 1, 0, 0 ],
  ],
  [
    [ 0, 0, 0, 0 ],
    [ 1, 1, 1, 1 ],
    [ 0, 0, 0, 0 ],
    [ 0, 0, 0, 0 ],
  ]
],
#  ###
#   #
[
  [
    [ 0, 0, 0 ],
    [ 1, 1, 1 ],
    [ 0, 1, 0 ],
  ],
  [
    [ 0, 1, 0 ],
    [ 0, 1, 1 ],
    [ 0, 1, 0 ],
  ],
  [
    [ 0, 1, 0 ],
    [ 1, 1, 1 ],
    [ 0, 0, 0 ],
  ],
  [
    [ 0, 1, 0 ],
    [ 1, 1, 0 ],
    [ 0, 1, 0 ],
  ],
],
#  #
#  #
#  ##
[
  [
    [ 0, 1, 0 ],
    [ 0, 1, 0 ],
    [ 0, 1, 1 ],
  ],
  [
    [ 0, 0, 1 ],
    [ 1, 1, 1 ],
    [ 0, 0, 0 ],
  ],
  [
    [ 1, 1, 0 ],
    [ 0, 1, 0 ],
    [ 0, 1, 0 ],
  ],
  [
    [ 0, 0, 0 ],
    [ 1, 1, 1 ],
    [ 1, 0, 0 ],
  ],
],
#   #
#   #
#  ##
[
  [
    [ 0, 1, 0 ],
    [ 0, 1, 0 ],
    [ 1, 1, 0 ],
  ],
  [
    [ 0, 0, 0 ],
    [ 1, 1, 1 ],
    [ 0, 0, 1 ],
  ],
  [
    [ 0, 1, 1 ],
    [ 0, 1, 0 ],
    [ 0, 1, 0 ],
  ],
  [
    [ 1, 0, 0 ],
    [ 1, 1, 1 ],
    [ 0, 0, 0 ],
  ],
],
#  ##
#   ##
[
  [
    [ 0, 1, 0 ],
    [ 1, 1, 0 ],
    [ 1, 0, 0 ],
  ],
  [
    [ 0, 0, 0 ],
    [ 1, 1, 0 ],
    [ 0, 1, 1 ],
  ],
],
#   ##
#  ##
[
  [
    [ 0, 1, 0 ],
    [ 0, 1, 1 ],
    [ 0, 0, 1 ],
  ],
  [
    [ 0, 0, 0 ],
    [ 0, 1, 1 ],
    [ 1, 1, 0 ],
  ],
],
]

def play():
  import os
  from x84.bbs import getterminal, getch, from_cp437, Ansi
  from x84.bbs import echo as echo_unbuffered
  term = getterminal()
  field = []
  global charcache
  charcache = u''
  field_width = 10
  field_height = 20
  class RectRedraw:
    x1 = None
    y1 = None
    x2 = None
    y2 = None
    def max (r, val, valmax):
      if val>valmax:
        return valmax
      return val
    def min (r, val, valmin):
      if val<valmin:
        return valmin
      return val
    def merge(r, x1, y1, x2, y2):
      if r.x1 == None or r.x1 > x1:
        r.x1 = r.min (x1,0)
      if r.y1 == None or r.y1 > y1:
        r.y1 = r.min (y1,0)
      if r.x2 == None or r.x2 < x2:
        r.x2 = r.max (x2,field_width)
      if r.y2 == None or r.y2 < y2:
        r.y2 = r.max (y2,field_height)
      #print r.x1,r.y1,r.x2,r.y2
    def clean(r):
      r.x1 = None
      r.y1 = None
      r.x2 = None
      r.y2 = None
  rr = RectRedraw()
  for i in range(field_height):
    field.append([0] * field_width)
  def echo(s):
    global charcache
    charcache += s
  assert term.height > (field_height + 1)
  echo_unbuffered(u''.join((
      u'\r\n\r\n',
      u'REAdY YOUR tERMiNAl %s ' % (term.bold_blue('(!)'),),
      u'\r\n\r\n',
      u'%s PRESS ANY kEY' % (term.bold_black('...'),),
      )))
  getch()
  artfile = os.path.join(os.path.dirname(__file__), 'tetris.ans')
  echo_unbuffered(u'\r\n' * (term.height))  # cls
  if os.path.exists(artfile):
      echo_unbuffered(from_cp437(open(artfile).read()))

  def gotoxy(x,y):
    echo (term.move(y,x))
  def plotblock (color, lastcolor):
    if color:
      c=u'\u2588\u2588' #'\xDB\xDB'
    else: # both empty
      c='  '
      color = 0
    # Output optimization
    if color%8 == 0:
      color = color / 8
    if color == lastcolor:
      echo(c)
    else:
      if color:
        fg = str(30+color%8)
      else:
        fg = '37'
      if color>=8:
        bg = ';%d'%(40+color/8)
      else:
        bg = ''
      echo('\33[0;'+fg+bg+'m')
      echo(c)
      lastcolor = color
    return lastcolor
  def redrawfieldbig(rr):
    #rr.merge(0,0,field_width,field_height)
    lastcolor=''
    if rr.x1 == None or rr.y1 == None:
      return
    # Only draw the parts which have been marked by the
    # redraw rectangle
    for y in range(rr.y1,rr.y2):
      gotoxy(field_width+rr.x1*2,2+y)
      for x in range(rr.x1,rr.x2):
        lastcolor = plotblock(field[y][x],lastcolor)
    echo(term.normal)
    rr.clean()
  def drawfieldbig():
    lastcolor=''
    for y in range(0,field_height):
      gotoxy(field_width,2+y)
      for x in range(field_width):
        lastcolor = plotblock(field[y][x],lastcolor)
    echo(term.normal)
  def drawfield():
    lastcolor=''
    for y in range(0,field_height,2):
      gotoxy(field_width,2+y/2)
      # Which block to show, full, half-up, half-down or empty.
      for x in range(field_width):
        color = field[y][x]+field[y+1][x]*8
        if       field[y][x] and     field[y+1][x]:
          c='\u2588' #'\xDB'
          if field[y][x] == field[y+1][x]:
            color = color%8
          else:
            c='\xDF'
        elif     field[y][x] and not field[y+1][x]:
          c='\xDF'
        elif not field[y][x] and     field[y+1][x]:
          c='\xDC'
        else: # both empty
          c=' '
        # Output optimization
        if color%8 == 0:
          color = color / 8
        if color == lastcolor:
          echo(c)
        else:
          if color:
            fg = str(30+color%8)
          else:
            fg = '37'
          if color>=8:
            bg = ';%d'%(40+color/8)
          else:
            bg = ''
          echo('\33[0;'+fg+bg+'m')
          echo(c)
          lastcolor = color
    echo(term.normal)

  #p    = -1  # Current piece type
  nextpiece = randint(0,len(layout)-1)
  p         = randint(0,len(layout)-1)
  p = 1
  r    = 0   # Current rotation
  xpos = 2   # X position
  #ypos = -2  # Y position
  ypos = -len(layout[p][0])
  #score = 0
  def flush():
    global charcache
    echo_unbuffered(charcache)
    charcache = u''
  def fillpiece(x,y,p,r,value):
    row=0
    for line in layout[p][r]:
      col = 0
      for c in line:
        if c and (y+row)>=0:
          field[y+row][x+col] = value
        col += 1
      row += 1
  def showpiece(x,y,p,r):
    fillpiece(x,y,p,r,layoutcolor[p])
  def hidepiece():
    fillpiece(xpos,ypos,p,r,0)
  def testpiece(x,y,newr):
    hidepiece()
    # Space at the new location?
    row=0
    for line in layout[p][newr]:
      col = 0
      for c in line:
        try:
          if (y+row)>=0 and c:
            if field[y+row][x+col] or (x+col)<0 or (x+col)>9: return 0
        except IndexError:
          return 0
        col += 1
      row += 1
    # Movement possible
    return 1
  def movepiece(x,y,newr):
    if testpiece(x,y,newr):
      # Build redraw rectangle
      rr.merge(xpos, ypos,
               xpos + len(layout[p][0][0]), ypos + len(layout[p][0]) )
      rr.merge(x, y,
               x + len(layout[p][0][0]), y + len(layout[p][0]) )
      showpiece(x,y,p,newr)
      return (x,y,newr,1)
    else:
      showpiece(xpos,ypos,p,r)
      return (xpos,ypos,r,0)
  def shownext(p):
    r = 0
    lastcolor = ''
    for y in range(6):
      gotoxy(38,1+y)
      for x in range(6):
        if y==0 or y==5 or x==0 or x==5:
          echo('\xB0\xB0')
        else:
          echo('\33[0m  ')
          lastcolor=''
    for y in range(len(layout[p][r])):
      gotoxy(40,2+y)
      for x in range(len(layout[p][r][0])):
        #plotblock(layoutcolor[layout[p][r][y][x]],lastcolor)
        plotblock(layout[p][r][y][x],lastcolor)

  #clear()
  # temp background
  #for i in range(12):
  #  gotoxy(8,1+i)
  #  echo('\xB0'*14)
  for i in range(22):
    gotoxy(8,1+i)
    echo(u'\u2592'*24)
  ticksize = 0.4
  nexttick = timenow()+ticksize
  showpiece(xpos,ypos,p,r)
  #shownext(nextpiece)

  # Full redraw first frame
  rr.merge(0,0,field_width,field_height)

  #cursor_hide()
  buf = ''
  while 1:
    redrawfieldbig(rr)
    #gotoxy(0,0)
    #echo('\33[37mx: %d, y: %d, p: %d         '%(xpos,ypos,p))
    #key=None
    #while not key:
    slice=nexttick-timenow()
    if slice <0:
      slice=0
    echo(buf)
    buf = ''
    flush()
    key=getch(slice+0.01)
    now=timenow()
    #hidepiece()
    if key:
      if key in [term.KEY_ENTER, term.KEY_ESCAPE, 'q']:
        return
      elif key == term.KEY_LEFT:
        xpos,ypos,r,m=movepiece(xpos-1,ypos,r)
      elif key == term.KEY_RIGHT:
        xpos,ypos,r,m=movepiece(xpos+1,ypos,r)
      elif key == term.KEY_UP:
        xpos,ypos,r,m=movepiece(xpos,ypos,(r+1) % len(layout[p]))
      elif key == term.KEY_DOWN:
        xpos,ypos,r,m=movepiece(xpos,ypos+1,r)
      elif key == ' ':
        m=True
        c=0
        while m:
          xpos,ypos,r,m=movepiece(xpos,ypos+1,r)
          if m: c += 1
        if c: nexttick = timenow() + ticksize
    # New tick?
    if now > nexttick:
      nexttick += ticksize
      # Move down piece
      xpos,ypos,r,moved=movepiece(xpos,ypos+1,r)
      # Piece has touched down?
      if not moved:
        # Any complete rows to remove?
        complete=[]
        for y in range(field_height):
          x=0
          while x<field_width:
            if field[y][x] == 0:
              break
            x += 1
          if x == field_width:
            complete.append(y)
        if len(complete)>0:
          # scroll a page, Flash
          echo(u'\r\n' * term.height)
          for n in range(5):
              echo(u'\033#8')
              getch(0.1)
              echo(term.clear)
              getch(0.1)
          # echo centered: you die
          getch()
          # Add score
          # Shrink field
          for line in complete:
            del field[line]
            field.insert(0,[0]*field_width)

          # Redraw complete field
          rr.merge (0, 0, field_width, field_height)

        # Time for a new piece
        p         = nextpiece
        nextpiece = randint(0,len(layout)-1)
        r    = 0
        xpos = 4
        ypos = -len(layout[p][0])
        showpiece(xpos,ypos,p,r)
        #shownext(nextpiece)

  #showcharset()
  #echo('\xDC\xDB\xDC '+RED+'\xDF\xDB\xDC '+BROWN+'\xDC\xDC\xDC\xDC   '+GREEN+'\xDB\xDB \xDB\xDF\xDF')
  #echo('\r\n\r\n')
  #echo(CYAN+'\xDC\xDB\xDC '+PURPLE+'\xDF\xDB\xDC   '+BROWN+'\xDC\xDC\xDC\xDC '+GREY+'\xDB\xDB '+BLUE+'\xDB\xDF\xDF')
  #getch()

def main():
  from x84.bbs import getsession, getterminal, echo
  session, term = getsession(), getterminal()
  with term.hidden_cursor():
      play()
  echo(term.move(term.height, 0))
