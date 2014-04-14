""" Automsg script 1.0 by Hellbeard for x84 """
from x84.bbs import getsession, getterminal, echo, getch, LineEditor, showcp437
import os
import codecs

# -----------------------------------------------------------------------------
def banner():
  term = getterminal()
  session = getsession()
  echo(term.clear)
  term = getterminal()
  banner = ''
  for line in showcp437(os.path.dirname(__file__)+ '/art/'+'automsg.ans'):
    banner = banner + line
  echo (banner)

  msg = ''
  fo = open(os.path.dirname(__file__)+ '/art/automsg.txt', 'r')

  echo(term.move(9,30)+term.blue_on_green+str(fo.readline())+term.normal)

  for i in range (1,4):
    echo(term.move(10+i,9)+term.yellow)
    echo(u''+str(fo.readline()))
  fo.close()
  echo(term.move(9,9)+term.white+'Public message from:')
  echo(term.move(18,0)+term.magenta+'do you want to write a new public message? '+term.green+'('+term.cyan+'yes/no'+term.green+')')

# -----------------------------------------------------------------------------

def main():
  term = getterminal()
  session = getsession()
  session.activity = 'automsg'
  banner()

  folder = os.path.join(os.path.dirname(__file__), os.path.pardir, 'data')
  if not os.path.exists(folder):
    os.makedirs(folder)
  automsg_txt = os.path.join(folder, 'automsg.txt')


  keypressed = ''
  while 1:
    keypressed = getch()
    if keypressed == 'n' or keypressed == 'N' or keypressed == 'Q' or keypressed == 'q' or keypressed == term.KEY_ENTER:
      return

    if keypressed == 'y' or keypressed == 'Y':
      echo(term.move(9,30)+term.blue_on_green+session.user.handle+term.normal+'       ')
      echo(term.move(18,0)+term.clear_eol)
      msg = {}
      for i in range (1,4):
        echo(term.move(10+i,9)+'                                                         ')
      for i in range (1,4):
        echo(term.move(10+i,9))
        le = LineEditor(56)
        le.colors['highlight'] = term.yellow
        msg[i] = le.read()

      echo(term.move(18,0)+term.magenta+'submit your text as a public message? '+term.green+'('+term.cyan+'yes/no'+term.green+')')
      keypressed = ''
      while 1:
        keypressed = getch()
        if keypressed == 'n' or keypressed == 'N':
          return
        if keypressed == 'y' or keypressed == 'Y':
          echo(term.move(18,0)+term.clear_eol)
          fo = codecs.open(automsg_txt, 'w', 'utf-8')
          fo.write(session.user.handle+'\n')
          for i in range (1,4):
            fo.write(msg[i]+'\n')
          fo.close()
          return
