#
# Main Menu for PRSV
#
# (c) 2007 Jeffrey Quast :: dingo@efnet

deps = ['bbs']

def main():
  pager = paraclass(ansiwin(h=14,w=70,y=12,x=5), split=8)
  pager.split = 8
  pager.silent = True

  def refresh():
    " refresh main menu screen "
    session.activity = 'Main Menu'
    echo ( color() + cls() +'\n\n\n')
    showfile('ans/motd')
    pager.update ('\n\nf)ilebrowser  n)ews        o)neliners   l)ast callers' \
                   + '\n\nw)hos on      c)hat        i)rc         g)oodbye' \
                   + '\n\nW)eather      m)astermind! s)end msg    r)ead msgs ' \
                   + '\n\n(when in doubt, ctrl+x)')

  refresh ()

  while True:
    choice = inkey()
    if choice == 'g':
      goto('logoff')
    elif choice == 'f':
      value = gosub('fb')
      print 'gosub fb returned value:', value
      refresh()
    elif choice == 'n':
      gosub('news')
      refresh()
    elif choice == 'N':
      gosub('newsreader')
      refresh()
    elif choice == 'b':
      gosub('test/ansiwin')
      refresh()
    elif choice == 'c':
      gosub('chat')
      refresh()
    elif choice == 'u':
      gosub('ue')
      refresh()
    elif choice == 'l':
      gosub('lc')
      refresh()
    elif choice == '1':
      gosub('lord/main')
      refresh()
    elif choice == 'w':
      gosub('wo')
      refresh()
    elif choice == 'e':
      gosub('test/editor')
      refresh()
    elif choice == 'p':
      gosub('test/paraclass')
      refresh()
    elif choice == '9':
      gosub('test/scroll')
      refresh()
    elif choice == 'i':
      gosub('irc')
      refresh()
    elif choice == ']':
      gosub('comment')
      refresh()
    #elif choice == '+' and 'sysop' in getuser(handle()).groups:
    #  gosub('test/writemessage')
    #  refresh()
    elif choice == 'o':
      gosub('ol')
      refresh()
    elif choice == 'S':
      gosub('games/sokoban')
      refresh()
    elif choice == 'W':
      gosub('weather')
      refresh()
#    elif choice == 'r':
#      gosub('sots/main')
#      refresh()
    elif choice == 'm':
      gosub('games/mastermind')
      refresh()
    elif choice == 's':
      gosub('msgwriter')
      refresh ()
    elif choice == 'r':
      print 'read private,'
      gosub('msgreader', listprivatemsgs(handle()))
      print 'read public,'
      gosub('msgreader', listpublicmsgs())
      if 'sysop' in user.groups:
        print 'read all,'
        gosub('msgreader', db.msgs.keys())
      refresh ()
    elif choice == '*':
      goto('main')
    elif choice == '~':
      goto('top',handle())
    #elif choice == '<':
    #  gosub('test/deleteall')
    #  echo (bel)
    #  refresh ()
    #elif choice == '!':
    #  gosub('test/markallunread')
    #  echo (bel)
    #  refresh ()
    #elif choice == 'a':
    #  gosub('ap')
    #  echo (bel)
    #  refresh ()
    elif choice == '7':
      gosub('test/userbase-profile')
      refresh ()
    choice = ''
