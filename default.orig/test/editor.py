# Editor (test)
#
# (c) 2007 Jeffrey Quast

from bbs import *
from ui.ansiwin import *
from usercfg import *

def main():
  session.activity = 'Composing message'
  import ui.pager
  reload(ui.pager)
  from ui.pager import paraclass

  # editor window
  editor = paraclass(ansiwin(5,10,10,35), xpad=0, ypad=0)
  editor.debug, editor.edit = True, True

  echo (color() + cursor_show() + cls())
  showfile ('editor.ans')
  editor.add ('test')
  editor.add ('tset')

  editor.ans.lowlight()
  editor.run()
