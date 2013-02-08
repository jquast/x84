""" System info for x/84 BBS, https://github.com/jquast/x84 """

def main ():
    from x84.bbs import getsession, Ansi, echo, getch, from_cp437
    from x84.engine import __url__ as url
    import platform
    import random
    import sys
    import os
    artfile = os.path.join(os.path.dirname(__file__), 'art', 'plant.ans',)
    body = u'\r\n'.join((
        ' Authors:',
        '   Johannes Lundberg <johannes.lundberg@gmail.com>',
        '   Jeffrey Quast <dingo@1984.ws>',
        '   Wijnand Modderman-Lenstra <maze@pyth0n.org>',
        ' Artwork: spidy!food, hellbeard!impure',))
    PAK = 'Press any key ... (or +-*)'
    session = getsession()
    term = session.terminal
    melt_colors = ([term.normal]
            + [term.bold_white]*16
            + [term.bold_cyan]*16
            + [term.bold_blue])
    system, node, release, version, machine, processor = platform.uname()
    xxx = from_cp437(open(artfile).read()) if os.path.exists(artfile) else u''
    otxt = u''.join((
        xxx,
        body, u'\r\n',
        u' System: %s %s %s\r\n' % (system, release, machine),
        u' Software: X/84, %s; ' % (url,),
        platform.python_implementation(),
        (platform.python_version()
            if hasattr(platform, 'python_implementation')
            else '%s %s\r\n' % ('.'.join(map(str, sys.version_info[:3])))),
        '-'.join(map(str, sys.version_info[3:])),
        u'\r\n',
        PAK.center(term.width).rstrip() + '\r\n',))
    print otxt
    width = max([len(Ansi(line)) for line in otxt.splitlines()])
    height = len(otxt.splitlines())
    numStars = int((term.width *term.height) *.03)
    stars = dict([(n, (random.choice('\\|/-'),
      float(random.choice(range(term.width))),
      float(random.choice(range(term.height))))) for n in range(numStars)])
    melting = {}
    plusStar = False
    tm_out, tMIN, tMAX, tSTEP = 0.08, 0.02, 2.0, .02
    wind = (0.7, 0.1, 0.01, 0.01)

    def refresh ():
        session.activity = 'System Info'
        echo(u'\r\n\r\n')
        if term.width < width+3:
            echo (term.bold_red + 'your screen is too thin! (%s/%s)\r\n' \
              'press any key...' % (term.width, width+5))
            getch ()
            return (None, None)
        if term.height < height:
            echo (term.bold_red + 'your screen is too short! (%s/%s)\r\n' \
              'press any key...' % (term.height, height))
            getch ()
            return (None, None)
        x = (term.width /2) -(width /2)
        y = (term.height /2) -(height /2)
        echo(u'\r\n' * term.height)
        echo (''.join([term.move(y+abs_y, x) + data \
              for abs_y, data in enumerate(otxt)]))
        return x, y

    txt_x, txt_y = refresh ()
    if (txt_x, txt_y) == (None, None):
        return

    def charAtPos(y, x, txt_y, txt_x):
        return ' ' if y-txt_y < 0 or y-txt_y >= height \
            or x-txt_x < 0 or x-txt_x >= len(otxt[y-txt_y]) \
            else otxt[y-txt_y][x-txt_x]

    def iterWind(xs, ys, xd, yd):
        # an easterly wind
        xs += xd; ys += yd
        if xs <= .5: xd = random.choice([0.01, 0.015, 0.02])
        elif xs >= 1: xd = random.choice([-0.01, -0.015, -0.02])
        if ys <= -0.1: yd = random.choice([0.01, 0.015, 0.02, 0.02])
        elif ys >= 0.1: yd = random.choice([-0.01, -0.015, -0.02])
        return xs, ys, xd, yd

    def iterStar(c, x, y):
        if c == '\\': char = '|'
        elif c == '|': char = '/'
        elif c == '/': char = '-'
        elif c == '-': char = '\\'
        x += wind[0]; y += wind[1]
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
        while True:
            if session.poll_event('refresh'):
                txt_x, txt_y = refresh()
            inp = getch(tm_out)
            if inp in (u'+',):
                if tm_out >= tMIN:
                    tm_out -= tSTEP
            elif inp in (u'-',):
                if tm_out <= tMAX:
                    tm_out += tSTEP
            elif inp in (u'*',) and not plusStar:
                plusStar = True
            elif inp in (u'*',) and plusStar:
                for star in stars:
                    erase (star)
                plusStar = False
            melt ()
            for starKey, starVal in stars.items():
                erase (starKey)
                stars[starKey] = iterStar(*starVal)
                drawStar (*stars[starKey])
            wind = iterWind(*wind)
