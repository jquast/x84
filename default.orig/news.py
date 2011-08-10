"""
 News reader module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: news.py,v 1.4 2008/05/26 07:25:32 dingo Exp $

 This modulde demonstrates simple use of a pager window.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

deps = ['bbs']

h, w, y, x = \
  15, 77, 11, 2

def init():
  import os
  global news_content, lastmod
  news_content = fopen('text/news.txt').read()
  lastmod = os.path.getmtime(abspath('text/news.txt'))

def main():

  session.activity = 'Reading News'
  echo (color() + cls())

  if lastmod < os.path.getmtime(abspath('text/news.txt')):
    init ()

  pager = paraclass(ansiwin(h, w, y, x), split=10, xpad=2, ypad=2)
  pager.interactive = False
  pager.ans.lowlight (partial=True)
  pager.ans.title ('up/down/(q)uit')
  pager.update (news_content)

  echo (pos(1,1))
  showfile ('ans/news.ans')

  pager.run ()
