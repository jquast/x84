from bbs import *

def main():
  import ui.ansiwin
  reload (ui.ansiwin)
  from ui.ansiwin import ansiwin
  win = ansiwin(h=8, w=8, y=10, x=36)
  while (1):
    if win.isinview():
      win.border ()
      win.fill('*')
      echo (win.pos(1,1) + '-')
      win.title('top','top')
      win.title('bot','bottom')
    else:
      echo (pos(1,1) + 'window out of view!')
    k = readkey ()
    if win.isinview():
      win.noborder ()
    if k == KEY.UP and win.y >= 1: win.y -= 1
    if k == KEY.DOWN and win.y <= 25: win.y += 1
    if k == KEY.LEFT and win.x >= 1: win.x -= 1
    if k == KEY.RIGHT and win.x <= 80: win.x += 1
    if k == 'q': break
