""" System info for x/84 BBS, https://github.com/jquast/x84 """

def main ():
    """ Main procedure. """
    # pylint: disable=R0914,W0141
    #         Too many local variables
    #         Used builtin function 'map'
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
    for num, line in enumerate(body):
        while num > len(otxt):
            otxt += [u'',]
        otxt[num] = otxt[num][:int(term.width/2.5)] + u' ' + line
    width = max([len(Ansi(line)) for line in otxt])
    height = len(otxt)
    num_stars = int((term.width *term.height) *.002)
    stars = dict([(n, (random.choice('\\|/-'),
      float(random.choice(range(term.width))),
      float(random.choice(range(term.height))))) for n in range(num_stars)])
    melting = {}
    plusStar = False
    tm_out, tm_min, tm_max, tm_step = 0.08, 0.01, 2.0, .01
    wind = (0.7, 0.1, 0.01, 0.01)

    def refresh ():
        """ Refresh screen and return top-left (x, y) location. """
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
        xloc = (term.width /2) -(width /2)
        yloc = (term.height /2) -(height /2)
        echo(u''.join((
            term.normal,
            (u'\r\n' + term.clear_eol) * term.height,
            u''.join([term.move(yloc + abs_y, xloc) + line
                for abs_y, line in enumerate(otxt)]),)))
        return xloc, yloc

    txt_x, txt_y = refresh ()
    if (txt_x, txt_y) == (None, None):
        return

    def charAtPos(yloc, xloc, txt_y, txt_x):
        """ Return art (y, x) for location """
        return (u' ' if yloc-txt_y < 0 or yloc-txt_y >= height
                or xloc-txt_x < 0 or xloc-txt_x >= len(otxt[yloc-txt_y])
                else otxt[yloc-txt_y][xloc-txt_x])

    def iter_wind(xs, ys, xd, yd):
        """ An easterly Wind """
        xs += xd; ys += yd
        if xs <= .5: xd = random.choice([0.01, 0.015, 0.02])
        elif xs >= 1: xd = random.choice([-0.01, -0.015, -0.02])
        if ys <= -0.1: yd = random.choice([0.01, 0.015, 0.02, 0.02])
        elif ys >= 0.1: yd = random.choice([-0.01, -0.015, -0.02])
        return xs, ys, xd, yd

    def iter_star(char, xloc, yloc):
        """ Given char and current position, apply wind and return new
        char and new position. """
        if char == '\\':
            char = '|'
        elif char == '|':
            char = '/'
        elif char == '/':
            char = '-'
        elif char == '-':
            char = '\\'
        xloc += wind[0]
        yloc += wind[1]
        if xloc < 1 or xloc > term.width:
            xloc = (1.0 if xloc > term.width
                    else float(term.width))
            yloc = (float(random.choice
                (range(term.height))))
        if yloc < 1 or yloc > term.height:
            yloc = (1.0 if yloc > term.height
                    else float(term.height))
            xloc = (float(random.choice
                (range(term.width))))
        return char, xloc, yloc

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

    def draw_star (star, x, y):
        ch = charAtPos(int(y), int(x), txt_y, txt_x)
        if ch != ' ':
            melting[(int(y), int(x))] = len(melt_colors)
        if plusStar:
            echo (term.move(int(y), int(x)) + melt_colors[-1] + star)

    with term.hidden_cursor():
        while txt_x is not None and txt_y is not None:
            if session.poll_event('refresh'):
                num_stars = int(num_stars)
                stars = dict([(n, (random.choice('\\|/-'),
                  float(random.choice(range(term.width))),
                  float(random.choice(range(term.height)))))
                  for n in range(num_stars)])
                otxt = list(art.splitlines())
                for n, b in enumerate(body):
                    while n > len(otxt):
                        otxt += [u'',]
                    otxt[n] = otxt[n][:int(term.width/2.5)] + u' ' + b
                txt_x, txt_y = refresh()
                continue
            inp = getch(tm_out)
            if inp in (term.KEY_UP, 'k'):
                if tm_out >= tm_min:
                    tm_out -= tm_step
            elif inp in (term.KEY_DOWN, 'j'):
                if tm_out <= tm_max:
                    tm_out += tm_step
            elif inp in (term.KEY_LEFT, 'h'):
                if num_stars > 2:
                    num_stars = int(num_stars * .5)
                    stars = dict([(n, (random.choice('\\|/-'),
                      float(random.choice(range(term.width))),
                      float(random.choice(range(term.height)))))
                      for n in range(num_stars)])
            elif inp in (term.KEY_RIGHT, 'l'):
                if num_stars < (term.width * term.height) / 4:
                    num_stars = int(num_stars * 1.5)
                    stars = dict([(n, (random.choice('\\|/-'),
                      float(random.choice(range(term.width))),
                      float(random.choice(range(term.height)))))
                      for n in range(num_stars)])
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
            for star_key, star_val in stars.items():
                erase (star_key)
                stars[star_key] = iter_star(*star_val)
                draw_star (*stars[star_key])
            wind = iter_wind(*wind)
