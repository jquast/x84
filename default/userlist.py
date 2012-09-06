deps = ['bbs']

def main():
  session = getsession()
  getsession().activity = 'user list'

  def getusers(hg='-', xpad=2):
    fx = (color(*DARKGREY), color(*LIGHTRED), color(*DARKGREY), color())
    header = \
      hg*(xpad-2) + \
      strpadd('%s[%shandle%s]%s' % fx, int(db.cfg.get('nua','max_user'))+1, ch=hg) + \
      strpadd('%s[%slocation%s]%s' % fx, int(db.cfg.get('nua','max_origin'))+1, ch=hg) + \
      strpadd('%s[%scalls%s]%s' % fx, 8, 'left', ch=hg) + \
      strpadd('%s[%sposts%s]%s' % fx, 8, 'left', ch=hg) + \
      strpadd('%s[%slast call%s]%s' % fx, 12, 'left', ch=hg)
    users = [ \
      strpadd(u.handle, int(db.cfg.get('nua','max_user'))+1) + \
      strpadd(u.location, int(db.cfg.get('nua','max_origin'))+1) + \
      strpadd(str(u.calls), 8, 'left') + \
      strpadd(str(u.numPosts()), 8, 'left') + \
      strpadd(asctime(time.time() - u.lastcall) + ' ago', 12, 'left') \
        for u in listusers()]
    return header, users

  def refresh (ul=None):
    echo (cls() + pos() +cursor_hide())
    if session.height < 15 or session.width < 70:
      echo (color(*LIGHTRED) + 'Screen size too small to display user list' \
            + color() + '\r\n\r\npress any key...')
      getch ()
      return False
    art = fopen('art/userlist.asc',  'r').readlines()
    # lowlight userlist
    ul = LightClass (h=session.height-7, w=69, y=7, x=(session.width/2)-(69/2), ypad=1, xpad=3)
    ul.partial = ul.interactive = True
    hg = ul.glyphs['top-horizontal']
    header, users = getusers(hg, ul.xpad)
    u = getuser(getsession().handle)
    ln = '%s-%s' % (color(*DARKGREY), color())
    footer = ln
    if 'sysop' in u.groups:
      footer += ' %sE%sdit USR %s %sD%sElEtE USR %s' \
        % (color(*WHITE), color(*LIGHTRED), ln, color(*WHITE), color(*LIGHTRED), ln)
    footer += ' %sW%sRitE MSG %s %sR%sEAd MSGS' \
        % (color(*WHITE), color(*LIGHTRED), ln, color(*WHITE), color(*LIGHTRED))
    footer += ' %s-%s' % (color(*DARKGREY), color())
    ul.lowlight ()
    ul.update (users, True)

    # display ascii art
    echo (''.join([pos(x=(session.width/2)-(maxwidth(art)/2), y=y) + row \
      for y, row in enumerate(art)]))

    # display header & footer
    echo (pos(ul.x+1, ul.y) + header)
    ul.title (footer, 'bottom')

    return ul

  ul = refresh()
  if not ul:
    return
  isSysop = 'sysop' in getuser(getsession().handle).groups
  while not ul.exit:
    event, data = readevent(['input','refresh'])
    selected = ul.selection.split(' ')[0]
    if event == 'refresh':
      ul = refresh (ul)
      if not ul:
        return
    elif event == 'input':
      if isSysop and data in 'EWR':
        savescreen = getsession().buffer['resume'].getvalue()
        if data == 'E':
          gosub('ueditor', selected)
        elif data == 'W':
          msg = Msg(author=handle(), recipient=selected)
          gosub('msgwriter', msg)
        elif data == 'R':
          gosub('msgreader', getuser(selected).posts())
        echo (savescreen)
      elif isSysop and data == 'D':
        l = len(YesNoClass.left_text + YesNoClass.right_text)
        lr = YesNoClass((session.width-l, session.height))
        lr.right ()
        echo (pos(session.width/2-(19/2), session.height))
        echo ('%s[  ERaSE user ?!  ]%s' % (color(RED)+color(INVERSE), color()))
        choice = lr.run (key=data)
        echo (cl())
        if choice == YES:
          getuser(selected).delete ()
          ul = refresh(ul)
          if not ul:
            return
      else:
        ul.run (data)
    echo (cursor_show())
