"""
 Last Callers module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 Copyright (c) 2006 Johannes Lundberg
 $Id: lc.py,v 1.5 2008/10/02 04:05:52 dingo Exp $

 When recordonly is passed to main(), only record call and return.
 Otherwise display last callers window. The displayed last callers
 is cached for 'rebuild_mins'.

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast',
                 'Copyright (c) 2006 Johannes Lundberg']
__license__ = 'ISC'

deps = ['bbs']

y, bottom = 14, 24
h, w = bottom -y, 57

def init():
  global udb
  # open sorted call log
  udb = openudb('lc')

def retrieve():
  " retrieve window paint data "
  print 'lc: retrieving call log'
  session.activity = 'Retrieving Call Log'
  data = []
  callers = udb['callers']
  for rec in callers:
    lctime = rec[0]
    handle = rec[1]
    user = getuser(handle)
    location = user.location
    calls = user.calls
    if not userexist(handle):
      continue
    data.append \
      ( strpadd(handle, cfg.max_user +1) \
      + strpadd(location, 14, trim=True)
      + strpadd(asctime(timenow() -lctime) +' ago', 12,'right') \
      + strpadd('  Calls: ' + str(calls), 13))
  return data

def build():
  " build and return last callers list for display "
  global udb
  print 'lc: building callog'
  session.activity = 'Building Call Log'
  callers = {}
  for user in listusers():
    while callers.has_key(user.lastcall):
      # very rare, duplicate keys?!
      user.lastcall += .1
    callers[user.lastcall] = user.handle
  sorted_callers = []
  lctimes = callers.keys()
  lctimes.sort ()
  lctimes.reverse ()
  for lc in lctimes:
    sorted_callers.append ([lc, callers[lc]])
  lock()
  udb['callers'] = sorted_callers
  commit()
  unlock()

def main(recordonly=False):
  if recordonly:
    build ()
    return
  session.activity = 'Viewing Last Callers'
  echo ( color() + cls() )
  pager = paraclass(ansiwin(h, w, y+1, (80-w)/2-2), split=0, xpad=3, ypad=1)
  pager.ans.lowlight (partial=True)
  echo ( pos(1, 1) )
  showfile ('ans/lc.ans')
  oflush ()
  data = retrieve()
  if len(data) < h:
    pager.ans.title ('(q)uit', 'bottom')
  else:
    pager.ans.title ('up/down/(q)uit', 'bottom')

  # update display dataset and run
  pager.update (data)
  return pager.run ()

