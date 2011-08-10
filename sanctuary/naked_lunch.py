__author__ = 'Jeffrey Quast <dingo@1984.ws>\nJohannes Lundberg <johannes.lundberg@gmail.com>'
__copyright__ = 'Copyright (c) 2006, 2011 Jeffrey Quast, Johannes Lundberg'
__license__ = 'ISC'
__url__ = 'http://1984.ws'

def seqc(seq, ch=' ', stripnl=True):
  " Replace string with \\033[nnC replaced by ' '*nn.  "
  # TODO: regexp's
  next, n_seq = 0, ''
  for n in range(len(seq)):
    cs, clen, ls = chkseq(seq[n:]), 0, 0
    if cs:
      clen = chkpadd(seq[n:]) # nn of ansi.right('nn'), if any
    if clen:
      next = n + cs
      n_seq += ch*(clen)
    elif ls:
      next = n + ls
    elif cs and isbad(seq[n:]):
      next = n + cs
    elif stripnl and isnl(seq[n]):
      next = n + 1
    elif next <= n:
      n_seq += seq[n]
  return n_seq

def strpadd(seq, paddlen=0, align='left', ch=' ', trim=True):
  """ This function padds strings with blanks (for painting over
      ghost data or background colors) so that the displayed width is
      paddlen, and aligned by variable align. By default, strings will
      be cropped to paddlen when trim=True. ANSI strings are correctly
      measured and are safe to pass here.
  """
  # make string padd-safe
  seq = seqc(seq, ch=ch)
  # printable ansi length of seq
  alen = len(seq)
  # create padding
  if paddlen >= alen:
    padd = (ch*(paddlen - alen))
  elif trim:
    seq, padd = chompto(seq, paddlen+1), ''
  # return aligned text
  if align == 'center':
    return padd[:-len(padd)/2] + seq + padd[-len(padd)/2:]
  elif align == 'left':
    return seq +padd
  elif align == 'right':
    return padd +seq
  else:
    return '(bad alignment)'

def cleanb (seq):
  # XXX regexp
  l = len(seq)
  swp = ''
  for ch in seq:
    if ch == '\b':
      # \b moves carriage back
      swp = swp[:-1]
    else:
      swp += ch
  return swp

def chompto (seq, maxlen, mark=''):
#  seq = chompn(seq)
  seq = cleanb(seq)

  # make maxlen measure up to printable length
  next, width = 0, 0
  for n in range(0, len(seq)):
    width += chkpadd(seq[n:]) # add n to width in sequence ansi.right(n)
    if next == n: next = n + chkseq(seq[n:])
    if next <= n:
      width += 1
      next = n + chkseq(seq[n:]) +1
    if width == maxlen:
      maxlen = n
      break
  return 

def chkpadd(seq):
  """ Returns int('nn') in CSI sequence \\033[nnC
      for use with replacing ansi.right(nn) with
      printable characters. prevents bleeding in
      scrollable windows """
  # TODO: regexp's
  slen = len(seq)
  if not slen: return 0
  if not seq[0] == esc: return 0
  if not slen >= 4: return 0
  if not seq[1] == '[': return 0
  if not isdigit(ord(seq[2])): return 0
  # sequence is CSI + str(int(cols)) + 'C'
  p = 2
  while isdigit(ord(seq[p])) and slen > p:
    p +=1
  if not seq[p] == 'C':
    return 0
  return int(seq[2:p])

def chkseq(seq, nlcounts=True):
  # XXX TODO: REGEXP
  """ Return non-zero for string 'seq' that begins with an ansi sequence.
      Value returned is bytes until sequence is complete.  This can be used
      as a 'next' pointer to skip past sequences
      Newlines count as a 1-width sequence unless 'nlcounts' is set to False."""

  def badseq(msg=''):
    # parse error, or user-supplied string error
    fp=open('debug_seq.log', 'w')
    fp.write(seq)
    fp.close()
    raise "Bad Sequence: " + repr(seq) + ':' + msg

  slen = len(seq)

  if not slen or seq[0] != esc: return 0

  # newline
  if nlcounts and isnl(seq[0]):
    return 1

  # all sequences are at least 2 (\033c)
  if slen < 2: badseq('short length (2)')

  # reset
  if seq[1] == 'c': return 2

  # all sequences are at least 3 (\033,#,8)
  if slen < 3: badseq('short length (3)')

  # fill screen (DEC)
  if seq[1] == '#' and seq[2] == '8': return 3

  # set charset (DEC/Latin/PCDOS)
  elif seq[1] == '(' and seq[2] in ['U','B','0']: return 3

  # CSI
  elif seq[1] == '[':
    p1 = 2

    # home/clear screen/reset/save pos/restore pos
    if seq[p1] in ['H','J','m','s','u']: return p1 + 1

    # positions
    if ord(seq[p1]) >= ord('A') \
    and ord(seq[p1]) <= ord('F'):
      return p1 + 1

    # all sequences are at least 4 (\033,[,0,m)
    elif slen < 4: badseq('short length (4)')

    # CSI + '?25(h|l)' # show|hide
    elif seq[p1] == '?':
      p2 = p1+1
      while (isdigit(ord(seq[p2]))): p2+=1
      if not seq[p2] in ['h','l']:
        badseq('? followed illegaly')
      return p2+1

    # SGR
    elif isdigit(ord(seq[p1])):
      p2 = p1
      while (isdigit(ord(seq[p2]))): p2+=1

      # multi-attribute SGR '[01;02(..)'(m|H)
      while seq[p2] == ';':
        p2 += 1
        try:
          while (isdigit(ord(seq[p2]))): p2+=1
        except IndexError:
          badseq('out of range in multi-attribute SGR')
        # 'H' pos, 'm' color;attr
        if seq[p2] in ['H','m']:
          return p2 +1
        elif seq[p2] == ';':
          # multi-attribute SGR
          continue
        else:
          badseq('illegal multi-attribute sgr')
      # single attribute SGT '[01(A|B|etc)'
      if seq[p2] in ['A','B','C','D','E','F','G','J','K','S','T','H','m']:
        # single attribute, up/down/right/left/bnl/bpl,pos,cls,cl,pgup,pgdown,color,attribute
        return p2 +1
      else: badseq('illegal single value')
    else: badseq('illegal nondigit')
  # unknown...
  badseq('unknown sequence')


NL = '\n'
MASK = ' '

class AnsiArt(str):
  def __len__(self):
    """ Return the printed width of a string that contains
        (most kinds) of ansi sequences. Strings containing
        sequences such as cls() or other vertical distance
        modifiers will not give accurate returns.

        For two-dimensional graphing distances, use the
        self.width() and self.height() methods, otherwise
        this works fine for horizontal distancing """

    s = self.__str__()
    l = s.__len__()
    if not esc in s:
      return l

    next, w = 0, 0
    for n in range(l):
      w += chkpadd(s[n:])
      # if not within bounds of ansi sequence
      if next == n:
        # point next past ansi seq or current pos if no ansi seq present
        next = n + chkseq(s[n:])
      if next <= n:
        w += 1
        # point next past ansi seq or next pos if no ansi seq present
        next = n +chkseq(s[n:]) +1
    return w

  def width(self, max=-1):
    """ return row with maximum width of 2d art, or the length
        of the first row above parameter 'max', when specified.  """
    w = 0
    for l in [row.__len__() for n,row in self.rows()]:
      w = l if l > w else w
      if max != -1 and w >= max:
        break
    return w

  def height(self):
    " return the number of rows (how many NL characters)"
    return sum([1 for ch in self if ch == self.NL]) \
      +1 # first line counts

  def grow(self, height, width):
    if height < 0:
      raise TypeError, 'grow height must be positive integer: %s' % (height,)
    if width < 0:
      raise TypeError, 'grow width must be positive integer: %s' % (height,)
    if self.height() < height:
      self.__add__('\n' * height-self.height())
    if self.width() < height:
      for idx, row in [(n self.row(n)
      for idx_row in self.height():
        row = self.row(idx_row)
        self.changeRow self.padd(row)



  def row(self, n):
    return self.split(NL, n) [n-1]

  def rows(self):
    # return dictionary of rows, indexed by their row number
    return dict([(n, self.row(n)) for n in self.height()])

  def charAt(self, y, x, n=1):
    # return characters from string for printing at the y,x position,

  def modifyChar(self, y, x, chars='')
    # modify character(s) at y, x position
    seq = self.row(y)

  def modifyRow(self, n, chars='')
    # modify row at y position

  def blank(self, y_1, x_1, y_2, x_2):
    # blank character(s) at bounding box (y_1, x_1), (y_2, x_2)
  def highlight(self, y_1, x_1, y_2, x_2):
    # ansi.REVERSE the characters from y_1, x_1 through y_2, x_2
  def 




deps = ['bbs']
import StringIO

#import random
#from ascii import *

def implode (array, delimiter=', ', andstr=' and '):
  """ Inspired by php's implode function: pass a list of strings as 'array',
     and a single string of items split by delimiter are returned. Optionaly,
     the andstr may be set with an english-style sequence to be used before
     last array element. All items in array must be of type string """
  foutstr = ''

  # saftey checks
  if not isinstance(array, list) \
    and isinstance(array, str):
      return str
  elif isinstance(array, list) \
    and len(array) == 0:
      return ''
  elif array == None:
    return ''
  elif len(array) == 1:
    return array[0]

  for x, item in enumerate(array):
    if x < len(array)-2:
      foutstr = foutstr + item + delimiter
    elif x == len(array)-1:
      # last item
      if andstr and len(array) > 1:
        # use 'and' instead of delimiter (english style)
        return foutstr + andstr + item
      else:
        # return as normal
        return foutstr + delimiter + item
    else:
      # second to last item
      foutstr = foutstr + item
  return foutstr

def strand (array):
  return implode(array, delimiter=', ', andstr=' and ')

## human readable string routines

def bytesize(size):
  """ Converts filesize bytes of type numeric to small string of
      number + magnitude (b/K/M/G/T) to represent bytesize """
  bs = 1024
  if size < bs:
    return str(size) +'b'
  elif size >= bs and size < pow(bs,2):
    return str(size /bs) +'K'
  elif size >= pow(bs,2) and size < pow(bs,3):
    return str(size /pow(bs,2)) +'M'
  elif size >= pow(bs,3) and size < pow(bs,4):
    return str(size /pow(bs,3)) +'G'
  elif size >= pow(bs,4):
    return str(size /pow(bs,4)) +'T'
  else: return str(size) +'?'

def filetime(file):
   " Return 'm/d/y' of file "
   return time.strftime ('%m/%d/%y', time.localtime (os.path.getctime(file)))

def asctime(secs, precision=0):
  """
  Pass float or int in seconds, and return string of 0d 0h 0s format,
  but only the two most relative, fe:
  asctime(126.32) returns 2m6s,
  asctime(10.9999, 2)   returns 10.99s
  """
  # split by days, mins, hours, secs
  years, weeks, days, mins, hours = 0,0,0,0,0

  mins,  secs  = divmod(secs,  60)
  hours, mins  = divmod(mins,  60)
  days,  hours = divmod(hours, 24)
  weeks, days  = divmod(days,   7)
  years, weeks = divmod(weeks, 52)

  years, weeks, days, hours, mins \
    = int(years), int(weeks), int(days), int(hours), int(mins)

  # return printable string
  if years > 0:
    return strpadd (str(years)+'y',3,'left') \
         + strpadd (str(weeks)+'w',3,'right')
  if weeks > 0:
    return strpadd (str(weeks)+'w',3,'left') \
         + strpadd (str(days)+'d',3,'right')
  if days > 0:
    return strpadd (str(days)+'d',3,'left') \
         + strpadd (str(hours)+'h',3,'right')
  elif hours > 0:
    return strpadd (str(hours)+'h',3,'left') \
         + strpadd (str(mins)+'m',3,'right')
  elif mins > 0:
    secs = int(secs)
    return strpadd (str(mins)+'m',3,'left') \
         + strpadd (str(secs)+'s',3,'right')

  return '%.'+str(precision)+'f s' % secs

## ANSI string routines

def isbad(seq):
  """ Return True if sequence is unhealthy for use with padding.
      Unhealthy sequences are generaly movement sequences unaccounted for,
      or sequences that put the terminal in undesirable state.
  """
  # XXX dont like having to sync up with seqchk, someway to merge? XXX
  def badseq(msg=''):
    # parse error, or user-supplied string error
    fp=open('debug_seq.log', 'w')
    fp.write(seq)
    fp.close()
    raise "Bad Sequence: " + repr(seq) + ':' + msg

  slen = len(seq)

  if not slen or seq[0] != esc: return False

  # all sequences are at -least- 3 (\033,#,8)
  if slen < 2: badseq('short length (2)')

  # reset
  if seq[1] == 'c': return True

  # all sequences are at least 3 (\033,#,8)
  if slen < 3: badseq('short length (3)')

  # fill screen (DEC)
  if seq[1] == '#' and seq[2] == '8': return True

  # set charset (DEC/Latin/PCDOS)
  elif seq[1] == '(' and seq[2] in ['U','B','0']: return True

  # CSI
  elif seq[1] == '[':
    p1 = 2

    # home/clear screen/reset/save pos/restore pos
    if seq[p1] in ['H','J','s','u']: return True
    if seq[p1] in ['m']: return False

    # positions
    if ord(seq[p1]) >= ord('A') \
    and ord(seq[p1]) <= ord('F'):
      return True

    # all sequences are at least 4 (\033,[,0,m)
    elif slen < 4: badseq('short length (4)')

    # CSI + '?25(h|l)' # show|hide
    elif seq[p1] == '?':
      p2 = p1+1
      while (isdigit(ord(seq[p2]))): p2+=1
      if not seq[p2] in ['h','l']:
        badseq('? followed illegaly')
      return False

    # SGR
    elif isdigit(ord(seq[p1])):
      p2 = p1
      while (isdigit(ord(seq[p2]))): p2+=1

      # multi-attribute SGR '[01;02(..)'(m|H)
      while seq[p2] == ';':
        p2 += 1
        try:
          while (isdigit(ord(seq[p2]))): p2+=1
        except IndexError:
          badseq('out of range in multi-attribute SGR')
        # 'H' pos, 'm' color;attr
        if seq[p2] == 'H': return True
        elif seq[p2] == 'm': return False
        elif seq[p2] == ';':
          # multi-attribute SGR
          continue
        else:
          badseq('illegal multi-attribute sgr')

      # single attribute SGT '[01(A|B|etc)'
      if seq[p2] in ['A','B','C','D','E','F','G','J','K','S','T','H']:
        # single attribute, up/down/right/left/bnl/bpl,pos,cls,cl,pgup,pgdown
        return True
      elif seq[p2] in ['m']: return False
      else: badseq('illegal single value:'+ seq[p2]+'.')
    else: badseq('illegal nondigit')
  badseq('unknown ansi sequence')

class WordSmith(string):
  def __len__(self):
    # 
  >>> dir('s')
  ['__add__',
  '__class__',
  '__repr__',
  '__rmod__', '__rmul__', '__setattr__', '__sizeof__',
  '__str__', '__subclasshook__', '_formatter_field_name_split',
  '_formatter_parser', 'capitalize', 'center', 'count', 'decode', 'encode', 'endswith', 'expandtabs', 'find', 'format', 'index', 'isalnum', 'isalpha', 'isdigit', 'islower', 'isspace', 'istitle', 'isupper', 'join', 'ljust', 'lower', 'lstrip', 'partition', 'replace', 'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit', 'rstrip',
  'split', 'splitlines', 'startswith', 'strip', 'swapcase', 'title', 'translate', 'upper', 'zfill']

deps = ['bbs']






