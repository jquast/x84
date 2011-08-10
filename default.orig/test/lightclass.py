from bbs import *
from ui.ansiwin import *
from ui.fancy import *

h, w, y, x = \
  23, 30, 1, 1

def main():

  import ui.lightwin
  reload (ui.lightwin)
  from ui.lightwin import lightclass

  echo ( color() + cls() )
  lb = lightclass (ansiwin(4, 60, 24-4, 40-(60/2)))
  lb.ans.border ()
  lb.ans.title ( high('up/down/(q)uit'), 'bottom')
  lb.debug = True
  lb.update (['a','b','c','d','e','f','g'])
  selection = lb.run ()
  echo (cls() + 'selection: ' + selection)
