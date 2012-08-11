deps = ['bbs']

TXT_RE = 'Re: '

def main(msgs):
  if not len(msgs):
    print handle() + ' msgreader: called with msgs=None'
    return

  getsession().activity = 'Reading messages'

  TOP=6
  ch=getsession().height-9
  cw=getsession().width-26
  cx=getsession().width/2 -(cw/2)
  pager = ParaClass(h=ch, w=cw, y=TOP, x=cx, xpad=3, ypad=2)
  pager.interactive = True
  pager.partial = True
  pager.colors['active'] = color(*YELLOW)

  lx = cx+cw-7
  ly = getsession().height
  lr = PrevNextClass((lx,ly), NEXT)
  lr.highlight = color(BROWN) + color(INVERSE)
  lr.lowlight = color()  + color(GREY)
  lr.interactive = True

  n = 0
  bitclear = False

  def remove(index, hard=False):
    if index in msgs:
      msgs.remove (n, force=hard)
      if index == 0:
        if not len(msgs):
          return False # last message!
        n += 1 # forward from beginning
      elif n >= len(msgs)-1:
        n -= 1 # backup
      else:
        n += 1 # forward
      return True
    return False

  def noclear():
    echo (pos(1, getsession().height) + color() + cl())

  def status(text='(^Y) Commands'):
    x, y=cx+(cw/2)-(len(text)/2), ch+TOP+1
    echo (pos(x,y) + color() + cl() + text)
    lr.refresh ()

  def refresh():
    echo (cls())
    #showfile ('ans/editor.ans')
    echo (color())
    echo (pos(5,1) + cl() + 'From: ' + msg.author)
    echo (pos(5,2) + cl() + 'To: '+ str(msg.recipient))
    # XXX convert to localtime zone
    echo (pos(5,3) + cl() + 'Date: ' + time.ctime(msg.creationtime) + ' (' + asctime(timenow()-msg.creationtime) + ' ago)')
    echo (pos(5,4) + cl() + 'Tags: ' + implode(msg.tags,', ',' and '))
    pager.title(color(*DARKGREY) + '-< ' + color() + msg.subject + color(*DARKGREY) + ' >-')
    if msg.public and not handle() in msg.read:
      ur = color(*LIGHTGREEN) + '+'
    else: ur=''
    pp = color(*DARKGREY) + '[' + color() + color(*YELLOW)
    if msg.public: pp += 'public'
    else: pp += 'private'
    pp += color(*DARKGREY) + ']'
    pager.highlight ()
    pager.title(color(*DARKGREY) + '-< ' + ur + color() + '#' + color() + str(n+1) + ' of ' + str(len(msgs)) + color(*DARKGREY) + ' ' + pp + ' >-',align='bottom')

    echo (''.join([pos(3, TOP+y)+row \
          for y, row in enumerate(fopen('art/p-left.ans').readlines())]))
    echo (''.join([pos(cx+cw-3, ch-9+y)+row \
          for y, row in enumerate(fopen('art/p-right.ans').readlines())]))

    txt = ''
    if 'sysop' in getuser(handle()).groups:
      if msg.public:
        txt += '\nthiS MESSAGE hAS bEEN REAd bY ' + str(len(msg.read)) + ' USERS:\n  '
        txt += strand(msg.read) + '.'
      elif not msg.public:
        txt += 'thiS MESSAGE hAS '
        if not msg.read: txt += 'NOt '
        txt += 'bEEN REAd bY ' + str(msg.recipient)
        if not isinstance(msg.read, list) and msg.read != True:
          txt += ' (' + asctime(timenow()-msg.read) + ' AGO)'
      if msg.draft:
        txt += '\nthiS MESSAGE iS A dRAft!'
      if msg.deleted:
        txt += '\nthiS MESSAGE hAS bEEN dElEtEd bY  ' + str(msg.deleted) + '.'
    if txt:
      pager.update (msg.body + '\n\n---------\n' + txt)
    else:
      pager.update (msg.body)
    status ()

  while True:
    if msgexist(msgs[n]):
      msg = getmsg(msgs[n])
      if msg.public and not handle() in msg.read:
        msg.set('read', msg.read + [handle()])
      elif not msg.public and msg.recipient == handle():
        msg.set('read', timenow())
    else:
      msg = Msg('','','','thiS MESSAGE hAS SiNCE bEEN hARd dElEtEd!')
      msg.creationtime = 0
    refresh ()
    while True:
      # TODO: poll for new messages
      k = readkey()
      if bitclear:
        status ()
        bitclear = False
      if k == 'p' or (k in [KEY.LEFT,'h'] and lr.isleft()) \
      or k == KEY.ENTER and lr.isleft():
        # previous
        if not lr.isleft(): lr.left ()
        if n == 0:
          status ('NO PRiOR MESSAGES')
          bitclear = True
        else:
          n -= 1
          break
      elif k == 'n' or (k in [KEY.RIGHT,'l'] and lr.isright()) \
      or k == KEY.ENTER and lr.isright():
        # next
        if not lr.isright(): lr.right ()
        if n >= len(msgs)-1:
          status ('NO MORE MESSAGES')
          bitclear = True
        else:
          n += 1
          break
      if k in [KEY.LEFT, KEY.RIGHT, 'h', 'l']:
        lr.run (k)
      elif k == '\031':
        compose_options = ['reply']
        if handle() in [msg.recipient, msg.author] \
        or 'sysop' in getuser(handle()).groups:
          if msg.readBy(handle()):
            compose_options.append ('mark unread')
          else:
            compose_options.append ('mark read')
          if msg.public:
            compose_options.append ('mark private')
          else:
            compose_options.append ('mark public')
          compose_options.append ('soft delete')
          if 'sysop' in getuser(handle()).groups:
            compose_options.append ('hard delete')
        compose_options += ['tag','untag']
        lb = LightClass(10,17,10,27)
        lb.partial = True
        lb.alignment = 'center'
        lb.bcolor = color(BROWN) + color(INVERSE)
        lb.update (compose_options)
        lb.resize (len(compose_options)+2)
        echo (color())
        lb.noborder ()
        echo (color(BROWN))
        lb.border ()
        echo (color())
        option = lb.run ()
        lb.noborder ()
        lb.clear ()
        if lb.exit:
          status ('CANCEllEd!')
        elif option == 'mark unread':
          if msg.public:
            msg.set('read', [])
          else:
            msg.set('read', False)
          status ('MESSAGE hAS bECOME UNREAd!')
        elif option == 'mark read':
          if msg.public:
            msg.set('read', [handle()])
          else:
            msg.set('read', timenow())
          status ('MESSAGE hAS bECOME REAd!')
        elif option == 'mark public':
          msg.set('public', True)
          msg.set('read', [])
          status ('MESSAGE hAS bECOME PUbliC ANd UNREAd!')
        elif option == 'mark private':
          msg.set('public', False)
          msg.set('read', False)
          status ('MESSAGE hAS bECOME PRiVAtE ANd UNREAd!')
        elif option == 'soft delete':
          msg.delete (killer=handle())
          status ('MESSAGE hAS bEEN MARkEd dElEtEd!')
          remove (n)
        elif option == 'hard delete':
          msg.delete (force=True, killer=handle())
          status ('MESSAGE hAS bEEN dElEtEd!')
          remove (n, hard=True)
        elif option == 'reply':
          # construct response message
          replymsg = Msg(author=handle(), recipient=msg.author, subject=msg.subject)
          # set parent message
          replymsg.set ('parent', msg.number)
          if msg.subject[0:len(TXT_RE)] != TXT_RE:
            # pre-append re: text
            replymsg.set('subject', TXT_RE + msg.subject [0:59 -len(TXT_RE)])
          # XXX screw with the body (quoting, not fucking)
          gosub ('msgwriter', replymsg)
          refresh ()
        pager.refresh ()
        bitclear = True
      else:
        pager.run (k)
      if pager.exit:
        return
