# $Id: fb.py,v 1.5 2008/10/02 04:05:52 dingo Exp $
#
# filebrowser for prsv -- in the works...
#
# Copyright 2007 (c) Jeffrey Quast
#
import traceback
import sys

import log
deps = ['bbs']

def main(basedir='./ansi'):
  path = basedir
  echo (cls())

  def readfile (filepath):
    fobj = open(filepath)
    sobj = Sauce(fobj)
    data = ''
    if sobj.sauce:
      # retrieve sauce and non-sauce data
      title = sobj.info['title']
      author = sobj.info['author']
      group = sobj.info['group']
      data = sobj.data ()
    else:
      # retrieve data, set title to filename
      title = filepath
      author, group = '', ''
      fobj.seek (0)
      data = fobj.read ()
    fobj.close ()
    del sobj

    pager = paraclass (ansiwin(24, 80, 1, 1), split=0, xpad=0, ypad=1)
    echo (color() + cls())

    pager.ans.lowlight (partial=True)
    pager.ans.title (color() + '-< ' + trim(title) + ' - ' \
                     + trim(author) + '/' + trim (group) + '>-')
    pager.ans.title (color() + '-< ' + 'up/down/(q)uit/(f)ullscreen' + ' >-', align='bottom')

    # cross your fingers and run
    try:
      pager.interactive = True
      pager.update (data)
      while 1:
        k = inkey()
        pager.run (k)
        if k == 'f':
          echo (color() + cls())
          echo (data)
          echo ('\r\n' + color() + charset() + 'Press any key to return')
          inkey ()
          break
        elif pager.exit: break
    except:
      type, value, tb = sys.exc_info ()
      log.write ('', 'fb: cant transpose', filepath)
      log.write ('', traceback.format_exception_only (type, value))
      log.write ('', traceback.format_tb (tb))

    pager.ans.clear ()
    pager.ans.noborder ()
    # refresh
    echo (cls() + reset() + charset())
    fbb.lowlight (partial=True)
    fbb.title('CTRl+X:EXIt RIGht/REtURN:OPEN lEft:bACk', align='bottom')
    fb.refresh ()

  # override retrieve method of lightstepclass to create a filebrowsing class
  class fileclass(lightstepclass):
    global basedir
    def retrieve(s, key):
      " overriding retrieve method with filepath listing "
      list = []
      for record in getfiles(key, basedir):
        list.append (record)
      return list

  # fb is filebrowser object, inherited from lightstepclass
  fb = fileclass(ansiwin(h=12, w=50, y=5, x=15))
  fb.interactive = True
  # fb border
  fbb = ansiwin(h=14, w=52, y=4, x=14)
  fbb.lowlight (partial=True)
  fbb.title('CTRl+X:EXIt RIGht/REtURN:OPEN lEft:bACk', align='bottom')

  fb.debug = True
  # lightbar is active window in filebrowser
  lightbar = fb.right(basedir)

  while True:
    lightbar.run ()
    if lightbar.lastkey == '':
      # exit
      return 'done'
    elif lightbar.lastkey in [KEY.RIGHT,KEY.ENTER,'l']:
      walk, dest = changedir(path, lightbar.selection)
      if walk == 'right':
        # walk right
        ol = lightbar
        lightbar = fb.right(dest)
        if not lightbar:
          lightbar = ol
        else:
          path = dest
      elif walk == 'left' and fb.depth:
        # walk left (must have walked into ../)
        ol = lightbar
        lightbar = fb.left()
        if not lightbar:
          lightbar = ol
        else:
          path = parentdir(path)
      elif walk == 'action':
        # do action (must be file)
        readfile (dest)
      else:
        print 'error on walk', walk, 'dest', dest, 'from', path
    elif lightbar.lastkey in [KEY.LEFT,KEY.ESC,'h'] and fb.depth:
      # walk left
      lightbar = fb.left()
      path = parentdir(path)
  return 'done again'
