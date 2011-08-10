"""
 AP Wire news reader for 'The Progressive' BBS
 Copyright (c) 2008 Jeffrey Quast
 $Id: ap.py,v 1.2 2008/05/10 08:27:25 dingo Exp $

 This modulde demonstrates extending prsv modules by using external resources.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2008 Jeffrey Quast']
__license__ = 'ISC'

import urllib, cStringIO, gzip, xml.parsers.expat, time
import sys
from time import strftime, gmtime, mktime
deps = ['bbs','ui.ansiwin','ui.pager','ui.lightwin','ui.fancy']

debug = fopen('stdout','w')
ap_categories = [ 'sptbaseball', 'topheads', 'usheads', 'politicsheads', 'washingtonheads', 'businessheads', 'sportsheads', 'entertainment', 'healthheads', 'scienceheads', 'strangeheads' ]
ap_keys = [ 'item', 'title', 'link', 'description', 'pubDate', 'author']

def main(categories=[]):
  # global 'state' variables
  global cname, cattrs, cvalues, story, ap_category, title

  # global 'data' variables
  global apwire

  # global variables modified by expat parser (XXX lock issue)
  cname, cattrs, cvalues, = None, None, None
  title = ''
  ap_category = ''
  # collection of stories
  apwire = {}
  # single story
  story = {}

  echo (color() + pos(16,4) + 'Retrieving ap wire data...')
  flush ()

  # retrieve ap data
  for ap_category in ap_categories:
    if not ( ap_category in categories or not categories):
      debug.write ('skipping: ' + ap_category + '\n')
      continue

    ap_xmlurl = 'http://hosted.ap.org/lineups/' \
    + ap_category.upper() + '-rss_2.0.xml?SITE=RANDOM&SECTION=HOME'
    fobj = cStringIO.StringIO(urllib.urlopen(ap_xmlurl).read())
    try: data = gzip.GzipFile(fileobj=fobj).read()
    except: data = '<?' + fobj.read()

    # parse xml data
    wp = xml.parsers.expat.ParserCreate ()
    wp.StartElementHandler = start
    wp.EndElementHandler = end
    wp.CharacterDataHandler = character
    wp.Parse(data, True)
    del wp

  #debug.write (repr(apwire))
  echo (pos(16, 4) + cl())

  # story selection
  lb = lightclass(ansiwin(h=6,w=77,y=2,x=1))
  lb.interactive = True

  l = []
  for key in apwire.keys():
    debug.write (repr(key)+'\n')
    l.append (key)
  lb.update (l)

  readkey ()
  # story
  pager = paraclass(ansiwin(h=14,w=77,y=10,x=1), xpad=2, split=8, ypad=2)

  def refresh_windows():
    # clear
    title ='thE MiNiStRY Of tRUth bRiNGS YOU thiS NEWS bUllEtiN...'
    echo (cls() + color() + cursor_show())
    lb.ans.lowlight (partial=True)
    lb.refresh ()
    pager.ans.lowlight (partial=True)
    lb.ans.title (color(BLUE) + '-< ' + hi(title, highlight=color(BLUE)) + color(BLUE) + ' >-',align='bottom')
    pager.ans.title (color(BLUE) + '-< ' + hi('q:QUit, UP/dOWN: StORY', highlight=color(BLUE)) + color(BLUE) + ' >-',align='bottom')

  refresh_windows()
  #
  # apwire conditions/forecast selector
  #
  while not lb.exit:
    txt = '__'
    if not lb.moved and lb.lastkey == '\014':
      refresh_windows ()
      pager.update (str(txt))
    if lb.moved:
      echo (color())
      #txt += hi(lo('\n(c) '+ str(apwire['Copyright'])),'isupper',highlight=color(*WHITE))
      pager.update (str(txt))

    lb.run ()

    if lb.exit: break

def start(name, attrs):
  global cname, cattrs, ap_category
  cname, cattrs = name, attrs
  debug.write (ap_category + 'start cname: ' + repr(cname) + 'cattrs' + repr(cattrs) + '\n')
  #if 'city' in cattrs.keys():
  #  lookup.append (cattrs)

def end(name):
  global cname, cattrs, ap_category
  cname, cattrs = None, None
  #debug.write (ap_category + 'end cname: ' + repr(cname) + 'cattrs' + repr(cattrs) + '\n')

def character(data):
  global cname, cattrs, story, title, ap_category

  if cname == 'title' and trim(data):
    title = trim(data)
    story = {}

  if (cname in ap_keys and trim(data)) \
  or (cname == 'description' and trim(cattrs)):
    debug.write (cname + ':' + trim(data) + '\n')
    #if cname == 'description' and trim(data):
    #  #if not 'description' in story.keys():
    #  #  story['description'] = trim(data)
    #  #story['description'] += trim(data)
    if cname == 'link' and trim(data):
      if not 'link' in story.keys():
        story['link'] = trim(data)
      story['link'] += trim(data)
    else:
      story[cname] = trim(data)
  elif cname == 'description':
    debug.write(str(cname in ap_keys) + str(cname) + '!: ' + str(cattrs) + '|' + str(data) + '\n')
  elif not cname in ap_keys and not trim(data):
    debug.write ('skipping: ' + str(cname) + '\n')

  # write
  if title: apwire[title] = story

#def location_chdata(data):
#  global cname, cattrs, lookup
#  pr

