# built-ins
import copy
import logging
import datetime
#import bbs.db

from bbs.session import getsession

last_line1 = ('','','','','','')
MAX_SIZE=10000 # N records to store (as openudb('eventlog'))
MAX_STEP=100 # cut N lines every buffer trim

class ColoredConsoleHandler(logging.StreamHandler):
  el = None
  fmt_txt = '%(levelname)s%(space)s%(handle)s' \
    '%(filename)s%(colon)s%(lineno)s%(space)s%(threadName)s' \
    '%(sep)s%(prefix)s%(message)s'

  def color_levelname (self, r):
    return r
    #r.levelname = '%s%s%s' % \
    #  (ansi.color(ansi.LIGHTRED) if r.levelno >= 50 \
    #  else ansi.color(*ansi.LIGHTRED) if r.levelno >= 40 \
    #  else ansi.color(*ansi.YELLOW) if r.levelno >= 30 \
    #  else ansi.color(*ansi.WHITE),
    #    r.levelname.title(),
    #  ansi.color())
    #return r

  def ins_handle(self, r):
    try:
      r.handle = '%s' % (getsession().handle + ' ' \
          if hasattr(getsession(), 'handle') and getsession().handle \
          else '')
    except KeyError:
      r.handle = ''
    return r

  def line_cmp(self, r):
    return (r.levelname, r.levelname, r.handle, r.filename, r.lineno, r.threadName)

  def line_blank(self, r):
    r.colon = r.space = r.sep = r.levelname = r.handle \
      = r.filename = r.lineno = r.threadName = ''
    return r

  def skip_repeat_line1(self, r):
    global last_line1
    cur_line1 = self.line_cmp(r)
    if cur_line1 == last_line1 \
    and last_line1[0].lower().strip() == 'error':
      # avoid repeating unnecessarily,
      r = self.line_blank(r)
    last_line1 = cur_line1
    return r

  def transform(self, src_record):
   src_record.colon = ':'
   src_record.space = ' '
   src_record.sep = ' - '
   src_record.prefix = ''
   return \
     (self.color_levelname \
       (self.skip_repeat_line1 \
         (self.ins_handle \
             (src_record))))

  def emit(self, src_record):
    # XXX hook in an event log database ... dont like this
    #if self.el is None:
    #  try:
    #    self.el = bbs.db.openudb('eventlog')
    #  except NameError, e:
    #    pass

    # trim database
    #if self.el is not None and len(self.el) > MAX_SIZE:
    #  largedb = copy.copy(self.el)
    #  for k in sorted(largedb.keys())[:-(MAX_SIZE-MAX_STEP)]:
    #    del self.el[k]

    dst_record = self.transform \
        (copy.copy(src_record))

    # write db record
#    if self.el is not None:
#      self.el.__setitem__ \
#          (datetime.datetime.now(), \
#          '%s %s %s:%s %s %s' % \
#            (dst_record.levelname, dst_record.handle,
#             dst_record.filename, dst_record.lineno,
#             dst_record.threadName, dst_record.getMessage(),))

    # emit to console
    logging.StreamHandler.emit \
      (self, dst_record)

def get_stderr(level=logging.INFO):
  stderr_format = logging.Formatter (ColoredConsoleHandler.fmt_txt)
  wscons = ColoredConsoleHandler()
  wscons.setFormatter (stderr_format)
  level = level if level != None else logging.INFO # default
  if level != None:
    wscons.setLevel(level) # default level
  return wscons
