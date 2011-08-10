from bbs import *
from ui.ansiwin import *
from ui.fancy import *

h, w, y, x = \
  25, 80, 1, 1

content = []

def main():
  global content

  import ui.pager
  reload (ui.pager)
  from ui.pager import paraclass

  session.activity = 'Testing paraclass'
  echo ( color() + cls() )
  pager = paraclass (ansiwin(h, w, y, x), split=0, xpad=0, ypad=1)
  pager.debug = True
  pager.ans.border ()
  pager.ans.title ( high('up/down/(q)uit'), 'bottom')
  if not content:
    pager.update (fopen('test.ans').readlines())
    content = pager.content
  else:
    pager.update (content, align='top')
  pager.run ()
