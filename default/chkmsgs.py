deps = ['bbs']

def main():
  getsession().activity = 'Checking for new messages'
  user = userbase.getuser(getsession().handle)
  term = getsession().getterminal()

  print repr(term.clear), repr(term.color)
  echo (term.clear + term.color)
  showfile ('art/msgs.asc')

  # check for new private messages
  echo ('\r\n\r\n  Checking for private messages... '); oflush()

  # privmsgs returns message record numbers only
  privmsgs = msgbase.listprivatemsgs(recipient=user.handle)
  newmsgs = [msg for msg in privmsgs if not getmsg(msg).read]

  echo ('%s messages, %s new\r\n' % (len(privmsgs), len(newmsgs)))
  if len(newmsgs):
    echo ((bel) + color(*LIGHTGREEN))
    echo ('\r\n  --> Read new private messages? [yna]   <--' + '\b'*5)
    echo (color())
    while True:
      k = getch()
      if k.lower() == 'y':
        savescreen = getsession().buffer['resume'].getvalue()
        gosub('msgreader', [msg for msg in newmsgs])
        echo (savescreen) # restore screen
        break
      elif k.lower() == 'a':
        savescreen = getsession().buffer['resume'].getvalue()
        gosub('msgreader', [msg for msg in privmsgs])
        echo (savescreen) # restore screen
        break
      elif k.lower() == 'n':
        break

  # check for new public messages
  echo ('\r\n\r\n  Checking for public messages...'); oflush()

  pubmsgs = msgbase.listpublicmsgs()
  newmsgs = [msg for msg in pubmsgs if not getsession().handle in getmsg(msg).read]

  echo ('%s messages, %s new\r\n' % (len(pubmsgs), len(newmsgs)))
  if len(newmsgs):
    echo ((bel) + color(*LIGHTGREEN))
    echo ('\r\nRead new public messages? [yna] ')
    echo (color())
    while True:
      k = getch()
      if k.lower() == 'y':
        savescreen = getsession().buffer['resume'].getvalue()
        gosub('msgreader', [msg for msg in newmsgs])
        echo (savescreen) # restore screen
        break
      elif k.lower() == 'a':
        savescreen = self.buffer['resume'].getvalue()
        gosub('msgreader', [msg for msg in pubmsgs])
        echo (savescreen) # restore screen
        break
      elif k.lower() == 'n':
        break
