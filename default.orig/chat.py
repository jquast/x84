"""
 Split-screen chat module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: chat.py,v 1.4 2008/10/02 04:05:52 dingo Exp $

 This modulde demonstrates pager windows in edit mode, and
 client-client communication.

 Important here, is the global variable players[], which is shared
 across all instances of this script. This list contains people who
 are available for chat. the available() function iterates this list
 and removes yourself from this list. join () and leave () functions
 set user's availability.

 When no one is available for chat, status is 'Waiting for other
 users'.  When others are available, they are placed in a lightclass
 object, and status becomes 'Select another user'. At this point,
 you may dial another user, or answer another user's call.

 We read from two events, the common 'input' event for user keypress,
 and a general 'page' event. If users are available for chat and the
 input event is trapped, input data is sent to an user list lightbar
 object.  If a user is selected (ENTER), she is paged by calling the
 dial() function. If a 'page' event is trapped, it is replied to via
 the answer() function.

 When dialing another user, a 'page' event is sent to that user's
 sessionid, along with a unique channel to handle future
 conversations. The caller's status becomes 'Waiting for reply', and
 we wait up to timeout for an acknowledgement of either 'accept' or
 'deny' on a negotiated communication channel. If accepted, the
 first while loop is broken, and the chat session begins through
 that channel.

 When answering a page request, the data sent along with the 'page'
 event signifies the caller's channel and session id. Then, a wait
 state up to timeout is entered for user to acknowledge or decline
 an invintation, sending 'accept' or 'deny' respectively. If user
 accepts, the chat session begins through the caller's communication
 channel. A check is done for a hangup before the chat session
 begins, in case the caller canceled the page request.
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast',
                 'Copyright (c)2006 Johannes Lundberg']
__license__ = 'ISC'

deps = ['bbs']

players     = []
timeout     = 15
# how often to poll for more available users
poll_delay        = 1

wfr_text    = ' .: Waiting for reply :. '
slice       = timeout/float(len(wfr_text))

def available ():
  " list users available for chat, except thyself "
  av = []
  for s in sessionlist():
      if s.__dict__.has_key('activity') \
      and s.activity == 'Waiting to chat' \
      and s.sid != session().sid:
        # add tuple of nick, sessionid
        av.append ((s.handle, s.sid))
  return av

def handleof (chatter):
  return chatter[0]
def sidof (chatter):
  return chatter[1]
def handles (chatters):
  h = []
  for chatter in chatters:
    h.append (chatter[0])
  return h

def join():
  " make self available for chat "
  echo (cls() + cursor_show())
  showfile ('ans/talk.ans')

def percentage_text (text, percentage):
  brk = int(float(len(text))*percentage)
  return color() + bcolor(RED) + color(BLACK) \
    + text[:brk] + color() \
    + text[brk:]

def main ():

  def dial (chatter):
    """ Request remote session to chat, waiting only as long as
        global value timeout. If chat request is acknowledged,
        return unique communication channel. Otherwise return 0 """
    (remote_handle, remotesid) = chatter
    channel = timenow ()
    sendevent (remotesid, 'page', (handle(), session.sid, channel) )
    # wait for remote user to accept
    for n in range(0, len(wfr_text)):
      status.update (percentage_text(wfr_text, n /(timeout /slice)))
      event, data = readevent ([channel,'input'], slice)
      if event == 'input' and data == '\030':
        sendevent (remotesid, channel, 'hangup')
        break
      if event == channel and data == 'accept':
        return channel
      elif event == channel and data == 'decline':
        warning ('Chat with ' + remote_handle + ' was declined', [60,6])
        break

    # timed out waiting for answer
    status.update ('Select another user', align='center')
    return 0

  def answer (data):
    """ Prompt user to answer a chat request, waiting only as long as
        global value timeout. If request is acknowledged,
        return communication channel. Otherwise return 0 """
    remotehandle, remotesid, channel = data

    p = 'z'
    echo (bel + cursor_show())
    while (not p in ['y','n','none']):
      echo (pos(45,6) + color() + 'Chat with %s?' % remotehandle)
      p = readkey (timeout)
    if p == 'y':
      event, data = readevent ([channel], .05)
      if data == 'hangup':
        warning (handle + ' hung up!', [60,6])
        return 0
      sendevent (remotesid, channel, 'accept')
      return channel
    elif p == 'n':
      sendevent (remotesid, channel, 'decline')
    return 0

  # top chat window
  top = paraclass (ansiwin(8, 78, 1, 2), split=5, xpad=1)
  # bottom chat window
  bot = paraclass (ansiwin(9, 78, 15, 2), split=5, xpad=1)
  # status bar (center-bottom of bottom chat window)
  status = paraclass (ansiwin(1, 27, bot.ans.y +bot.ans.h, 27), split=0, xpad=1, ypad=0)
  # user selection window (center of bottom chat window)
  dialpad = lightclass (ansiwin(bot.height -2, cfg.max_user +2, bot.ans.y +2, 40-((cfg.max_user+2)/2)))
  dialpad.alignment = 'center'
  dialpad.byindex, dialpad.interactive = True, True

  statechange = True

  session.activity = 'Waiting to chat'
  join ()
  top.ans.title (' Ctrl-X to Exit')
  chatters = available ()
  names = handles(chatters)

  while 1:
    if not statechange and chatters != available():
      statechange = True
      chatters = available ()

    if statechange and len(chatters):
        # users are available for chat
        status.update ('. Select another user', align='center')
        dialpad.ans.lowlight (partial=True)
        dialpad.update (handles(chatters))
    elif statechange:
        # waiting for other users to become available
        dialpad.ans.noborder()
        dialpad.ans.clear()
        status.update ('Waiting for other users', align='center')
    statechange = False

    # read user input, read for page requests
    event, data = readevent (['input','page'], poll_delay)
    print user.handle, ':', available()

    # evaluate input
    if event == 'input':
      if data == '\030':
        # exit (^X)
        return
      elif len(names):
        # users are available for chat, use keystroke as input to dialpad
        index = dialpad.run (data)
        if index is None:
          continue
        # user selected name, call user
        (remote_handle, remotesid) = chatters[index]
        channel = dial (chatters[index])
        if channel > 0:
          print handle(), 'called', chatters[index], 'got', remote_handle
          break

    # evaluate page request
    elif event == 'page':
      print data
      (remote_handle, remotesid, channel) = data
      answer (data)
      if channel > 0:
        print handle(), 'answered for', remote_handle
        break

    # evaluate state change
    newnames = handles(chatters)
    if names != newnames:
      names = newnames
      statechange = True

  def readonly (msg):
    " place window in read-only mode. "
    bot.interactive, bot.edit = False, False
    bot.add ('\n\n* ' + msg)
    return bot.run ()

  status.update ('-< '+ remote_handle +' >-', align='center')
  echo (cursor_show() + color())

  bot.add ('* ' + remote_handle + ' has arrived.')
  top.edit, top.interactive, bot.edit, bot.interactive = \
    True, True, True, True

  session.activity = 'Chatting with ' + remote_handle
  while 1:
    event, data = readevent (['input', channel])
    if event == 'input':
      if data == '\030':
        sendevent (remotesid, channel, ['exit'])
        return readonly (remote_handle + ' has been booted.\n\n pager still active -- Ctrl+X to exit')
      top.run (key=data)
      sendevent (remotesid, channel, data)
    elif event == channel:
      if isinstance(data, str):
        bot.run (key=data)
      elif isinstance(data, list):
        if data[0] == 'exit':
          return readonly (remote_handle + ' has left.\n\n pager still active -- Ctrl+X to exit')
        else:
          bot.ins_ch ('Uknown command: ' + repr(data) + '\n')
      else:
        bot.ins_ch ('Uknown msg: ' + repr(data) + '\n')
