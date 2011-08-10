from bbs import *

def main():

  session.activity = "userbase profiling"
  echo (cls() + cursor_show())

  class prof:
    def __init__ (self):
      self.startTime = self.lastTime = timenow()

    def tick (self, msg):
      echo (msg + ' complete in ' + asctime(timenow() -self.lastTime, precision=4) + '.\r\n')
      self.lastTime = timenow()

    def end (self):
      echo ('Total time:' + asctime(timenow() - self.startTime, precision=4) + '.\r\n')

  p = prof()

  def getInt(maxChars):
    while True:
      value = readline (maxChars)
      if not value: return
      try:
        return int(value)
      except ValueError:
        echo ('\r\nwhat? ')
        value = ''

  echo ('\r\ngenerate how many users? ')
  nusers = getInt(4)
  if not nusers: return

  echo ('\r\ndisplay how many most recent records? ')
  show = getInt(4)
  if not show: return

  intTime = int(timenow())
  adds = []
  for n in range(0, nusers):
    u = User()
    u.handle = 'test' + str(n)
    u.lastcall = intTime -2600 -(n+77)
    adds.append (u)
  addusers (adds)
  p.tick ('\r\nuser creation')

  users = listusers()
  p.tick ('record retrieval')

  callsort = []
  for u in users:
    callsort.append ((u.lastcall, u))
  p.tick ('transform')

  deletes = []
  for u in users:
    if u.handle.startswith('test'):
      deletes.append(u)
  delusers (deletes)
  p.tick ('delete')

  callsort.sort()
  callsort.reverse()
  p.tick ('sort/reverse')

  callsort = callsort[:show]
  p.tick ('truncate')

  for lc, u in callsort:
    echo (u.handle + ' last called ' + asctime(p.startTime -lc) + ' ago.\r\n')
  p.tick ('displayed ' + str(show) + '/' + str(len(users)) + ' records')
  p.end ()

  readkey ()
