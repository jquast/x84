deps = ['bbs']

def main():
  session.activity = 'Testing paraclass'
  echo ( color() + cls() )
  pager = ParaClass \
    (h=getsession().height, w=getsession().width, y=1, x=1, xpad=0, ypad=0)
  pager.debug = True
  pager.border ()
  pager.title ( 'up/down/(q)uit', 'bottom')
  pager.update (fopen('test.ans').read())
  pager.run ()
