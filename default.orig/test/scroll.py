"""
 About screen for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: scroll.py,v 1.1 2008/04/07 23:20:13 dingo Exp $

 This is a simple example of a scrolling pager window
"""
__author__ = "Jeffrey Quast <dingo@1984.ws>"
__contributors__ = []
__copyright__ = "Copyright (c) 2007 Jeffrey Quast"
__license__ = "ISC"

from bbs import *
from ui.ansiwin import *
from ui.pager import *
from ui.fancy import *

h, w, y, x = \
  11, 31, 7, 35

def main():
  session.activity = 'Reading About'
  echo ( color() + cls() )
  showfile ('../ans/about.ans')

  pager = paraclass(ansiwin(h, w, y, x), split=4, xpad=2, ypad=1)
  pager.ans.lowlight (partial=True)
  pager.ans.title ( hi('test::scrolling', 'ispunct'), 'top')
  pager.ans.title ( hi('(q)uit', 'ispunct'), 'bottom')

  lines = []
  lines = fopen('../text/test.txt').readlines()

  def exit():
    pager.add ('\n\n * Press any key to return *\n')
    readkey()

  k = ''
  i = 0
  while True:
    pager.add (lines[i])
    i +=1
    if i == len(lines) or k == 'q':
      exit ()
      return
    k = readkeyto(2)
  exit()
