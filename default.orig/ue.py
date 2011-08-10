# $Id: ue.py,v 1.5 2008/10/02 04:05:52 dingo Exp $
#
# user editor for prsv -- in the works...
#
# Copyright 2007 (c) Jeffrey Quast

deps = ['bbs']

# prompts
aus = 'Are you sure?'
euk = 'Enter User Key'
ekv = 'Enter Key Value'
kvt = 'Key value type?'
fpw = 39 # foll prompt width
ynlen = 13

def getuservalue(user, attr):
  if getuser(user).__dict__.has_key(attr):
    return getuser(user).__dict__[attr]
  else:
    return

def remove(obj, key):
  obj.pop(key)

def addnew(obj, key, value):
  obj[key] = value

def change(obj, key, value):
  if isinstance(obj[key], str):
    obj[key] = str(value)
  if isinstance(obj[key], int):
    obj[key] = int(value)
  if isinstance(obj[key], float):
    obj[key] = float(value)

def clear(obj, key):
  if isinstance(obj[key], str):
    change(obj, key, '')
  if isinstance(obj[key], int):
    change(obj, key, 0)
  if isinstance(obj[key], float):
    change(obj, key, 0.0)

def editdata(pager):
  echo (cursor_show() + color())
  pager.interactive, pager.edit = True, True
  pager.cursor_end (silent=True)
  pager.fixate ()
  while not pager.exit:
    key = inkey()
    if key == KEY.ENTER:
      break
    pager.run (key)
  echo (color())
  pager.interactive, pager.edit = False, False
  return pager.data()

def main(user=None):
  session.activity = 'user editor'

  # support copy and paste operations
  clipboard = None

  # override retrieve method of lightstepclass to create a userbrowsing class
  class userbrowserclass(lightstepclass):
    def retrieve(s, key):
      " retrieve function override: user data browser "
      user, attr = key[0], key[1]
      if s.depth == 0:
        # build and return users
        l = []
        for u in listusers():
          l.append (u.handle)
        return l
      if s.depth == 1:
        return getuser(user).__dict__.keys()
      elif s.depth == 2:
        return ['edit', 'paste', 'clear', 'delete', 'copy']
      else:
        print key
        return ['unknown','depth!']

  def cl():
    " clear status line "
    echo (color() + pos(vw.ans.x, lr.y) + ' '*vw.ans.w)

  def pl(string, color=bcolor(RED)+color(BLACK)):
    " print string in status line "
    echo (color + pos(vw.ans.x, lr.y) + strpadd(string,vw.ans.w,'center'))

  def confirm(ynbar):
    " confirm y/n bar "
    echo (bcolor(RED)+color(BLACK) + pos(ynbar.x-vw.ans.w +ynlen, ynbar.y) + strpadd(aus,vw.ans.w-13,'center'))
    ynbar.refresh()
    choice = ynbar.run ()
    cl ()
    if choice == LEFT:
      return True

  def deletekey(obj, key):
    " Delete user attribute "
    vw.update ('dElEtE \'' + attr + '\' fROM USER \'' + user + '\'?', align='center')
    if confirm(lr):
      remove(obj, key)
    ub.active().pos (ipos[ub.depth], spos[ub.depth])
    key = ub.active().selection
    ub.activate (ub.depth, [user, key])
    cl ()

  def addnewkey(obj):
    " Create new user attribute "
    vw.update()
    pl ('ENtER USER AttRibUtE NAME')
    key = editdata(vw)
    if not key: return cl()
    vw.update()
    pl ('ENtER AttRibUtE VAlUE')
    value = editdata(vw)
    if not value: return cl()
    pl ('SElECt VAlUE tYPE')
    lb_kvt.update(['StRiNG','iNt','flOAt'])
    lb_kvt.ans.border ()
    kvtype = lb_kvt.run()
    lb_kvt.ans.noborder ()
    lb_kvt.ans.clear (clean)
    if not lb_kvt.selection or lb_kvt.exit:
      return cl()
    vw.update('kEY: ' + key + ', VAlUE: ' + value + ' (' + kvtype + ')', align='center')
    try:
      if kvtype.lower() == 'string':  value = value
      elif kvtype.lower() == 'int':   value = int(value)
      elif kvtype.lower() == 'float': value = float(value)
    except:
      pl('iNVAlid VAlUE/tYPE PAiRiNG')
      inkey (timeout=2)
    if confirm(lr):
      addnew(obj, key, value)
    # update user record (depth 1)
    lightbar.update (ub.retrieve([user, attr]))

  def modify(action, user, key):
    " Handle modifer on user->key"
    obj = getuser(user).__dict__
    if action == 'edit':
      oldvalue, newvalue = vw.data(), editdata(vw)
      if newvalue != oldvalue:
        vw.update("'" + newvalue+ "'")
        if confirm(lr):
          change(obj, key, newvalue)
    elif action == 'clear':
      clear(obj, key)
    elif action == 'delete':
      remove(obj, key)
    elif action == 'copy':
      clipboard = str(obj[key])
    elif action == 'paste' and clipboard:
      change(obj, key, clipboard)

  echo (cls())

  u = getuser(handle())
  if not 'sysop' in u.groups:
    echo (pos(20, 10) + 'You must be in the sysop group')
    inkey ()
    return

  # ub is userbrowser object, inherited from lightstepclass
  ub = userbrowserclass(ansiwin(h=10, w=40, y=6, x=20))
  # value window
  vw = paraclass(ansiwin(h=4, w=ub.ans.w, y=ub.ans.y+ub.ans.h, x=ub.ans.x), xpad=1)
  # left-right bar
  lr = leftrightclass([vw.ans.x+vw.ans.w-ynlen, vw.ans.y+vw.ans.h +1])
  # keyvaluetype selection lightbar
  lbw,lbh = 9, 5
  lb_kvt = lightclass(ansiwin(h=lbh, w=lbw, y=vw.ans.y, x=vw.ans.x-lbw))

  # create root tree (list of users)
  lightbar = ub.right([None,None])
  print lightbar.interactive

  if user and userexist(user):
    for row, u in enumerate(lightbar.list):
      if user == u: lightbar.pos(row)
    lightbar = ub.right([user, lightbar.selection])
  elif user: user = None

  # user attribute name
  attr = None
  # value of user attribute
  value = None
  # store cursor position
  ipos, spos = [ 0, 0, 0 ], [ 0, 0, 0 ]

  def show_value(value=None):
    if not attr:
      value = None
    else:
      value = getuservalue(user, attr)
    echo (color())
    vw.ans.lowlight (partial=True)
    if isinstance(value, str):
      vw.update (value)
    else:
      vw.update (str(value))
    # type
    if attr:
      tstr = '-' + repr(type(value)) + '-'
      tstr = tstr[0:2] + ' ' + tstr[2:-2] + color() + ' ' + tstr[-2:]
      vw.ans.title (tstr, 'bottom')
      vw.ans.title ('-< ' + user + color(*BRIGHTRED) + "['" + color() + \
        str(attr) + color(*BRIGHTRED) + "']" + color() + ' >-', 'top')

  def deleteuser(handle):
    vw.update('dElETE \'' + handle + '\' fROM USER db?' ,align='center')
    if confirm(lr):
      deluser(getuser(handle))
      ub.active().pos (ipos[ub.depth], spos[ub.depth])
      user = ub.active().selection
      ub.activate (ub.depth, [user, None])

  def addnewuser():
    u = User ()
    vw.update ()
    pl('WhAt thiS PUSSiES NAME?', color())
    u.handle = editdata(vw)
    if not u.handle: return
    if userexist(u.handle):
      pl('USER AlREAdY EXiStS!', bcolor(RED)+color(BLACK))
      inkey (1)
      cl()
      return
    pl('WhAtS thE SECRET?', color())
    vw.update ()
    u.password = editdata(vw)
    if not u.password: return
    vw.update ('HANdlE: ' + u.handle + ', ' + 'PASSWORd: ' + u.password)
    if confirm(lr):
      adduser (u)
      ub.activate (ub.depth, [user, attr])
      lightbar.pos (ipos[ub.depth], spos[ub.depth])

  while True:
    if ub.depth in [0,1]:
      pl('(N)EW (D)ElEtE', color())
    if ub.depth == 0:
      user = lightbar.selection
      show_value ()
    if ub.depth == 1:
      attr = lightbar.selection
      show_value ()
    if ub.depth == 2:
      action = lightbar.selection
      cl()

    ipos[ub.depth], spos[ub.depth] = lightbar.item, lightbar.shift

    lightbar.run ()

    if lightbar.lastkey == '':
      return
    elif lightbar.lastkey == 'N':
      if ub.depth == 0:
        addnewuser()
      elif ub.depth == 1 and user:
        addnewkey (getuser(user).__dict__)
    elif lightbar.lastkey == 'D':
      if ub.depth == 0:
        deleteuser(user)
      elif ub.depth == 1 and user:
        deletekey (getuser(user).__dict__, lightbar.selection)
    elif lightbar.lastkey in [KEY.RIGHT, KEY.ENTER, 'l']:
      if ub.depth == 0:
        user = lightbar.selection
        lightbar = ub.right ([user, None])
        lightbar.pos (ipos[ub.depth], spos[ub.depth])
      elif ub.depth == 1:
        lightbar = ub.right ([user, attr])
        lightbar.pos (ipos[ub.depth], spos[ub.depth])
      elif ub.depth == 2:
        modify (lightbar.selection, user, attr)
        lightbar = ub.left ([user, attr])
        lightbar.pos (ipos[ub.depth], spos[ub.depth])
    elif lightbar.lastkey in [KEY.LEFT, 'h'] and ub.depth > 0:
      lightbar = ub.left ([user, attr])
      lightbar.pos (ipos[ub.depth], spos[ub.depth])

  echo (cursor_show())
  return
