"""
String helper functions for X/84 (formerly 'The Progressive') BBS.
"""
from curses.ascii import ESC, isdigit
import re
pANS_PIPE = re.compile(r'(\|\d\d)')

def chompn (s):
  """
    This chomp utility is unique for its purpose. firstly, it removes only
    trailing \\n and \\r characters, and replaces single \\r's with \\r\\n
  """
  s = s.rstrip()
  def cr(n, c, s):
    if n < len(s) and c == '\x0a' and s[n+1] != '\x0d':
      return '\x0a\x0d'
    else: return c
  return ''.join([cr(n, c, s) for n, c in enumerate(s)])

def pstr(pascal_string):
  """ Return string of pascal string bytes, where
      under pascal, *p = address; *p = (int)(strlen(string)) """
  width = int(ord(pascal_string[0])) +1
  return pascal_string[1:width]

def strpadd(string, paddlen=0, align='left', ch=' ', trim=True):
  """ This function padds strings with blanks (for painting over
      ghost data or background colors) so that the displayed width is
      paddlen, and aligned by variable align. By default, strings will
      be cropped to paddlen when trim=True. ANSI strings are correctly
      measured and are safe to pass here.
  """
  # make string padd-safe
  string = seqc(string, ch=ch)
  # printable ansi length of string
  alen = ansilen(string)
  # create padding
  if paddlen >= alen:
    padd = (ch*(paddlen - alen))
  elif trim:
    string, padd = chompto(string, paddlen+1), ''
  # return aligned text
  if align == 'center':
    return padd[:-len(padd)/2] + string + padd[-len(padd)/2:]
  elif align == 'left':
    return string +padd
  elif align == 'right':
    return padd +string
  else:
    return '(bad alignment)'

def maxanswidth(dataset, ceil=None):
  " return size of largest line of ansi in art, trimmed to max "
  return min(ceil,max([ansilen(l) for l in dataset])) \
      if ceil is not None \
      else max([ansilen(l) for l in dataset])

def implode (array, delimiter=', ', andstr=None):
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
      if andstr is not None and len(array) > 1:
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
# XXX TODO: Use maze's internationalized version ..
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
  if years > 0: return '%3s%-3s' % (str(years)+'y', str(weeks)+'w',)
  if weeks > 0: return '%3s%-3s' % (str(weeks)+'w', str(days)+'d',)
  if days > 0: return '%3s%-3s' % (str(days)+'d', str(hours)+'h',)
  elif hours > 0: return '%3s%-3s' % (str(hours)+'h', str(mins)+'m',)
  elif mins > 0: return '%3s%-3s' % (str(mins)+'m', str(int(secs))+'s',)
  else:
    fmt = '%.'+str(precision)+'f s'
    return fmt % secs

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

  if not slen or seq[0] != chr(ESC): return False

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

def seqp(src, term):
  """Return ansi string given string with |03 pipe codes ..."""
  tgt = ''
  ptr, match = 0, None
  for match in pANS_PIPE.finditer(src):
    value = int(src[match.start()+len('|'):match.end()], 10)
    tgt += src[ptr:match.start()] + term.color(value)
    ptr = match.end()
  if match is None:
    return src # as-is
  return ''.join((tgt, src[match.end():], term.normal))

def seqc(string, ch=' '):
  " Replace string with \\033[nnC replaced by ' '*nn.  "
  # TODO: regexp's
  next, nstring = 0, ''
  for n in range(0,len(string)):
    cs, clen, ls = chkseq(string[n:]), 0, 0
    if cs:
      clen = chkpadd(string[n:]) # nn of ansi.right('nn'), if any
    if clen:
      next = n + cs
      nstring += ch*(clen)
    elif ls:
      next = n + ls
    elif cs and isbad(string[n:]):
      next = n + cs
    elif next <= n:
      nstring += string[n]
  return nstring

def chkpadd(seq):
  """ Returns int('nn') in CSI sequence \\033[nnC
      for use with replacing ansi.right(nn) with
      printable characters. prevents bleeding in
      scrollable windows """
  # TODO: regexp's
  slen = len(seq)
  if not slen: return 0
  if not seq[0] == chr(ESC): return 0
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

def chkseq(seq):
  """ Return non-zero for string 'seq' that begins with an ansi sequence.
      Value returned is bytes until sequence is complete.  This can be used
      as a 'next' pointer to skip past sequences
  """

  def badseq(msg=''):
    # parse error, or user-supplied string error
    fp=open('debug_seq.log', 'w')
    fp.write(seq)
    fp.close()
    raise "Bad Sequence: " + repr(seq) + ':' + msg

  slen = len(seq)

  if not slen or seq[0] != chr(ESC): return 0

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

def ansilen(string, max=0):
  """ Return the printed length of a string that contains
      (some types) of ansi sequences. Although accounted for,
      strings containing sequences such as cls() will not
      give accurate returns. """

  # equivalent of len() call if no ansi sequences exist
  if not chr(ESC) in string:
    return len(string)

  # next points to first character beyond next ansi string
  # width is returned length of ansi string as displayed (in theory)
  next, width = 0, 0
  for n in range(0, len(string)):
    width += chkpadd(string[n:])
    # if not within bounds of ansi sequence
    if next == n:
      # point next past ansi seq or current pos if no ansi seq present
      next = n + chkseq(string[n:])
    if next <= n:
      width += 1
      if max and width >= max:
        return width
      # point next past ansi seq or next pos if no ansi seq present
      next = n + chkseq(string[n:]) +1
  return width
