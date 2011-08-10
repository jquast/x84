"""
 IRC module for 'The Progressive' BBS
 Copyright (c) 2007 Jeffrey Quast
 $Id: irc.py,v 1.7 2008/10/02 04:05:52 dingo Exp $

"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__contributors__ = []
__copyright__ = ['Copyright (c) 2007 Jeffrey Quast']
__license__ = 'ISC'

import time
deps = ['bbs']

# buffer length
history = 512

def init():
  global udb, online
  # irc database
  udb = db.openudb ('irc')

  # list of users on irc
  online = []

def main ():

  def draw_screen():
    " draw screen "
    echo (cls() + color())
    showfile ('ans/irc.ans')
    echo (cursor_show())

  def draw_wo():
    " draw 'whos online' window "
    whoson_txt = 'whos on: %s' % implode(online)
    whoson.update (whoson_txt)

  def draw_ib():
    " draw input bar "
    inputbar.ans.lowlight (partial=True)
    inputbar.ans.title (color() + '-< ^X:Exit >-')
    inputbar.ans.title (color() + '-< #1984 >-', align='bottom')

  def draw_buf():
    " draw buffer "
    rebuild_buffer ()
    buffer.ans.title ('-'+'< pgup/down:history >'+color()+'-')

  def rec2str(record):
    " convert raw irc log line to printable string "
    datetime, event, name, text = record[0], record[1], record[2], record[3]
    timestamp = time.strftime('[%a %H:%M]',time.localtime(datetime))
    if event == 'chat' and name == handle():
      return timestamp +' <' +name +'> ' + color() +text
    elif event == 'chat':
      return timestamp +' <' +name +'> ' +color() +text
    elif event == 'action':
      return timestamp +color() +' * ' +name +' ' +color() +text
    elif event == 'join':
      return timestamp +color(*WHITE) +' :' +color(GREY,NORMAL) +':' \
        + color(*LIGHTBLACK) +': ' +color() +name +color() +' [' +text +']' \
        + color() +' has joined #1984'
    elif event == 'part':
      return timestamp +color(*WHITE) +' :' +color(GREY,NORMAL) +':' \
        + color(*LIGHTBLACK) +': ' +color() +name +color() +' [' +text +']' \
        + color() +' has left #1984'

  def rebuild_buffer ():
    """ re-create window data from raw irc db """
    n, data = 0, []
    for n, rec in enumerate(udb['lines'][-history:]):
      data.append (rec2str(rec))
    buffer.update (data, '')
    return data

  def rebuild_db():
    " re-create raw irc buffer, called by /rebuild"
    db.lock ()
    udb['lines'] = db.PersistentList ()
    udb['lines'].insert(0, (timenow(), 'chat', 'biG BROthER', 'bEhAVE YOURSElVES'))
    db.commit ()
    db.unlock ()

  def sayline(event, text=''):
    """ say something into the buffer by .add()ing it to our own, then, send
        stored window content for quick load for anybody who joins irc (or
        presses ^L) """
    if not text and event =='chat': return

    datetime, name = timenow(), handle()
    record = [datetime, event, name, text]
    addstr = rec2str(record)

    # store raw irc data log
    db.lock ()
    udb['lines'].append (record)
    db.commit ()
    db.unlock ()

    # process window data
    buffer.add (addstr)

    # send to every one else's window
    broadcastevent ('irc_event', ['update', record])

    # store window data as quick-resume buffer

  def ring_bell(rings=3):
    " ring the bell by printing \a's "
    for n in range(0, rings):
      echo (bel)
      inkey (.19)

  def part ():
    " remove user from online list, send part event "
    online.remove (handle())
    sayline ('part', user.location)
    broadcastevent ('irc_event', 'part')
    inputbar.fixate ()

  def join ():
    " add user to online list and redraw screen in good order, and send join event "
    draw_screen ()
    online.append (handle())
    broadcastevent ('irc_event', 'join')
    draw_wo ()
    draw_buf ()
    sayline ('join', user.location)
    draw_ib ()
    inputbar.fixate ()

  # read-only pager for 'whos online' list
  whoson = paraclass(ansiwin(4,67,2,8), xpad=2)
  # read-only pager for buffer history
  buffer = paraclass(ansiwin(17,71,5,6), xpad=3, ypad=1)

  # editable pager for input
  inputbar = paraclass(ansiwin(3, 67, 22, 8), ypad=1, xpad=1)
  inputbar.edit, inputbar.interactive = True, True

  if not udb.has_key('lines'):
    print 'irc: building first db'
    rebuild_db()
    rebuild_buffer()

  join ()

  flushevent ('irc_event')
  session.activity = 'irc'
  while 1:
    event, data = readevent(['input', 'irc_event'])
    if event == 'irc_event':
      if isinstance(data, list):
        if data[0] == 'update':
          buffer.add (rec2str(data[1]))
        else:
          buffer.add ('unknown update: ' +str(data[1]))
      elif data == 'bell':
        ring_bell ()
      elif data == 'window':
        redraw ()
      elif data in ['join', 'part']:
        draw_wo ()
        inputbar.fixate ()
      else:
        buffer.add ('unknown irc_event: ' +str(data))

    elif event == 'input':
      if data == KEY.ENTER:
        # process input on return key
        txt = trim(inputbar.data())
        inputbar.update ('', align='top')
        inputbar.ans.clear ()
        if not txt: continue

        if str(txt[0:3]).lower() == '/me':
          sayline ('action', txt[4:])
        elif str(txt[0:5]).lower() in ['/part','/quit']:
          part ()
          break
        elif str(txt[0:5]).lower() == '/help':
          buffer.add (' :: Commands:')
          buffer.add (' :: me, quit, whois')
        elif str(txt[0:6]).lower() == '/whois' and ' ' in str(txt):
          nick = str(txt).split(' ')[1]
          if not userexist(nick):
            buffer.add (' :: ' + nick + ' does not exist')
            continue
          u = getuser(nick)
          buffer.add (' :: ' + u.handle + '(' + u.location + ')')
          if u.groups:
            buffer.add (' :: groups: ' + repr(u.groups))
          for s in sessionlist():
            if u.handle == s.handle:
              buffer.add (' :: session[' + str(s.sid) + '] idle ' + asctime(s.idle()) + ', ' + str(s.activity))
              for i, t in enumerate(s.terminals):
                buffer.add (' >> terminal[' + str(i) + '] attached ' + asctime(timenow() -t.attachtime) + ' ago')
        elif str(txt[0:8]).lower() == '/rebuild':
          rebuild_db ()
          rebuild_buffer ()
          draw_buf()
        elif not txt[0] == '/':
          sayline ('chat', txt)
        else:
          buffer.add (' :: Unknown command: ' +txt)
        inputbar.fixate ()
      elif data == '\030':
        part ()
        break
      elif data == '\022':
        buffer.update ('')
        buffer.refresh ()
        rebuild_buffer ()
        draw_buf ()
        inputbar.fixate ()
      elif data == '\014':
        draw_screen ()
        draw_wo ()
        draw_buf ()
        draw_ib ()
      elif data == bel:
        ring_bell ()
        broadcastevent ('irc_event', 'bell')
      elif data == KEY.PGDOWN:
        buffer.pgdown ()
      elif data == KEY.PGUP:
        buffer.pgup ()
      elif data == KEY.HOME:
        buffer.home ()
      elif data == KEY.END:
        buffer.end ()
      else:
        # pass input into input bar
        inputbar.run (key=data)
  return
