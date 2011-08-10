deps = ['bbs']

#XXX todo: build into class

def main(msg=None):
  echo (cls() + cursor_show() + color())
  session.activity = 'Composing a message'

  pager = paraclass(ansiwin(19,70,5,5), xpad=2, ypad=2)
  pager.interactive = True
  pager.edit = True
  pager.ans.lowlight (partial=True)
  lr = leftrightclass([60,24], RIGHT)

  if not msg:
    msg = Msg(handle(),'','','')

  echo (color())
  echo (pos(5,1) + cl() + 'fROM: ' + color(INVERSE) + msg.author)
  echo (color())

  max = 25
  while True:
    # populate To: field ...
    echo (cursor_show())
    echo (pos(20,4) + color() + cl() + 'ENtER RECiPiENt, REtURN CARRiAGE WhEN fiNishEd')
    echo (pos(20,24) + cl() + 'USE \'NONE\' tO POSt tO All, \'EXit\' tO QUit')
    ws = max -len(str(msg.recipient))
    echo (pos(5,2) + cl() + 'tO: ' \
          + color(INVERSE) + '*'*len(msg.recipient) \
          + ' '*(ws) + '\b'*(ws))
    echo (pos(9, 2))
    msg.recipient = readline (max, msg.recipient)
    echo (color())
    # complete match
    match = finduser(msg.recipient)
    if match:
      break
    if str(msg.recipient).lower() == 'exit':
      return
    if str(msg.recipient).lower() == 'all':
      msg.recipient = 'None'
      ws = max -len(str(msg.recipient))
      echo (pos(30,24) + cl() + 'All OR NONE:?!')
      inkey (.7)
      echo (pos(5,2) + cl() + 'tO: ' \
            + color(INVERSE) + str(msg.recipient) \
            + ' '*(ws) + '\b'*(ws) \
            + color())
      break
    if str(msg.recipient).lower() == 'none':
      msg.recipient = None
      break

    # create nickname picklist
    userlist = []
    def add(user):
      userlist.append (user.handle)
    if not msg.recipient:
      for u in listusers():
        add (u)
    # begins with,
    for u in listusers():
      if u.handle.lower().startswith(str(msg.recipient).lower()):
        add (u)
    # is partial
    if not userlist:
      for u in listusers():
        if str(msg.recipient).lower() in u.handle.lower():
          add (u)
    if not len(userlist):
      echo (pos(30,4) + color(RED) + color(INVERSE) \
            + cl() + 'NO MAtChES fOUND' + bel)
      inkey (1)
      echo (cl())
      continue
    # only one match, stay at prompt for confirmation
    if len(userlist) == 1:
      msg.recipient = userlist[0]
      echo (pos(8,4) + cl() + '1 MAtCh')
      continue
    lb = lightclass(ansiwin(10,20,10,30))
    lb.bcolor = color(BLUE) + color(INVERSE)
    lb.update (userlist)
    if len(userlist) < 8:
      lb.resize (len(userlist)+2)
    lb.ans.border (partial=True)
    msg.recipient = lb.run ()
    if lb.exit: msg.recipient = 'EXit'
    lb.ans.noborder ()
    lb.ans.clear ()
    echo (pos(5,2) + color() + cl())

  # Populate Subject: field
  echo (pos(20,4) + cl() + 'ENtER SUbJECt, REtURN CARRiAGE WhEN fiNiShEd')
  echo (pos(20,24) + cl() + 'REtURN CARRIAGE With EMPtY SUbJECt tO EXit')
  max = 60
  #ws = max -len(msg.subject)
  echo (pos(5,3) + cl() + 'SUbJECt: ' \
    + color(INVERSE) \
    + ' '*(max) \
    + pos(14+len(msg.subject),3))
  msg.subject = readline (max, msg.subject)
  echo (color())

  if not msg.subject:
    return

  # XXX convert to localtime zone
  echo (color() + pos(5,3) + cl() + 'DAtE: ' + color(INVERSE) + time.ctime(msg.creationtime))
  echo (color() + pos(5,4) + cl() + 'tAGS: ' + color(INVERSE) + implode(msg.tags,', ',' and '))

  echo (color())
  pager.ans.lowlight (partial=True)
  pager.ans.title (color() + color(*DARKGREY) + '-' + color(GREY) + '< ' \
    + color(*LIGHTBLUE) + msg.subject + color(GREY) + ' >' \
    + color(*DARKGREY) + '-')
  echo (pos(20,4) + color() + color(BLUE) + cl() + 'WhO CONtROlS thE PAST CONtROlS thE fUtURE;')
  echo (pos(20,24) + color(BLUE) + cl() + 'WhO CONtROlS thE PRESENt CONtROlS thE PASt.')
  pager.ans.title(color(*DARKGREY) + '-< (^Y) COMMANdS >-',align='bottom')
  echo (color())
  pager.update (msg.body)

  while True:
    k = inkey()
    if k == '\031': #^Y
      lb = lightclass(ansiwin(10,20,10,27))
      lb.alignment='center'
      compose_options = ['send','abort','suspend','quote','tag','untag','change subject','change addressee']
      lb.bcolor = color(BLUE) + color(INVERSE)
      lb.update (compose_options)
      lb.resize (len(compose_options)+2)
      echo (color(*WHITE))
      lb.ans.border (partial=True)
      option = lb.run ()
      lb.ans.noborder ()
      lb.ans.clear ()
      if option == 'send':
        msg.body = pager.data()
        pager.update (msg.body)
        # public or private
        echo (pos(30,24) + color(*LIGHTBLUE) + cl() + 'MAkE PUbliC?')
        lr.right ()
        lr.run ()
        if lr.isright() and not msg.recipient:
          echo (pos(20,24) + color(RED) + color(INVERSE) + cl() + 'PRiVAtE MESSAGES MUSt bE AddRESSEd!' + color())
          inkey (2)
        elif lr.isright():
          msg.draft = False
          msg.public = False
        elif lr.isleft():
          msg.draft = False
          msg.public = True
        # confirm
        echo (pos(30,24) + color(*LIGHTBLUE) + cl() + 'SENd MESSAGE?')
        lr.refresh ()
        lr.run ()
        if lr.isleft():
          msg.send ()
          return
      if option == 'abort':
        echo (pos(30,24) + color(*LIGHTBLUE) + cl() + 'REAllY QUit?')
        lr.refresh ()
        lr.run ()
        if lr.isleft():
          return
      elif option == 'suspend':
        # drafts are not recieved by recipient
        msg.draft = True
        sendmsg (msg)
      elif option in ['quote', 'tag', 'untag']:
        echo (pos(20,24) + color(RED) + color(INVERSE) + cl() + 'sorry, not yet ;/' + color())
        inkey (1)
      echo (pos(20,24) + color(BLUE) + cl() + 'WhO CONtROlS thE PRESENt CONtROlS thE PASt.')
      pager.refresh ()
    pager.run (k)
