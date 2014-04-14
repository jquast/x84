""" Userlister v1.0 by Hellbeard for x84 """

from x84.bbs import getsession, getterminal, echo, getch
from x84.bbs import list_users, get_user, timeago
from x84.bbs import userbase
import time

# ------------------------------------------------------------------

def showansi(fname):
    """ Return banner """
    from x84.bbs import getterminal, Ansi, from_cp437, showcp437
    import os
    term = getterminal()
    for line in showcp437(os.path.dirname(__file__)+ '/art/'+fname):
        echo(line)

# ------------------------------------------------------------------

def waitprompt():
        ansiprompt = {}
        numberofprompts = 0
        numberofrows = 0
        term = getterminal()

        echo ('\n\r'+term.magenta+'('+term.green+'..'+term.white+' press any key to continue '+term.green+'..'+term.magenta+')')
        getch()
        echo(term.normal_cursor)
        return

# ------------------------------------------------------------------

def main():
   session, term = getsession(), getterminal()
   session.activity = 'userlist'
   echo(term.clear)
   showansi('userlist.ans')
   echo('\r\n')

   counter = 0
   sortera = []
   user_handles = list_users()

   for handle in user_handles:
      user_record = get_user(handle)
      sortera.append(str(user_record.handle))
   sortera = sorted(sortera, key=lambda s: s.lower())

   for i in range (0,len(sortera)):
      user_record = get_user(sortera[i])
      echo(term.white+term.move_x(4)+user_record.handle+term.move_x(32)+term.green(user_record.location)+term.move_x(59)+term.bright_white+timeago(time.time() - user_record.lastcall)+'\r\n')
      counter = counter + 1
      if counter > term.height - 12:
          counter = 0
          waitprompt()
          echo (term.move_x(0)+term.clear_eol+term.move_up)

   waitprompt()
