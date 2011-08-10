"""
bbs listing for X/84, http://1984.ws
$Id: bbslist.py,v 1.1 2010/01/02 07:35:27 dingo Exp $
"""
__author__ = 'Jeffrey Quast <dingo@1984.ws>'
__copyright__ = ['Copyright (c) 2010 Jeffrey Quast']
__license__ = 'ISC'
__url__ = 'http://1984.ws'

deps = ['bbs']

def main():
  udb = openudb('bbslist')
  session.activity = 'BBS Lister'
  dirty=True
  lightbar=False
  bbslist=[]

  bbsname=host=port=software=sysop=ratings=comments=None
  while True:
    if dirty or not lightbar:
      def calcRating(ratings):
        rating, d = '----', 0
        if len(ratings):
          d=sum([r for u, r in ratings])/len(ratings)
        return '*'*(d) + '-'*(4-d)
      echo (cls() + color())
      echo ('\r\n ansi needed :( \r\n')
      if not lightbar:
        lightbar = LightClass (y=10, x=2, w=76, h=14, xpad=1, ypad=1)
        lightbar.byindex = lightbar.interactive = lightbar.partial = True
      lightbar.lowlight()
      bbslist = sorted(openudb('bbslist')['boards'])
      sys.stderr.write('%r\n' % (bbslist,))
      echo (color() + lightbar.pos(3,0))
      echo ('%-27s %-15s %-18s %s' \
        % ('- BBS Name', 'Software', '+o', 'rating -'))
      lightbar.update \
        (['    %-25s %-15s %-18s %-4s %-3i' \
          % (bbsname, software, sysop, calcRating(ratings), len(comments)) \
              for bbsname, host, port, software, sysop,
                ratings, comments in bbslist])
      title = color() + '- %sa%sdd %sc%somment %sr%sate ' \
        '%si%snfo %st%selnet %sd%selete %sq%suit -' \
        % (color(*LIGHTBLUE), color(), color(*LIGHTBLUE), color(), \
           color(*LIGHTBLUE), color(), color(*LIGHTBLUE), color(), \
           color(*LIGHTBLUE), color(), color(*LIGHTBLUE), color(), \
           color(*LIGHTBLUE), color())
      lightbar.title(title, align='bottom')
      bbsname, host, port, software, sysop, ratings, comments \
        = bbslist[lightbar.selection]
    event, data = readevent(['input','refresh'])
    if event == 'refresh':
      dirty=True
      continue
    if event == 'input' and data.lower() not in 'acritdq':
      lightbar.run (key=data)
      bbsname, host, port, software, sysop, ratings, comments \
        = bbslist[lightbar.selection]
    elif event == 'input':
      if data.lower() == 'a': # add new bbs entry
        dirty=True
        lightbar.clear ()
        echo (lightbar.pos(2, 2) + color())
        echo ('Name of BBS: ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*25 + '\b'*25)
        bbsname = readline(25)
        if not bbsname: continue
        echo (lightbar.pos(2, 4) + color())
        echo ('telnet host: ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*30 + '\b'*30)
        host = readline(30)
        if not host: continue
        echo (lightbar.pos(2, 6) + color())
        echo ('telnet port (blank for default): ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*5 + '\b'*5)
        port = readline(5)
        if port:
          try: port = int(port)
          except ValueError: continue
        else:
          port=None
        echo (lightbar.pos(2, 8) + color())
        echo ('BBS Software: ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*15 + '\b'*15)
        software = readline(15)
        echo (lightbar.pos(2, 10) + color())
        echo ('sysop name: ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*18 + '\b'*18)
        sysop = readline(18)
        udb = openudb('bbslist')
        bbslist = [(r_bbsname, r_host, r_port, r_software,
          r_sysop, r_ratings, r_comments) \
            for r_bbsname, r_host, r_port, r_software,
              r_sysop, r_ratings, r_comments, \
                in udb['boards']] \
          + [(bbsname, host, port, software, sysop, [], [])]
        lock()
        udb['boards'] = bbslist
        commit()
        unlock()

      elif bbsname and data.lower() == 'c': # comment on bbs board
        dirty=True
        lightbar.clear ()
        echo (lightbar.pos(2, 2) + color())
        echo ('comment: ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*65 + '\b'*65)
        new_comment = readline(70).strip()
        if not new_comment: continue
        echo (lightbar.pos(2, 8) + color())
        if handle() in [u for u,c in comments]:
          echo ('change your comment for %s? [yn]' % (bbsname,))
        else:
          echo ('add comment for %s? [yn] ' % (bbsname,))
        yn=readkey()
        if yn.lower() != 'y':
          continue
        new_comments = \
          [(u,c) for u,c in comments if u != handle()] \
          + [(handle(), new_comment)]
        udb = openudb('bbslist')
        bbslist = [(r_bbsname, r_host, r_port, r_software,
          r_sysop, r_ratings, r_comments) \
            for r_bbsname, r_host, r_port, r_software,
              r_sysop, r_ratings, r_comments \
                in udb['boards'] \
                  if r_bbsname != bbsname] \
          + [(bbsname, host, port, software, sysop, ratings, new_comments)]
        lock()
        udb['boards'] = bbslist
        commit()
        unlock()

      elif bbsname and data.lower() == 'r': # rate a bbs board
        dirty=True
        lightbar.clear ()
        echo (lightbar.pos(2, 6) + color())
        echo ('rate bbs [1-4]: ')
        echo (color(BLUE)+color(INVERSE))
        echo (' '*1 + '\b'*1)
        rate = readkey()
        if not rate.isdigit(): continue
        try: rate = int(rate)
        except ValueError: continue
        echo (str(rate) + lightbar.pos(2, 8) + color())
        if handle() in [u for u, rating in ratings]:
          echo ('change your rating for %s to %i stars? [yn] ' \
            % (bbsname, rate,))
        else:
          echo ('rate %s with %i stars? [yn] ' % (bbsname, rate,))
        yn=readkey()
        if yn.lower() != 'y':
          continue
        new_rating = \
          [(u,r) for u, r in ratings if u != handle()] \
          + [(handle(), rate)]
        udb = openudb('bbslist')
        bbslist = [(r_bbsname, r_host, r_port, r_software,
          r_sysop, r_ratings, r_comments) \
            for r_bbsname, r_host, r_port, r_software,
              r_sysop, r_ratings, r_comments, \
                in udb['boards'] \
                  if r_bbsname != bbsname] \
          + [(bbsname, host, port, software, sysop, new_rating, comments)]
        lock()
        udb['boards'] = bbslist
        commit()
        unlock()

      elif bbsname and data.lower() == 't': # telnet to host
        dirty=True
        lightbar.clear ()
        gosub('telnet', host, port)

      elif bbsname and data.lower() == 'd': # delete record
        dirty=True
        udb = openudb('bbslist')
        bbslist = [(r_bbsname, r_host, r_port, r_software,
          r_sysop, r_ratings, r_comments) \
            for r_bbsname, r_host, r_port, r_software,
              r_sysop, r_ratings, r_comments \
                in udb['boards'] \
                  if r_bbsname != bbsname]
        lock()
        udb['boards'] = bbslist
        commit()
        unlock()

      elif data.lower() == 'q':
        break
