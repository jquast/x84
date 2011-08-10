
deps = ['bbs']

def main():
  session = getsession()
  w, h = session.width, session.height
  ocean = [(['x']*w)]*h
  level = 0
  stage = 'transition_in'
  transition_steps = 0
  while True:
    transition_steps += 1
    print ocean
    echo (cls())
    for row in ocean:
      echo (''.join(row))
    if stage == 'transition_in':
      minfill = transition_steps/2
      for n in range(minfill):
        ocean[-(n+1)] = ['y']*w
    k = readkey(2)
    if k == 'q':
      disconnect()
