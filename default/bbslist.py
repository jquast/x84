"""
bbs listing for X/84, http://github.com/x84/jquast
"""
def main():
    session, term = getsession(), getterminal()
    session.activity = 'BBS Lister'
    dirty=True
    lightbar=False
    bbslist=[]
    udb = DBSessionProxy('bbslist')
    bbsname=host=port=software=sysop=ratings=comments=None
    while True:
        if dirty or not lightbar:
            def calcRating(ratings):
                rating, d = '----', 0
                if len(ratings):
                    d=sum([r for u, r in ratings])/len(ratings)
                return '*'*(d) + '-'*(4-d)
            echo (term.clear + term.normal)
            echo (u'\r\n ansi needed :( \r\n')
            if not lightbar:
                lightbar = LightClass (yloc=10, xloc=2, width=76, height=14, xpad=1, ypad=1)
                lightbar.byindex = lightbar.interactive = lightbar.partial = True
            lightbar.lowlight()
            if 0 == len(udb):
                udb['1984'] = ['1984.ws', 23, 'x/84',
                     'dingo', (('biG bROthER', 5),),
                     (('biG bROthER', 'a very loyal board to the cause'),),]
            bbslist = sorted(udb.items())
            echo (term.normal + lightbar.pos(3,0))
            echo ('%-27s %-16s %-18s %s' \
              % ('- BBS Name', 'Software', '+o', 'rating -'))
            lightbar.update \
              (['    %-25s %-16s %-18s %-4s %-3i' \
                % (r_bbsname, r_software, r_sysop, calcRating(r_ratings),
                             len(r_comments)) \
                    for r_bbsname, (r_host, r_port, r_software, r_sysop,
                      r_ratings, r_comments) in bbslist])
            title = term.normal + '- %sa%sdd %sc%somment %sr%sate ' \
              '%si%snfo %st%selnet %sd%selete %sq%suit -' \
              % (term.bold_blue, term.normal, term.bold_blue, term.normal, \
                 term.bold_blue, term.normal, term.bold_blue, term.normal, \
                 term.bold_blue, term.normal, term.bold_blue, term.normal, \
                 term.bold_blue, term.normal)
            lightbar.title(title, align='bottom')
            lightbar.title(title, align='top')
            bbsname, (host, port, software, sysop, ratings, comments) \
              = bbslist[lightbar.selection]
        event, data = readevent(['input','refresh'])
        if event == 'refresh':
            dirty=True
            continue
        if event == 'input' and (type(data) is int or data not in
                u'acritdqACRITDQ'):
            lightbar.run (key=data)
            bbsname, (host, port, software, sysop, ratings, comments) \
              = bbslist[lightbar.selection]
        elif event == 'input':
            if data in u'aA': # add new bbs entry
                dirty=True
                lightbar.clear ()
                echo (lightbar.pos(2, 2) + term.normal)
                echo ('Name of BBS: ')
                echo (term.blue + term.reverse)
                echo (' '*25 + '\b'*25)
                bbsname = readline(25)
                if not bbsname: continue
                echo (lightbar.pos(2, 4) + term.normal)
                echo ('telnet host: ')
                echo (term.blue + term.reverse)
                echo (' '*30 + '\b'*30)
                host = readline(30)
                if not host: continue
                echo (lightbar.pos(2, 6) + term.normal)
                echo ('telnet port (blank for default): ')
                echo (term.blue + term.reverse)
                echo (' '*5 + '\b'*5)
                port = readline(5)
                if port:
                    try: port = int(port)
                    except ValueError: continue
                else:
                    port=None
                echo (lightbar.pos(2, 8) + term.normal)
                echo ('BBS Software: ')
                echo (term.blue + term.reverse)
                echo (' '*16 + '\b'*16)
                software = readline(16)
                echo (lightbar.pos(2, 10) + term.normal)
                echo ('sysop name: ')
                echo (term.blue + term.reverse)
                echo (' '*18 + '\b'*18)
                sysop = readline(18)
                # XXX dupe entries allowed
                udb [bbsname] = (host, port, software, sysop, [], [])

            elif bbsname and data in u'Cc': # comment on bbs board
                dirty=True
                lightbar.clear ()
                echo (lightbar.pos(2, 2) + term.normal)
                echo ('comment: ')
                echo (term.blue + term.reverse)
                echo (' '*65 + '\b'*65)
                new_comment = readline(65).strip()
                if not new_comment:
                    continue
                echo (lightbar.pos(2, 8) + term.normal)
                if session.handle in [u for u,c in comments]:
                    echo ('change your comment for %s? [yn]' % (bbsname,))
                else:
                    echo ('add comment for %s? [yn] ' % (bbsname,))
                yn=getch()
                if yn not in 'yY':
                    continue
                new_comments = \
                  [(u,c) for u,c in comments if u != session.handle] \
                  + [(session.handle, new_comment)]
                udb[bbsname] = (host, port, software, sysop, ratings, new_comments)

            elif bbsname and data in u'Rr': # rate a bbs board
                dirty=True
                lightbar.clear ()
                echo (lightbar.pos(2, 6) + term.normal)
                echo ('rate bbs [1-4]: ')
                echo (term.blue + term.reverse)
                echo (' '*1 + '\b'*1)
                rate = getch()
                if not rate.isdigit(): continue
                try: rate = int(rate)
                except ValueError: continue
                echo (str(rate) + lightbar.pos(2, 8) + term.normal)
                if session.handle in [u for u, rating in ratings]:
                    echo (u'change your rating for %s to %i stars? [yn] ' \
                      % (bbsname, rate,))
                else:
                    echo (u'rate %s with %i stars? [yn] ' % (bbsname, rate,))
                yn=getch()
                if type(yn) is int or yn not in u'Yy':
                    continue
                new_rating = \
                  [(u,r) for u, r in ratings if u != session.handle] \
                  + [(session.handle, rate)]
                udb[bbsname] = (host, port, software, sysop, new_rating, comments)

            elif bbsname and data in u'tI': # telnet to host
                dirty=True
                lightbar.clear ()
                gosub('default/telnet', host, port)

            elif bbsname and data in u'dD' \
            and session.user.is_sysop: # delete record
                dirty=True
                del udb[bbsname]
            elif bbsname and data in u'iI':
                dirty = True
                p = ParaClass (y=10, x=2, w=76, h=14, xpad=1, ypad=1)
                p.lowlight ()
                cr = ''
                for nick, comment in comments:
                    rating = None
                    for r_nick, rating in ratings:
                        if r_nick == nick:
                            break
                        rating = None
                    cr += '%s%s%s%s\n  %s\n' % \
                        (term.bold_blue, nick, term.normal,
                            ' %s%s%s:' % (term.bold_red,'*'*rating,term.normal)
                            if rating else ':',
                         comment)
                p.update ('%saddress: telnet://%s%s\nsysop: %s\n' \
                           '%ssoftware:%s\n%s%s' \
                           % (term.normal, host,
                             ':%s' % (port,) if port not in (23, None) else '',
                             sysop,
                             'number of ratings: %i\n' % (len(ratings)) \
                                 if ratings else '',
                             software, '\n' if comments else '', cr ))
                p.title ('<return/spacebar> return to list', align='top')
                k = getch()
                if k in (' ',term.KEY_ENTER, term.KEY_ESCAPE):
                    continue
                p.run (k)

            elif data in u'qQ':
                break
