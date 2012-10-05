import warnings

from session import getsession

def delay(n):
    getsession().read_event([], seconds)

def echo(data, encoding=None):
  if data is None or 0 == len(data):
    warnings.warn ('terminal capability not translated: %s%r' % \
        (encoding if encoding is not None \
        else '', data,), Warning, 2)
  if type(data) is bytes:
    warnings.warn('non-unicode: %s%r' % \
        (encoding if encoding is not None \
        else '', data,), UnicodeWarning, 2)
    return getsession().write \
        (data.decode(encoding if encoding is not None else 'iso8859-1'))

  assert encoding is not None, 'just send unicode'
  # thanks for using unicode !
  return getsession().write (data)

def oflush():
  warnings.warn('oflush() is deprecated', DeprecationWarning, 2)
