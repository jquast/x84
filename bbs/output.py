from session import getsession

def delay(n):
    getsession().read_event([], seconds)

def echo(data):
    return getsession().write(data)

def oflush():
  import warnings
  warnings.warn('oflush() is deprecated', DeprecationWarning, 2)
