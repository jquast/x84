"""
 Main menu script for X/84, http://1984.ws
 $Id: main.py,v 1.12 2010/01/02 07:35:27 dingo Exp $

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2009 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']

def main():
  def refresh():
    " refresh main menu screen "
    getsession().activity = 'Main Menu'
    echo (color() + cursor_show() + cls() +'\n')
    showfile ('art/main_alt.asc')
    echo ('\r\n\r\n > ')
  def sorry():
    echo ('\r\n\r\n  ' + color(*LIGHTRED) + 'Sorry')
    readkey (1)
    refresh ()
  def pak():
    echo ('\r\n\r\n  ' + color() + 'Press any key...')
    readkey ()
    refresh ()

  refresh ()

  while True:
    choice = inkey()

    if choice == '*':
      goto ('main')
    elif choice == '/':
      m = Msg(handle())
      m.recipient = handle()
      m.subject = 'test!'
      m.body = 'test'
      m.tags = ['test']
      m.send ()
    elif choice.lower () == 'c':
      gosub ('wfc')
      refresh ()
    elif choice.lower() == 'f':
      sorry ()
    elif choice.lower() == 'n':
      gosub ('chkmsgs')
      pak ()
    elif choice.lower() == 'w':
      gosub ('msgwriter')
      refresh ()
    elif choice.lower() == 'r':
      gosub ('msgreader', listprivatemsgs(handle()) + listpublicmsgs())
      refresh ()
    elif choice == 'b':
      gosub ('bbslist')
      refresh ()
    elif choice == 'k':
      gosub ('userlist')
      refresh ()
    elif choice == 'l':
      gosub ('lc')
      refresh ()
    elif choice == 'o':
      gosub ('ol')
      refresh ()
    elif choice == 'i':
      gosub ('irc')
      refresh ()
    elif choice == 'e':
      gosub ('viewlog')
      refresh()
    elif choice == 'E':
      gosub ('test.editor')
    elif choice == 'x':
      gosub ('wo')
      refresh ()
    elif choice == 'u':
      gosub ('ueditor', getsession().handle)
      refresh ()
    elif choice == 's':
      gosub ('si')
      refresh ()
    elif choice == 't':
      gosub ('games/tetris')
      refresh ()
    elif choice == 'm':
      gosub('games/mastermind')
      refresh()
    elif choice == 'z':
      gosub('news')
      refresh()
    elif choice.lower() == 'v':
      gosub ('imgviewer')
      refresh ()
    elif choice.lower() == 'g':
      gosub ('logoff')
      refresh ()
    else:
      echo (bel)
