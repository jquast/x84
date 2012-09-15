from session import getsession

def delay(n):
    getsession().read_event([], seconds)

def echo(data, encoding=None):
    return getsession().write(data, encoding)

def oflush():
  import warnings
  warnings.warn('oflush() is deprecated', DeprecationWarning, 2)
