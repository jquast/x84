""" System info for x/84 BBS, https://github.com/jquast/x84 """

def main ():
    from x84.bbs import getsession, getterminal, Ansi, echo, getch, from_cp437
    from x84.engine import __url__ as url
    import platform
    import random
    import sys
    import os
    session, term = getsession(), getterminal()
    session.activity = 'System Info'
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'plant.ans',)
    system, node, release, version, machine, processor = platform.uname()
    body = [u'AUthORS:',
            u'Johannes Lundberg',
            u'Jeffrey Quast',
            u'Wijnand Modderman-Lenstra',
            u'',
            u'ARtWORk:',
            u'spidy!food,',
            u'hellbeard!impure',
            u'\r\n',
            u'SYStEM: %s %s %s' % (system, release, machine),
            u'SOftWARE: X/84',
            url,
            u'\r\n',
            (platform.python_implementation() + u' '
                + '-'.join(map(str, sys.version_info[3:])))
            + u' ' + (platform.python_version()
                if hasattr(platform, 'python_implementation')
                else u'.'.join(map(str, sys.version_info[:3]))),
            ]
    melt_colors = (
            [term.normal]
            + [term.bold_blue]*3
            + [term.red]*4
            + [term.bold_red]
            + [term.bold_white]
            + [term.normal]*6
            + [term.blue]*2
            + [term.bold_blue]
            + [term.bold_white]
            + [term.normal])
    art = from_cp437(open(artfile).read()) if os.path.exists(artfile) else u''
    otxt = list(art.splitlines())
    for n, b in enumerate(body):
        while n > len(otxt):
            otxt += [u'',]
        otxt[n] = otxt[n][:int(term.width/2.5)] + u' ' + b
    width = max([len(Ansi(line)) for line in otxt])
    height = len(otxt)
    numStars = int((term.width *term.height) *.002)
    stars = dict([(n, (random.choice('\\|/-'),
      float(random.choice(range(term.width))),
      float(random.choice(range(term.height))))) for n in range(numStars)])
    melting = {}
    plusStar = False
    tm_out, tMIN, tMAX, tSTEP = 0.08, 0.01, 2.0, .01
    wind = (0.7, 0.1, 0.01, 0.01)

    def refresh ():
        echo(u'\r\n\r\n')
        if term.width < width:
            echo(u''.join((
                term.move(term.height, 0),
                u'\r\n\r\n',
                term.bold_red + 'screen too thin! (%s/%s)' % (
                    term.width, width,),
                u'\r\n\r\n',
                u'press any key...',)))
            getch ()
            return (None, None)
        if term.height < height:
            echo(u''.join((
                term.move(term.height, 0),
                u'\r\n\r\n',
                term.bold_red + 'screen too short! (%s/%s)' % (
                    term.height, height),
                u'\r\n\r\n',
                u'press any key...',)))
            getch ()
            return (None, None)
        x = (term.width /2) -(width /2)
        y = (term.height /2) -(height /2)
        echo(u''.join((
            term.normal,
            (u'\r\n' + term.clear_eol) * term.height,
            u''.join([term.move(y + abs_y, x) + line
                for abs_y, line in enumerate(otxt)]),)))
        return x, y

    txt_x, txt_y = refresh ()
    if (txt_x, txt_y) == (None, None):
        return

    def charAtPos(y, x, txt_y, txt_x):
        return (u' ' if y-txt_y < 0 or y-txt_y >= height
                or x-txt_x < 0 or x-txt_x >= len(otxt[y-txt_y])
                else otxt[y-txt_y][x-txt_x])

    def iterWind(xs, ys, xd, yd):
        # an easterly wind
        xs += xd; ys += yd
        if xs <= .5: xd = random.choice([0.01, 0.015, 0.02])
        elif xs >= 1: xd = random.choice([-0.01, -0.015, -0.02])
        if ys <= -0.1: yd = random.choice([0.01, 0.015, 0.02, 0.02])
        elif ys >= 0.1: yd = random.choice([-0.01, -0.015, -0.02])
        return xs, ys, xd, yd

    def iterStar(c, x, y):
        if c == '\\':
            char = '|'
        elif c == '|':
            char = '/'
        elif c == '/':
            char = '-'
        elif c == '-':
            char = '\\'
        x += wind[0]
        y += wind[1]
        if x < 1 or x > term.width:
            x = (1.0 if x > term.width
                    else float(term.width))
            y = (float(random.choice
                (range(term.height))))
        if y < 1 or y > term.height:
            y = (1.0 if y > term.height
                    else float(term.height))
            x = (float(random.choice
                (range(term.width))))
        return char, x, y

    def erase(s):
        if plusStar:
            char, x, y = stars[s]
            echo (''.join((term.move(int(y), int(x)), term.normal,
              charAtPos(int(y), int(x), txt_y, txt_x),)))

    def melted(y, x):
        melting[(y,x)] -= 1
        if 0 == melting[(y,x)]:
            del melting[(y,x)]

    def melt():
        for (y, x), phase in melting.items():
            echo (''.join((term.move(y, x), melt_colors[phase-1],
              charAtPos(y, x, txt_y, txt_x),)))
            melted(y, x)

    def drawStar (star, x, y):
        ch = charAtPos(int(y), int(x), txt_y, txt_x)
        if ch != ' ':
            melting[(int(y), int(x))] = len(melt_colors)
        if plusStar:
            echo (term.move(int(y), int(x)) + melt_colors[-1] + star)

    with term.hidden_cursor():
        while txt_x is not None and txt_y is not None:
            if session.poll_event('refresh'):
                numStars = int(numStars)
                stars = dict([(n, (random.choice('\\|/-'),
                  float(random.choice(range(term.width))),
                  float(random.choice(range(term.height)))))
                  for n in range(numStars)])
                otxt = list(art.splitlines())
                for n, b in enumerate(body):
                    while n > len(otxt):
                        otxt += [u'',]
                    otxt[n] = otxt[n][:int(term.width/2.5)] + u' ' + b
                txt_x, txt_y = refresh()
                continue
            inp = getch(tm_out)
            if inp in (term.KEY_UP, 'k'):
                if tm_out >= tMIN:
                    tm_out -= tSTEP
            elif inp in (term.KEY_DOWN, 'j'):
                if tm_out <= tMAX:
                    tm_out += tSTEP
            elif inp in (term.KEY_LEFT, 'h'):
                if numStars > 2:
                    numStars = int(numStars * .5)
                    stars = dict([(n, (random.choice('\\|/-'),
                      float(random.choice(range(term.width))),
                      float(random.choice(range(term.height)))))
                      for n in range(numStars)])
            elif inp in (term.KEY_RIGHT, 'l'):
                if numStars < (term.width * term.height) / 4:
                    numStars = int(numStars * 1.5)
                    stars = dict([(n, (random.choice('\\|/-'),
                      float(random.choice(range(term.width))),
                      float(random.choice(range(term.height)))))
                      for n in range(numStars)])
            elif inp in (u'*',) and not plusStar:
                plusStar = True
            elif inp in (u'*',) and plusStar:
                for star in stars:
                    erase (star)
                plusStar = False
            elif inp is not None:
                echo(term.move(term.height, 0))
                break
            melt ()
            for starKey, starVal in stars.items():
                erase (starKey)
                stars[starKey] = iterStar(*starVal)
                drawStar (*stars[starKey])
            wind = iterWind(*wind)
