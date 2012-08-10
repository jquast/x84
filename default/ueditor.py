"""
User Editor script for X/84, http://1984.ws
$Id: ueditor.py,v 1.3 2009/12/31 08:46:48 dingo Exp $

A simple user editor, for use by both sysops and non-sysop

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']

def init():
  global fields, hidefields
  # field keys not listed here are deletable
  fields = { \
    'groups':       ('ls','sysop'),
    'lastliner':    ('f', 'sysop'),
    'calls':        ('i', 'sysop'),
    'postrefs':     ('li','sysop'),
    'lastcall':     ('f', 'sysop'),
    'creationtime': ('f', 'sysop'),
    'location':     ('s', 'user'),
    'hint':         ('s', 'user'),
    'pubkey':       ('s', 'user'),
    'password':     ('s', 'user'),
  }
  # these fields are not modifable
  hidefields = ['saved', 'handle']

def main(editing_user=None):

  max_input = 2048

  def getfield(userKeys):
    echo ('\r\nField id [0-%s]: ' % (len(userKeys)-1),)
    x = readline(3)
    echo ('\r\n')
    try: id = int(x)
    except: return None
    if id > len(userKeys)-1 or id < 0:
      return None
    return userKeys[id]

  def displayField(handle, field):
    value = getuser(handle).get(field)
    echo ('\r\nValue: %r' % (value,))

  def coerceType(value, ft):
    s=','
    coerced=True
    if ft.startswith('l'):
      echo ('\r\nField type is list, seperator is: %s[   ]%s' \
         % (color(*LIGHTGREEN), color()) + '\b\b\b')
      s=readline(1, s)
      if not s: False, None
      if ft[1] == 's':
        value = value.split(s)
      elif ft[1] == 'i':
        try: value = [int(v) for v in value.split(s)]
        except ValueError: coerced=False
      elif ft[1] == 'f':
        try: value = [float(v) for v in value.split(s)]
        except ValueError: coerced=False
      elif ft[1] == 'b':
        value = value.lower().replace('true','1')
        value = value.lower().replace('false','0')
        try: value = [bool(v) for v in value.split(s)]
        except ValueError: coerced=False
      else:
        coerced=False
    elif ft == 's':
      None # no action necessary
    elif ft == 'i':
      try: value = int(value)
      except ValueError: coerced=False
    elif ft == 'f':
      try: value = float(value)
      except ValueError: coerced=False
    elif ft == 'b':
      value = value.lower().replace('true','1')
      value = value.lower().replace('false','0')
      value = bool(value)
    else:
      coerced=False
    return coerced, value

  def setfield(handle, field):
    if field in fields:
      fieldType = fields[field][0]
    else:
      # try to guess field type using existing value
      value = getuser(handle).get(field)
      fieldType = ''
      if type(value) == list and len(list):
        value, fieldType = value[0], 'l'
      if type(value) == str: fieldType += 's'
      elif type(value) == int: fieldType += 'i'
      elif type(value) == bool: fieldType += 'b'
      elif type(value) == float: fieldType += 'f'
      if not fieldType or fieldType == 'l':
        echo('\r\n%sCould not determine field type: %s%s' \
          % (color(*LIGHTRED), color(), type(getuser(handle).get(field))))
        return False
    echo ('\r\nEnter value (%s): ' % fieldType)
    newValue = readline (max_input)
    success, newValue = coerceType(newValue, fieldType)
    if not success:
      echo ('\r\nFailed to coerce value to type')
      return False
    echo ('\r\nOld value is: %r' % (getuser(handle).get(field),))
    echo ('\r\nNew value is: %r' % (newValue,))
    echo ('\r\n\r\n save? [%sn%s] ' % (color(*LIGHTGREEN), color()))
    k = readkey()
    if k.lower() == 'y':
      getuser(handle).set(field, newValue)
      return True
    return False

  def getfieldtype():
    echo ('\r\n\r\n[l*] list, * is any of the following:')
    echo ('\r\n[s] string')
    echo ('\r\n[i] integer')
    echo ('\r\n[b] boolean')
    echo ('\r\nField type: ')
    ftype = readline(3).strip()
    if (ftype.startswith('l') and not ftype[1:] in ['s','i','b']) \
    or not ftype in ['s','i','b']:
      return None
    return ftype.lower()

  def isEditable(key):
    if isSysop:
      return True
    return not key in fields or fields[key][1] == 'user'

  def isDeletedable(key):
    return not key in fields

  session = getsession()
  isSysop = 'sysop' in getuser(session.handle).groups

  getsession().activity = 'user editor: handle'
  echo (cls() + color() + cursor_show())
  showfile ('art/ueditor.asc')
  echo ('\r\n')
  if editing_user:
    editing_user= finduser(editing_user)
    if not isSysop and editing_user != handle():
      echo (pos(20, 13) + 'You must be in the sysop group')
      inkey ()
      return
  if not editing_user:
    editing_user = session.handle

  def help():
    echo ('\r\n')
    echo ('[l] list fields\r\n')
    echo ('[v] value display\r\n')
    echo ('[m] modify field\r\n')
    if isSysop:
      echo ('[d] delete field\r\n')
      echo ('[a] add field\r\n')
      echo ('[c] change user\r\n')
    echo ('[?] help\r\n')
    echo ('[q] quit')

  help ()

  while True:
    userKeys = getuser(editing_user).keys()
    for hide in hidefields:
      if hide in userKeys: userKeys.remove(hide)
    session.activity = 'editing user (' + editing_user + ')'
    echo (color() + '\r\n\r\n')
    echo (session.activity)
    echo (color(*DARKGREY) + ' --' +  color(*LIGHTRED) + '> ' + color())
    k = readkey()
    echo ('\r\n')
    if k in ['h','?']:
      help()
    if k == 'q':
      break
    elif k == 'l':
      roFields=False
      for n, key in enumerate(userKeys):
        echo ('\r\n %2s. %s' % (n, key))
        if not isEditable(key):
          echo (color(*LIGHTRED) + ' *' + color())
      echo ('\r\n    ' + color(*LIGHTRED) + '*' + color() + ' read-only field')
      echo ('\r\n')
    elif k == 'v':
      viewfield = getfield (userKeys)
      if not viewfield: continue
      displayField (editing_user, viewfield)
    elif k == 'm':
      modfield = getfield (userKeys)
      if not modfield: continue
      if not isEditable(modfield):
        echo ('\r\n' + color(*LIGHTRED) + 'you may not edit this field!')
        continue
      echo ('\r\nModifying field: %s\r\n' % (modfield,))
      if setfield (editing_user, modfield):
        echo ('\r\n %s*%s Saved' % (color(*LIGHTGREEN), color()))
    elif isSysop and k == 'a':
      echo ('\r\nField name: ')
      field = readline(12).strip()
      if not field: continue
      if getuser(editing_user).has_key(field):
        echo ('\r\n' + color(*LIGHTRED) + 'field already exists!')
        continue
      fieldType = getfieldtype ()
      if not fieldType: continue
      echo ('\r\nEnter value (%s): ' % (fieldType,))
      newValue = readline (max_input)
      success, newValue = coerceType(newValue, fieldType)
      if not success:
        echo ('\r\nFailed to coerce value to type')
        continue
      echo ('\r\nNew value is: %r' % (newValue,))
      echo ('\r\n\r\n save? [%sn%s] ' % (color(*LIGHTGREEN), color()))
      k = readkey()
      if k.lower() == 'y':
        getuser(editing_user).set(field, newValue)
        echo ('\r\n %s*%s Saved' % (color(*LIGHTGREEN), color()))
    elif isSysop and k == 'd':
      delfield = getfield (userKeys)
      if not delfield: continue
      echo ('\r\n\r\nDeleting field: %s\r\n' % (delfield,))
    elif isSysop and k == 'c':
      echo ('\r\n\r\nFind user [' + ' '*int(cfg.get('nua','max_user')) + ']' +
          '\b'*(int(cfg.get('nua','max_user'))+1))
      find = finduser(readline(int(cfg.get('nua','max_user'))))
      if find:
        echo ('\r\n\r\nNew user: %s' % (find,))
        editing_user = find
        continue
      else:
        echo ('\r\n\r\nUser not found')
    else:
      echo ('\r\n' + color(*LIGHTRED) + 'bad key' + color() + ', %r' % (k,) + '\r\n')
      help()
  return

