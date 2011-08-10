# based off ascii(7)

nul = '\000'
soh = '\001'
stx = '\002'
etx = '\003'
eot = '\004'
enq = '\005'
ack = '\006'
bel = '\007'
bs = '\010'
ht = '\011'
nl = '\012'
vt = '\013'
np = '\014'
cr = '\015'
so = '\016'
si = '\017'
dle = '\020'
dc1 = '\021'
dc2 = '\022'
dc3 = '\023'
dc4 = '\024'
nak = '\025'
syn = '\026'
etb = '\027'
can = '\030'
em = '\031'
sub = '\032'
esc = '\033'
fs = '\034'
gs = '\035'
rs = '\036'
us = '\037'
sp = '\040'
delete = '\177' # 'del' is reserved keyword!

# based off <ctype.h>

"Character comparators"
def isprint(c):
   """ return true if c is printable character """
   return (c > 31 and c < 127)
def isgraph(c):
   """ return true if c is non-control character """
   return (c > 31 and c < 255)
def iscntrl(c):
   """ return true if c is control character """
   return (c < 32)
def ispunct(c):
   """ return true if c is punctuation character """
   return ((c > 32 and c < 48) or (c > 57 and c < 65) or (c > 90 and c < 97))
def islower(c):
   """ return true if c is lowercase alpha character """
   return (c > 96 and c < 123)
def isupper(c):
   """ return true if c is uppercase alpha character """
   return (c > 64 and c < 91)
def isdigit(c):
   """ return true if c is uppercase alpha character """
   return (c > 47 and c < 58)
def isalpha(c):
   """ return true if c is alpha character """
   return (isupper(c) or islower(c))
def isalnum(c):
   """ return true if c is alpha-numeric character """
   return (isalpha(c) or isdigit(c))
def isspace(c):
   """ return true if c is whitespace """
   return (c == ' ' or c == '\t')
def isnl(c):
   """ return true if c is newline character """
   return (c == '\n' or c == '\r')

"Character transformations"
def toascii(c):
   """ return c masked to ascii character """
   return (c & 0177)
def toupper(c):
   """ return c as upper-case character """
   return (c - 'a' + 'A')
def tolower(c):
   """ return c as lower-case character """
   return (c - 'A' + 'a')
