# sword of the samurai bbs door clone

import db
deps = ['bbs',
  'games/sots/data_province',
  'games/sots/data_text',
  'games/sots/gamedb',
  'games/sots/events']

import random

debugKill=0

def main():
  session.activity = 'playing Sword of the Samurai'

  if not handle() in events.keys():
    print '-'*80
    print 'create new event in db'
    events[handle()] = Event(handle())

  eventHandler = events[handle()]
  eventHandler.joinGame (handle())

  echo (cls() + color())

  while True:
    nextEvent = eventHandler.pop ()

    callEvent = nextEvent[0]
    args = nextEvent[1:][0]
    print 'next event:', callEvent
    print 'arguments:', args

    retvalue = callEvent(eventHandler, *args)

    if callEvent == Event.newSamurai and not retvalue:
      # failed to create a new samurai
      return retvalue
    elif callEvent == Event.quit:
      # user quit
      return retvalue

  return
