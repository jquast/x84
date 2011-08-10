from bbs import *
from ui.ansiwin import *
from ui.pager import *
from ui.fancy import *

y, x = \
5, 10

title = (color(CYAN)*10) +'B' + color() + 'i' + (bcolor(CYAN)*3) + color(BLACK) + 'g Brother ' \
      + bcolor(BLACK) + color(CYAN) + '\033[4CB' + (color()*10) + 'roadcasting ' \
      + color(CYAN) +'S' + color() + 'ystem'

def main():
  echo ( cls() )
  session.activity = 'testing ansilen()'
  echo ( pos(x, y-1) + '-' * ansilen(title))
  echo ( pos(x, y) + title)
  echo ( pos(x, y+1) + '-' * ansilen(title))

  echo ('\r\n\r\n if ansilen() is working, the \'-\'s should size up to the printed size')
  readkey ()
