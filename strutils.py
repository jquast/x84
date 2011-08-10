"""
String helper functions for 'The Progressive' BBS.
(c) Copyright 2006, 2007 Jeffrey Quast
$Id: strutils.py,v 1.39 2009/05/26 14:18:21 dingo Exp $

These functions assist the manipulation of python strings (non-unicode!)
Also available are functions that assist the measurement and manipulation
of strings that contain ANSI escape sequences.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>\nJohannes Lundberg <johannes.lundberg@gmail.com>'
__contributors__ = []
__copyright__ = 'Copyright (c) 2006, 2007 Jeffrey Quast, Johannes Lundberg'
__license__ = 'ISC'
from ascii import *
import StringIO

## unicode transformations

def stoascii(string):
  """ Return only halfbyte (<127) of multibyte strings """
  ns = ''
  for ch in string:
    ns += chr(ord(ch) & 0177)
  return ns

## string manipulation

def chompn (s):
  """
    This chomp utility is unique for its purpose. firstly, it removes only
    trailing \\n and \\r characters, and replaces single \\x0a's with 
    \\x0a\\x0d
  """
  if not s:
    return ''

  while len(s) > 0 and (s[-1:] == '\n' or s[-1:] == '\r'):
    s= s[:-1]

  def cr(n, c, s):
    if n < len(s) and c == '\x0a' and s[n+1] != '\x0d': return '\x0a\x0d'
    else: return c
  return ''.join([cr(n, c, s) for n, c in enumerate(s)])

def trim(string, trimchars=['\n', '\r', '\t', ' '], which='both'):
  " Return string after (whitespace) characters from trimchars array "
  " have been removed from beginning and/or end of string, by specifying "
  " which='both', 'right', or 'left' "
  if which == 'both' or which == 'right':
    while len(string) > 0 and (right(string,1) in trimchars):
      string = string[:-1]
  if which == 'both' or which == 'left':
    while len(string) > 0 and (left(string,1) in trimchars):
      string = string[1:]
  return string

def chompto (string, maxlen, mark=''):
  """ If string is wider than maxlen, crop to maxlen with optional trailing
      mark, Use by pagers to ensure data is within a window. You may cut
      ansi art into slices, the use of mark is however not ansi sequence safe."""
  string = chompn(string)
  swp = ''
  for c in string:
    if c == '\b': swp = swp[:-1] # \b moves carriage back
    else: swp += c

  # make maxlen measure up to printable length
  next, width = 0, 0
  for n in range(0, len(swp)):
    width += chkpadd(swp[n:]) # add n to width in sequence ansi.right(n)
    if next == n: next = n + chkseq(swp[n:])
    if next <= n:
      width += 1
      next = n + chkseq(swp[n:]) +1
    if width == maxlen:
      maxlen = n
      break

  # return string fit to size
  if len(swp) > maxlen:
    if len(mark):
      return swp[:maxlen-len(mark)]+mark
    else:
      return swp[0:maxlen]
  return swp

def strip(string):
  " strip string of non-printable characters and trailing spaces "
  def endswith(string, ch):
    if len(string) > 0 and string[-1] == ch:
      return True
    return False
  newstring = ''
  for ch in string:
    # Keep the good stuff
    if isprint(ch):
      newstring += ch
    # Trailing spaces
    elif isspace(ch) and not endswith(newstring, ' '):
      newstring += ch
  # delete trailing spaces
  while len(newstring) > 0 and endswith(newstring, ' '):
    newstring = newstring[:-1]
  return newstring

def pstr(pascal_string):
  """ Return string of pascal string bytes, where
      under pascal, *p = address; *p = (int)(strlen(string)) """
  width = int(ord(pascal_string[0])) +1
  return pascal_string[1:width]

def insert(dataset, insertion, column):
  """ return dataset, with record 'insertion' inserted at index position column """
  return dataset[:column] \
       + insertion \
       + dataset[column:]

def replace(dataset, replacement, column):
  """ return dataset, with record 'insertion' replacing at index position column """
  return dataset[:column] \
       + replacement \
       + dataset[column +len(replacement):]

def remove(dataset, column, n=1):
  """ return dataset, with record at index position column removed from list """
  return dataset[:column] + dataset[column+n:]

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

## list<->string routines

def left(data, num):
  " return 'num' chunks of the beginning of sequence 'data' "
  return data[:num]

def right(data, num):
  " return 'num' chunks of the end of sequence 'data' "
  return data[-num:]

def maxwidth(dataset, max=None):
  " return size of largest record in dataset, trimmed to max "
  w = 1
  for record in dataset:
    ln = len(record)
    if ln > w:
      if max and ln >= max:
        w = max
        break
      w = ln
  return w

def maxanswidth(art, max=None):
  " return size of largest line of ansi in art, trimmed to max "
  w = 1
  for record in art:
    ln = ansilen(record)
    if ln > w:
      if max and ln >= max:
        w = max
        break
      w = ln
  return w

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

def seqc(string, ch=' ', stripnl=True):
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
    elif stripnl and isnl(string[n]):
      next = n + 1
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

def ansilen(string, max=0):
  """ Return the printed length of a string that contains
      (some types) of ansi sequences. Although accounted for,
      strings containing sequences such as cls() will not
      give accurate returns. """

  # equivalent of len() call if no ansi sequences exist
  if not esc in string:
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

#         /* 0  1  2  3  4  5  6  7 */
ansi2ega = [ 0, 4, 2, 6, 1, 5, 3, 7 ]
ega2ansi = [ 0, 4, 2, 6, 1, 5, 3, 7 ]

def textmem2ansi (textmem,width=80,height=24):
  " Builds a string of ANSI codes of the art in textmem "
  global codes
  global output

  attr = 0x07;
  spaces = 0;
  codes = 0;
  p = 0;

  output = StringIO.StringIO()
  out=output.write
  # Internal functions go here
  def pchar():
    return textmem[p]
  def pattr():
    return ord(textmem[p+1])
  def outint(d):
    out(str(d))
  #def outint(d):
  #  if (d>99): out(chr((d/100)%10+ord('0')));
  #  if (d>9):  out(chr((d/10)%10+ord('0')));
  #  out(chr(d%10+ord('0')));
  def code(d):
    global codes
    if(codes==0):
      codes=1;out('\x1B');out('[');
    else:
      out(';');
    outint(d);

  # Add a clearscreen at the top. */

  out('\x1B');out('[');out('H');
  out('\x1B');out('[');out('J');

  p = 0;
  for y in range(height):
    spaces = 0
    for x in range(width):
      if (pchar() == ' '):
        spaces += 1
      else:
        if (spaces):
          if (spaces > 4):
            out('\x1B');out('[');outint(spaces);out('C');
          else:
            for i in range(spaces):
              out(' ');
          spaces = 0
        if (pattr() != attr and pattr() != 0):
          codes = False;
          if ((attr & 0x08) and not (pattr() & 0x08)):
            code(0); attr = 0x07;
          elif ((attr & 0x08) == 0 and (pattr() & 0x08)):
            code(1);
          if ((attr & 0x07) != (pattr() & 0x07)):
            code(30+ega2ansi[(pattr()&0x07)]);
          if ((attr & 0x70) != (pattr() & 0x70)):
            code(40+ega2ansi[(pattr()&0x70)>>4]);
          attr = pattr();
          out('m');
        out(pchar());
      p += 2;
    out('\r');out('\n');

  return output.getvalue()
