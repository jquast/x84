# built-ins
import copy
import logging

# locals
import ansi
import session

last_line1 = ('','','','','')

class ColoredConsoleHandler(logging.StreamHandler):
  fmt_txt = '%(levelname)s%(space)s%(handle)s' \
    '%(filename)s:%(lineno)s%(space)s%(threadName)s' \
    '%(linesep)s%(prefix)s%(message)s'
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
        (session.sessions.getsession().handle \
          if hasattr(session.sessions.getsession(), 'handle') \
          and session.sessions.getsession().handle is not None \
          else '^_*')
    except KeyError:
      r.handle = ''
    return r

  def skip_repeat_line1(self, r):
    return r
#    global last_line1
#    r.prefix = ''
#    r.space = ' '
#    r.linesep = '\n'
#    # unpack
#    cmp_levelname, cmp_handle, cmp_filename, cmp_lineno, cmp_threadName \
#      = copy.copy(last_line1) if last_line1 is not None else ('','','','','',)
#    last_line1 = (r.levelname, r.handle, r.filename, r.lineno, r.threadName)
#    # compare
#    if cmp_levelname == r.levelname and \
#       cmp_handle == r.handle and \
#       cmp_threadName == r.threadName and \
#       cmp_filename == r.filename:
#         if cmp_lineno == r.levelno:
#           r.prefix = 'a'
#         else:
#           r.prefix = '%sx:z%s ==> ' % (r.filename, r.lineno)
#         r.levelname=r.handle=r.filename=r.threadName=''
#         r.prefix = r.linesep = r.space = ''
#    return r

  def transform(self, src_record):
   src_record.space = ' '
   src_record.linesep = '\t'
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
