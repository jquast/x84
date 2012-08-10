# built-ins
import copy
import logging

# locals
import ansi
import session

last_line1 = ('','','','','')

class ColoredConsoleHandler(logging.StreamHandler):
  fmt_txt = '%(levelname)s%(space)s%(handle)s' \
    '%(filename)s%(colon)s%(lineno)s%(space)s%(threadName)s' \
    '%(sep)s%(prefix)s%(message)s'
  def color_levelname (self, r):
    #r.levelname = r.levelname.strip()
    r.levelname = '%s%s%s' % \
      (ansi.color(ansi.LIGHTRED) if r.levelno >= 50 \
      else ansi.color(*ansi.LIGHTRED) if r.levelno >= 40 \
      else ansi.color(*ansi.YELLOW) if r.levelno >= 30 \
      else ansi.color(*ansi.WHITE),
        r.levelname.title(),
      ansi.color())
    return r

  def modify_threadName(self, r):
    r.threadName = 'twisted-%s' % (r.threadName.split('-')[-1]) \
      if 'twisted' in r.threadName \
        else r.threadName
    return r

  def ins_handle(self, r):
    try:
      r.handle = '%s' % \
        (session.sessions.getsession().handle + ' ' \
          if hasattr(session.sessions.getsession(), 'handle') \
          and session.sessions.getsession().handle \
          else '^_* ')
    except KeyError:
      r.handle = ''
    return r

  def line_cmp(self, r):
    return (r.levelname, r.handle, r.filename, r.lineno, r.threadName)
  def line_blank(self, r):
    r.colon = r.space = r.sep = r.levelname = r.handle \
      = r.filename = r.lineno = r.threadName = ''
    return r

  def skip_repeat_line1(self, r):
    global last_line1
    cur_line1 = self.line_cmp(r)
    if cur_line1 == last_line1:
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
     (self.skip_repeat_line1 \
       (self.color_levelname \
         (self.ins_handle \
           (self.modify_threadName \
             (src_record)))))

  def emit(self, src_record):
    logging.StreamHandler.emit \
      (self, self.transform \
        (copy.copy(src_record)))

def get_stderr(level=logging.INFO):
  stderr_format = logging.Formatter (ColoredConsoleHandler.fmt_txt)
  wscons = ColoredConsoleHandler()
  wscons.setFormatter (stderr_format)
  level = level if level != None else logging.INFO # default
  if level != None:
    wscons.setLevel(level) # default level
  return wscons
