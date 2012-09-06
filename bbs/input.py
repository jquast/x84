from session import getsession
import ascii
from output import echo

def getch(timeout = None):
    (event, data) = getsession().read_event(events=['input'], timeout=timeout)
    return data

def readline(width, value = '', hidden = '', paddchar = ' ', events = [
    'input'], timeout = None, interactive = False, silent = False):
    (value, event, data) = readlineevent(width, value, hidden, paddchar, events, timeout, interactive, silent)
    return value

def readlineevent(width, value = '', hidden = '', paddchar = ' ', events = [
    'input'], timeout = None, interactive = False, silent = False):
  term = getsession().getterminal()

  if not hidden and value:
    echo (value)
  elif value:
    echo (hidden *len(value))

  while 1:
    event, char = getsession().read_event(events, timeout)

    # pass-through non-input data
    if event != 'input':
      data = char
      return (value, event, data)

    data = None
    print repr(char)
    if char == term.KEY_EXIT:
      return (None, 'input', data)

    elif char == term.KEY_ENTER:
      return (value, 'input', '\n')

    elif char == term.KEY_BACKSPACE:
      if len(value) > 0:
        value = value [:-1]
        echo (ascii.bs + paddchar + ascii.bs)

    elif isinstance(char, int):
      pass # unhandled keycode ...

    elif len(value) < width and ascii.isprint(ord(char)):
      value += char
      if hidden:
        echo (hidden)
      else:
        echo (char)

    elif not silent:
      echo (ascii.bel)
    if interactive:
      return (value, 'input', None)

