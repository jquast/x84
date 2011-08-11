import copy, logging

# compatibility for old log.write()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ColoredConsoleHandler(logging.StreamHandler):
  # http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored
  def emit(self, record):
    myrecord = copy.copy(record)
    levelno = myrecord.levelno
    if(levelno >= 50): # CRITICAL / FATAL
      color = '\x1b[35m' # red
    elif(levelno >= 40): # ERROR
      color = '\x1b[31m' # red
    elif(levelno >= 30): # WARNING
      color = '\x1b[33m' # yellow
    else:
      color=''
    myrecord.levelname = '%s%-7s%s' % \
      (color, myrecord.levelname.capitalize(), '\x1b[0m' if color else '')
    logging.StreamHandler.emit(self, myrecord)

def get_stderr(level=None):
  ch = ColoredConsoleHandler()
  ch.setFormatter (logging.Formatter ('[%(processName)-13s] '\
    '%(relativeCreated)7.0f us %(levelname)s ' \
    '%(filename)s:%(lineno)-4i ' \
    '- %(message)s'))
  level = level if level != None else logging.INFO # default
  if level != None:
    ch.setLevel(level) # default level
  return ch

def write (channel='', msg=''):
  if isinstance(msg, list):
    # XXX use pprint or similar
    for v in msg:
      line='[%s]: %s' % (channel if channel else '?', v.strip('\r\n'))
      logger.info(line)
  else:
    line='[%s]: %s' % (channel if channel else '?', str(msg).strip('\r\n'))
    logger.info(line)

#def dowrite(channel, msg, linesep):
#  PAGE=24
#  LENGTH=3
#  fpath=db.cfg.log_file
#  if os.path.isfile(fpath) and os.stat(fpath).st_size > (pow(1024,2)*db.cfg.log_rotate):
#    # only rotate 1 file back for now
#    if os.path.exists(fpath+'.1'):
#      os.remove(fpath+'.1')
#    os.rename(fpath, fpath+'.1')

#  # store to internal database
#  # keep only 1024 most recent for now
#  db.lock()
#  idx = timenow()
#  while db.logfile.has_key(idx):
#    idx += .000001
#  db.logfile[idx] = (channel and channel or '?', msg)
#  db.commit()
#  db.unlock()
#  if len(db.logfile) > (PAGE*LENGTH+1):
#    db.lock()
#    for idx in db.logfile.keys()[:PAGE*LENGTH]:
#      del db.logfile[idx]
#    db.commit()
#    db.unlock()
#
#  # should broadcast an event here, but circular
#  # import of engine prevents us
#  fo = open(fpath, 'a')
#  line='[%s]: %s%s' % (channel and channel or '?', msg, linesep,)
#  fo.write (line)
#  if not db.cfg.local_wfc:
#    # if there is no WFC screen, print log to stdout
#    sys.stdout.write(line)
#  fo.close ()
