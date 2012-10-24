# Single player tetris for The Progressive
# Copyright (C) 2007-2009 Johannes Lundberg

#from bbs import *

deps = [ 'bbs' ]

from random import randint

def clear():
  echo ('\33[H\33[J')

def gotoxy(x,y):
  echo (pos(x,y))

# Help for the artistic developer
def showcharset():
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
      r.x2 = r.max (x2,10)
    if r.y2 == None or r.y2 < y2:
      r.y2 = r.max (y2,20)
    #print r.x1,r.y1,r.x2,r.y2
  def clean(r):
    r.x1 = None
    r.y1 = None
    r.x2 = None
    r.y2 = None

def play():
  rr = RectRedraw()
  field = []
  for i in range(20):
    field.append([0]*10)
  #echo (str(field))
  #readkey()
  echo (cls())
  showfile ('tetris.ans')
  def plotblock (color, lastcolor):
    if color:
      c='\xDB\xDB'
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
    #rr.merge(0,0,10,20)
    lastcolor=''
    if rr.x1 == None or rr.y1 == None:
      return
    # Only draw the parts which have been marked by the
    # redraw rectangle
    for y in range(rr.y1,rr.y2):
      gotoxy(10+rr.x1*2,2+y)
      for x in range(rr.x1,rr.x2):
        lastcolor = plotblock(field[y][x],lastcolor)
    echo('\33[0m')
    rr.clean()
  def drawfieldbig():
    lastcolor=''
    for y in range(0,20):
      gotoxy(10,2+y)
      for x in range(10):
        lastcolor = plotblock(field[y][x],lastcolor)
    echo('\33[0m')
  def drawfield():
    lastcolor=''
    for y in range(0,20,2):
      gotoxy(10,2+y/2)
      # Which block to show, full, half-up, half-down or empty.
      for x in range(10):
        color = field[y][x]+field[y+1][x]*8
        if       field[y][x] and     field[y+1][x]:
          c='\xDB'
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
    echo('\33[0m')

  #p    = -1  # Current piece type
  nextpiece = randint(0,len(layout)-1)
  p         = randint(0,len(layout)-1)
  p = 1
  r    = 0   # Current rotation
  xpos = 2   # X position
  #ypos = -2  # Y position
  ypos = -len(layout[p][0])
  score = 0

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

  clear()
  # temp background
  for i in range(12):
    gotoxy(8,1+i)
    echo('\xB0'*14)
  for i in range(22):
    gotoxy(8,1+i)
    echo('\xB0'*24)
  ticksize = 0.4
  nexttick = timenow()+ticksize
  showpiece(xpos,ypos,p,r)
  #shownext(nextpiece)

  # Full redraw first frame
  rr.merge(0,0,10,20)

  cursor_hide()
  while 1:
    redrawfieldbig(rr)
    #gotoxy(0,0)
    #echo('\33[37mx: %d, y: %d, p: %d         '%(xpos,ypos,p))
    #key=None
    #while not key:
    slice=nexttick-timenow()
    if slice <0:
      slice=0
    key=readkeyto(slice)
    now=timenow()
    #hidepiece()
    if key:
      if   key in [KEY.ENTER, KEY.ESCAPE, 'q']:
        break
      elif key == KEY.LEFT:
        xpos,ypos,r,m=movepiece(xpos-1,ypos,r)
      elif key == KEY.RIGHT:
        xpos,ypos,r,m=movepiece(xpos+1,ypos,r)
      elif key == KEY.UP:
        xpos,ypos,r,m=movepiece(xpos,ypos,(r+1) % len(layout[p]))
      elif key == KEY.DOWN:
        xpos,ypos,r,m=movepiece(xpos,ypos+1,r)
      elif key == KEY.SPACE:
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
        for y in range(20):
          x=0
          while x<10:
            if field[y][x] == 0:
              break
            x += 1
          if x == 10:
            complete.append(y)
        if len(complete)>0:
          # Flash
        
          # Add score
          # Shrink field
          for line in complete:
            del field[line]
            field.insert(0,[0]*10)

          # Redraw complete field
          rr.merge (0, 0, 10, 20)

        # Time for a new piece
        p         = nextpiece
        nextpiece = randint(0,len(layout)-1)
        r    = 0
        xpos = 4
        ypos = -len(layout[p][0])
        showpiece(xpos,ypos,p,r)
        #shownext(nextpiece)

  #cursor_show()
  #clear()
  #echo('\33[0m')
  #showcharset()
  #echo('\xDC\xDB\xDC '+RED+'\xDF\xDB\xDC '+BROWN+'\xDC\xDC\xDC\xDC   '+GREEN+'\xDB\xDB \xDB\xDF\xDF')
  #echo('\r\n\r\n')
  #echo(CYAN+'\xDC\xDB\xDC '+PURPLE+'\xDF\xDB\xDC   '+BROWN+'\xDC\xDC\xDC\xDC '+GREY+'\xDB\xDB '+BLUE+'\xDB\xDF\xDF')
  #readkey()

def main():
  play()
  #scripttest()
