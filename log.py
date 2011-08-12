import copy, logging
import session # log username, if available

# compatibility for old log.write()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fmt = '[%(threadName)-13s] %(relativeCreated)5dms %(levelname)s ' \
      '<%(handle)s> %(filename)s:%(lineno)-4i - %(message)s'
class ColoredConsoleHandler(logging.StreamHandler):
  # http://stackoverflow.com/questions/384076/how-can-i-make-the-python-logging-output-to-be-colored
  def emit(self, record):
    myrecord = copy.copy(record)
    if(myrecord.levelno >= 50): # CRITICAL / FATAL
      color = '\x1b[35m' # red
    elif(myrecord.levelno >= 40): # ERROR
      color = '\x1b[31m' # red
    elif(myrecord.levelno >= 30): # WARNING
      color = '\x1b[33m' # yellow
    else:
      color=''
    myrecord.levelname = '%s%-7s%s' % \
      (color, myrecord.levelname.capitalize(), '\x1b[0m' if color else '')
    myrecord.handle = sid = None
    try:
      myrecord.handle = session.sessions.getsession().handle
    except KeyError:
      pass
    logging.StreamHandler.emit(self, myrecord)

def get_stderr(level=None):
  ch = ColoredConsoleHandler()
  ch.setFormatter (logging.Formatter (fmt \
))
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
