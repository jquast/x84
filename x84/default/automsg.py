""" Automsg script 1.0 by Hellbeard for x84 """
from x84.bbs import getsession, getterminal, echo, LineEditor, showcp437
import os
import codecs


def get_datafile():
    from x84.bbs import ini
    folder = os.path.join(ini.CFG.get('system', 'datapath'), os.path.pardir, 'data')
    return os.path.join(folder, 'automsg.txt')


# -----------------------------------------------------------------------------
def banner():
  session, term = getsession(), getterminal()
  art_file = os.path.join(os.path.dirname(__file__), 'art', 'automsg.ans')
  echo(term.clear)
  for line in showcp437(art_file):
    echo (line)

  with open(get_datafile()) as fo:
    handle = fo.readline().strip()
    echo(term.move(9, 30) + term.blue_on_green(handle))
    for row in range(1, 4):
      echo(term.move(10 + row, 9) + term.yellow(fo.readline().strip()))

  echo(term.move(9, 9) + term.white(u'Public message from:'))
  echo(term.move(18, 0))
  echo(term.magenta(u'do you want to write a new public message? '))
  echo(term.green(u'(') + term.cyan(u'yes/no') + term.green(u')'))

# -----------------------------------------------------------------------------

def main():
  term = getterminal()
  session = getsession()
  session.activity = 'automsg'
  banner()



  while True:
    keypressed = term.inkey()
    if keypressed.lower() in (u'n', 'q') or keypressed.code == term.KEY_ENTER:
      break

    if keypressed.lower() == u'y':
      echo(term.move(9, 30))
      echo(term.blue_on_green(session.user.handle))
      echo((u' ' * 7))

      echo(term.move(18, 0) + term.clear_eol)
      for row in range (1, 4):
        echo(term.move(10 + row, 9))
        echo(u' ' * 57)

      msg = []
      for row in range (1, 4):
        echo(term.move(10 + row, 9))
        le = LineEditor(56)
        le.colors['highlight'] = term.yellow
        msg.append(le.read())

      echo (term.move(18, 0))
      echo (term.magenta(u'submit your text as a public message? '))
      echo (term.green(u'(') + term.cyan(u'yes/no') + term.green(u')'))

      while 1:
        keypressed = term.inkey()
        if keypressed.lower() == u'n':
          return
        if keypressed == 'y' or keypressed == 'Y':
          echo(term.move(18, 0) + term.clear_eol)
          with codecs.open(get_datafile(), 'w', 'utf-8') as fo:
            fo.write('\n'.join([session.user.handle] + msg))
            fo.close()
          return
