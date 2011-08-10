"""
Logging module for 'The Progressive' BBS.
Copyright 2005 Johannes Lundberg
$Id: log.py,v 1.13 2010/01/06 19:30:04 jojo Exp $
"""
import types, os, traceback, sys
from time import time as timenow
import db

def write (channel='', msg='', linesep=-1):
  if linesep == -1:
    linesep = os.linesep
  if isinstance(msg, list):
    # XXX use pprint or similar
    for v in msg:
      dowrite(channel, v.strip('\n\r'), linesep)
  else:
    dowrite(channel, str(msg).strip('\n\r'), linesep)

def dowrite(channel, msg, linesep):
  PAGE=24
  LENGTH=3
  fpath=db.cfg.log_file
  if os.path.isfile(fpath) and os.stat(fpath).st_size > (pow(1024,2)*db.cfg.log_rotate):
    # only rotate 1 file back for now
    if os.path.exists(fpath+'.1'):
      os.remove(fpath+'.1')
    os.rename(fpath, fpath+'.1')

  # store to internal database
  # keep only 1024 most recent for now
  db.lock()
  idx = timenow()
  while db.logfile.has_key(idx):
    idx += .000001
  db.logfile[idx] = (channel and channel or '?', msg)
  db.commit()
  db.unlock()
  if len(db.logfile) > (PAGE*LENGTH+1):
    db.lock()
    for idx in db.logfile.keys()[:PAGE*LENGTH]:
      del db.logfile[idx]
    db.commit()
    db.unlock()

  # should broadcast an event here, but circular
  # import of engine prevents us
  fo = open(fpath, 'a')
  line='[%s]: %s%s' % (channel and channel or '?', msg, linesep,)
  fo.write (line)
  if not db.cfg.local_wfc:
    # if there is no WFC screen, print log to stdout
    sys.stdout.write(line)
  fo.close ()

def tb(type, value, tb):
  for t in traceback.format_tb (tb) \
  +traceback.format_exception_only (type, value):
    for n in t.split(os.linesep):
      if n.strip():
        write ('!!', n.lstrip().startswith('File') and n.strip() or n.rstrip())
